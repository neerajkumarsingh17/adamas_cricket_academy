# Local development — native setup

No Docker locally. Services run natively; the app runs natively. Production still ships as a
container image to ECS Fargate, so a `Dockerfile` exists — it is just never used on your machine.

Two consequences to accept up front:

- **Versions drift from production unless you pin them.** Install PostgreSQL **16**, not
  whatever your package manager defaults to. The audit diffs use JSONB and the numbering series
  uses database sequences; a version mismatch is a real divergence, not a theoretical one.
- **A second developer gets this page instead of one command.** Fine for one person. Revisit
  when the team grows.

---

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.12 | Django 5.1 |
| Node | 20 LTS | Vite 5 |
| PostgreSQL | **16** | JSONB, sequences, `pg_trgm` for duplicate detection |
| Redis | 7 | Celery broker + cache + OTP store |
| MinIO | latest | S3 substitute, so no AWS credentials are needed to develop |

### macOS

```bash
brew install python@3.12 node@20 postgresql@16 redis
brew install minio/stable/minio minio/stable/mc

brew services start postgresql@16
brew services start redis

# postgresql@16 is keg-only — put it on PATH
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
```

### Ubuntu / Debian

```bash
# PostgreSQL 16 from PGDG — the distro default is usually older
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list'
wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update && sudo apt install -y postgresql-16 redis-server python3.12 python3.12-venv

curl -O https://dl.min.io/server/minio/release/linux-amd64/minio && chmod +x minio
sudo mv minio /usr/local/bin/
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc
sudo mv mc /usr/local/bin/

sudo systemctl enable --now postgresql redis-server
```

### Windows

Run everything under **WSL2** and follow the Ubuntu steps. Native Postgres and Redis on Windows
are more trouble than they are worth.

---

## One-time project setup

```bash
# 1. Database
createdb aca_oms_dev
psql aca_oms_dev -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"     # fuzzy name matching
psql aca_oms_dev -c "CREATE EXTENSION IF NOT EXISTS unaccent;"

# 2. Python
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

# 3. Node
cd ../frontend && npm ci && cd ..

# 4. Environment
cp .env.example .env        # then fill it in — see below

# 5. Object storage
mkdir -p ~/.aca-oms-storage
minio server ~/.aca-oms-storage --console-address :9001 &
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/aca-oms-dev

# 6. Migrate and seed
cd backend
python manage.py migrate
python manage.py seed_roles
python manage.py seed_master_data
python manage.py createsuperuser
```

### `.env` for native development

```ini
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=dev-only-not-a-real-secret
DEBUG=True

DATABASE_URL=postgres://localhost:5432/aca_oms_dev
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# MinIO — the same variables production uses, pointed at localhost
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=aca-oms-dev
AWS_S3_ENDPOINT_URL=http://localhost:9000
AWS_S3_REGION_NAME=ap-south-1

NOTIFICATION_BACKEND=console          # prints instead of sending

# Optional. When set, every OTP request (any mobile, any role) returns this
# code instead of a random one — no more fishing the real code out of the
# console log when testing several accounts. config/settings/dev.py only;
# never set this in staging/prod .env.
DEV_STATIC_OTP=765432
```

`AWS_S3_ENDPOINT_URL` is the only setting that differs from production. Leave it unset in
staging and production and boto3 talks to real S3. Nothing in application code branches on it.

---

## Running it

Four processes. Do not manage four terminal tabs by hand — use **honcho**, which is a pip
install and gives you one command, the native equivalent of `docker compose up`.

`Procfile.dev` at the repository root:

```
web:      cd backend && .venv/bin/python manage.py runserver 0.0.0.0:8000
worker:   cd backend && .venv/bin/celery -A config worker -l info
beat:     cd backend && .venv/bin/celery -A config beat -l info
frontend: cd frontend && npm run dev
```

MinIO stays out of the Procfile — run it once as a background service and forget it
(`brew services start minio` on macOS, or a systemd user unit on Linux).

`Makefile`:

```make
.PHONY: dev migrate seed test lint fmt shell reset-db storage

dev:        ## everything, one terminal
	honcho -f Procfile.dev start

migrate:
	cd backend && .venv/bin/python manage.py migrate

seed:
	cd backend && .venv/bin/python manage.py seed_roles && \
	  .venv/bin/python manage.py seed_master_data

test:
	cd backend && .venv/bin/pytest -q
	cd frontend && npm run test

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/mypy .
	cd frontend && npx tsc --noEmit

fmt:
	cd backend && .venv/bin/ruff format .

shell:
	cd backend && .venv/bin/python manage.py shell_plus

storage:    ## start MinIO in the foreground if it is not already running
	minio server ~/.aca-oms-storage --console-address :9001

reset-db:   ## destructive — local only
	dropdb --if-exists aca_oms_dev && createdb aca_oms_dev && \
	  psql aca_oms_dev -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" && \
	  psql aca_oms_dev -c "CREATE EXTENSION IF NOT EXISTS unaccent;" && \
	  $(MAKE) migrate seed
```

Day to day: `make dev`. The MinIO console is at http://localhost:9001 if you want to see the
uploaded files.

---

## Testing

`pytest-django` creates and drops `test_aca_oms_dev` itself — no setup needed. Add
`--reuse-db` locally to skip recreation between runs, and drop it in CI.

```bash
cd backend && .venv/bin/pytest -q --reuse-db
```

Tests must not touch MinIO. Point storage at Django's in-memory backend in `settings/test.py`
and mock the presign calls — a test suite that needs a running object store is a test suite
that fails on someone else's machine.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `psql: command not found` on macOS | `postgresql@16` is keg-only | Add `/opt/homebrew/opt/postgresql@16/bin` to PATH |
| `FATAL: database "aca_oms_dev" does not exist` | Skipped step 1 | `createdb aca_oms_dev` |
| `function similarity() does not exist` | `pg_trgm` not installed | `psql aca_oms_dev -c "CREATE EXTENSION pg_trgm;"` |
| Celery connects but no tasks run | Worker started before Redis | `redis-cli ping`, then restart the worker |
| `SignatureDoesNotMatch` from MinIO | Wrong key, or endpoint URL missing | Check `AWS_S3_ENDPOINT_URL` is set in `.env` |
| Uploads 403 from the browser | MinIO CORS | `mc admin config set local api cors_allow_origin="http://localhost:5173"` |
| Migrations conflict after a `git pull` | Two branches added migrations | `python manage.py makemigrations --merge`, review before committing |
| Postgres is 14 or 15 | Package manager default | Reinstall 16 — do not proceed on the wrong version |

---

## CI is different, and that is fine

GitHub Actions uses its own **service containers** for Postgres and Redis. That is the runner's
mechanism, unrelated to local setup, and it works whether or not you use Docker on your machine.
No change is needed there.

## Production is still a container

`Dockerfile` (multi-stage, non-root user, gunicorn) exists for ECS Fargate. It is built by CI
and never used locally. Keep the Python version in it pinned to the same 3.12 you develop
against.
