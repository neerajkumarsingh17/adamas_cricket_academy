#!/usr/bin/env bash
# Deploy the latest changes to the production Docker stack
# (deploy/docker-compose.prod.yml — containers deploy-web-1, deploy-worker-1,
# deploy-beat-1, deploy-nginx-1, deploy-redis-1):
#   1. pull the code
#   2. build the frontend   (nginx serves frontend/dist directly)
#   3. build the backend image
#   4. run database migrations (only if there are new ones)
#   5. collect static files
#   6. restart web + worker + beat   (nginx and redis keep running)
#
# Usage (on the server, from anywhere in the repo):
#   ./deploy/deploy.sh            # deploys the current branch
#   ./deploy/deploy.sh main       # switches to / deploys branch "main"

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${1:-$(git -C "$ROOT" branch --show-current)}"
# Same project name ("deploy") the running containers already use.
COMPOSE="docker compose -p deploy -f $ROOT/deploy/docker-compose.prod.yml"

echo "==> Pulling latest code ($BRANCH)"
cd "$ROOT"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

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
$COMPOSE run --rm -T web python manage.py collectstatic --noinput > /dev/null

echo "==> Restarting backend (web, worker, beat)"
$COMPOSE up -d --no-deps web worker beat
$COMPOSE ps

echo "==> Cleaning up old images"
docker image prune -f > /dev/null

echo "==> Done: $(git -C "$ROOT" log -1 --format='%h %s')"
