#!/usr/bin/env bash
# Deploy the latest changes to the production Docker stack
# (deploy/docker-compose.prod.yml — containers deploy-web-1, deploy-worker-1,
# deploy-beat-1, deploy-nginx-1, deploy-redis-1):
#   1. pull the code
#   2. build the frontend   (nginx serves frontend/dist directly)
#   3. build the backend image
#   4. run database migrations (only if there are new ones)
#   5. collect static files
#   6. restart web + worker + beat, reload nginx config (redis keeps running)
#   7. verify /api/v1/health/ through nginx
#
# Usage (on the server, from anywhere in the repo):
#   ./deploy/deploy.sh            # deploys the current branch
#   ./deploy/deploy.sh main       # switches to / deploys branch "main"

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${1:-$(git -C "$ROOT" branch --show-current)}"
# Same project name ("deploy") the running containers already use.
COMPOSE="docker compose -p deploy -f $ROOT/deploy/docker-compose.prod.yml"

# One deploy at a time — two concurrent `npm ci` runs corrupt node_modules.
exec 9> /tmp/acaoms-deploy.lock
flock -n 9 || { echo "Another deploy is already running" >&2; exit 1; }

echo "==> Pulling latest code ($BRANCH)"
cd "$ROOT"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

# Generated dirs must belong to the deploying user. A past build run as root
# (e.g. a Docker build without --user) leaves root-owned files that make
# `npm ci` fail with EACCES, so repair them up front.
FRONTEND_GENERATED=("$ROOT/frontend/node_modules" "$ROOT/frontend/dist")
for dir in "${FRONTEND_GENERATED[@]}"; do
  [ -e "$dir" ] || continue
  if [ -n "$(find "$dir" -not -user "$(id -un)" -print -quit)" ]; then
    echo "==> Fixing ownership of $dir"
    sudo -n chown -R "$(id -u):$(id -g)" "$dir" || {
      echo "Cannot fix ownership; run: sudo chown -R $(id -un): $dir" >&2
      exit 1
    }
  fi
done

echo "==> Building frontend"
if command -v npm > /dev/null; then
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund && npm run build)
else
  # No Node on the server — build inside a throwaway Node container instead.
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$ROOT/frontend:/app" -w /app node:20-alpine \
    sh -c "npm ci --no-audit --no-fund && npm run build"
fi

echo "==> Building backend image"
$COMPOSE build web worker beat

echo "==> Checking for database migrations"
pending="$($COMPOSE run --rm -T web python manage.py showmigrations --plan | grep -F '[ ]' || true)"
if [ -n "$pending" ]; then
  echo "$pending"
  $COMPOSE run --rm -T web python manage.py migrate --noinput
else
  echo "No new migrations"
fi

echo "==> Collecting static files"
# The static volume may have been created root-owned; the app user can't write
# to it then. Idempotent repair, run as root.
$COMPOSE run --rm -T --no-deps --user root web chown -R app:app /app/staticfiles
$COMPOSE run --rm -T web python manage.py collectstatic --noinput > /dev/null

echo "==> Restarting backend (web, worker, beat)"
$COMPOSE up -d --no-deps web worker beat

echo "==> Reloading nginx"
# Make sure nginx is up, then pick up any change to the bind-mounted nginx.conf.
$COMPOSE up -d --no-deps nginx
$COMPOSE exec -T nginx nginx -t
$COMPOSE exec -T nginx nginx -s reload
$COMPOSE ps

echo "==> Waiting for health check"
# Django rejects Host: localhost, so send the first host from ALLOWED_HOSTS.
HEALTH_HOST="$(grep -E '^ALLOWED_HOSTS=' "$ROOT/backend/.env" | cut -d= -f2- | cut -d, -f1 | tr -d '"'"'"' ')"
healthy=0
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null -H "Host: $HEALTH_HOST" http://localhost/api/v1/health/; then
    healthy=1
    break
  fi
  sleep 2
done
if [ "$healthy" -ne 1 ]; then
  echo "Health check failed after deploy; recent web logs:" >&2
  $COMPOSE logs --tail=50 web >&2
  exit 1
fi
echo "Healthy"

echo "==> Cleaning up old images"
docker image prune -f > /dev/null

echo "==> Done: $(git -C "$ROOT" log -1 --format='%h %s')"
