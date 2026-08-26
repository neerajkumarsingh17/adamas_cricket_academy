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
