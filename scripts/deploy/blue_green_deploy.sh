#!/bin/bash
set -euo pipefail

PROJECT_PATH="/var/www/community_savings"
DOMAIN="njangihub.medremindr.com"

BLUE_PORT=8010
GREEN_PORT=8011
ACTIVE_FILE=".active_color"
NGINX_SITE="/etc/nginx/sites-available/njangihub" 

cd "$PROJECT_PATH"

log() {
  echo ""
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

rollback_failed_new_color() {
  log "❌ Deployment failed. Cleaning failed new color: $NEW_COLOR"

  WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
    --env-file ".env.$NEW_COLOR" \
    -p "community_savings_$NEW_COLOR" \
    -f docker-compose.app.yml down || true

  log "✅ Old color remains active: $ACTIVE_COLOR"
  log "✅ Application should still be online."
  exit 1
}

trap rollback_failed_new_color ERR

log "🚀 Starting safe blue-green deployment..."

if [ ! -f "$ACTIVE_FILE" ]; then
  echo "blue" > "$ACTIVE_FILE"
fi

ACTIVE_COLOR=$(cat "$ACTIVE_FILE")

if [ "$ACTIVE_COLOR" = "blue" ]; then
  NEW_COLOR="green"
  NEW_PORT=$GREEN_PORT
  OLD_COLOR="blue"
  OLD_PORT=$BLUE_PORT
else
  NEW_COLOR="blue"
  NEW_PORT=$BLUE_PORT
  OLD_COLOR="green"
  OLD_PORT=$GREEN_PORT
fi

log "Current active color: $ACTIVE_COLOR"
log "New color: $NEW_COLOR on port $NEW_PORT"

NEW_ENV_FILE=".env.$NEW_COLOR"
OLD_ENV_FILE=".env.$OLD_COLOR"

log "📥 Pulling latest code..." 
git fetch origin
git reset --hard origin/main
git clean -fd -e .env -e .env.blue -e .env.green

log "🔒 Isolating environment configs ($NEW_ENV_FILE)"
cp .env "$NEW_ENV_FILE"

if [ -n "${EXCHANGE_API_KEY:-}" ]; then
  sed -i '/^EXCHANGE_API_KEY=/d' "$NEW_ENV_FILE"
  echo "EXCHANGE_API_KEY=${EXCHANGE_API_KEY}" >> "$NEW_ENV_FILE" 
fi


log "🐳 Ensuring infrastructure is running..."
docker compose -f docker-compose.infra.yml --env-file .env up -d

log "🐳 Building new app image..."
WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
  --env-file "$NEW_ENV_FILE" \
  -p "community_savings_$NEW_COLOR" \
  -f docker-compose.app.yml build

log "📦 Running migrations once..."
WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
  --env-file "$NEW_ENV_FILE" \
  -p "community_savings_$NEW_COLOR" \
  -f docker-compose.app.yml run --rm web python manage.py migrate --noinput

log "📁 Collecting static files once..."
WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
  --env-file "$NEW_ENV_FILE" \
  -p "community_savings_$NEW_COLOR" \
  -f docker-compose.app.yml run --rm web python manage.py collectstatic --noinput --clear

# log "🌍 Compiling translation messages once..."
# WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
#   --env-file "$NEW_ENV_FILE" \
#   -p "community_savings_$NEW_COLOR" \
#   -f docker-compose.app.yml run --rm web python manage.py compilemessages

log "🧹 Cleaning stale containers for $NEW_COLOR..."

WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
  --env-file "$NEW_ENV_FILE" \
  -p "community_savings_$NEW_COLOR" \
  -f docker-compose.app.yml down --remove-orphans || true

log "🟢 Starting new color..."
WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
  --env-file "$NEW_ENV_FILE" \
  -p "community_savings_$NEW_COLOR" \
  -f docker-compose.app.yml up -d

log "⏳ Running health checks on new color..."

for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:$NEW_PORT/health/" > /dev/null; then
    log "✅ New color passed health check"
    break
  fi

  if [ "$i" -eq 30 ]; then
    log "❌ New color failed health checks"
    rollback_failed_new_color
  fi

  sleep 3
done

log "🔁 Switching Nginx traffic to $NEW_COLOR..."

sudo tee "$NGINX_SITE" > /dev/null <<EOF
server {
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 50M;

    location /static/ {
        alias /opt/community_savings/staticfiles/;
    }

    location /media/ {
        alias /opt/community_savings/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:$NEW_PORT;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$host\$request_uri;
}
EOF

sudo nginx -t
sudo systemctl reload nginx

log "🔎 Verifying public domain after traffic switch..."

for i in {1..20}; do
  if curl -fsS "https://$DOMAIN/health/" > /dev/null; then
    log "✅ Public domain is healthy after switch"
    break
  fi

  if [ "$i" -eq 20 ]; then
    log "❌ Public domain failed after switch. Rolling back Nginx to old color."

    sudo sed -i "s/127.0.0.1:$NEW_PORT/127.0.0.1:$OLD_PORT/g" "$NGINX_SITE"
    sudo nginx -t
    sudo systemctl reload nginx

    WEB_PORT="$NEW_PORT" ENV_FILE="$NEW_ENV_FILE" docker compose \
      --env-file "$NEW_ENV_FILE" \
      -p "community_savings_$NEW_COLOR" \
      -f docker-compose.app.yml down || true

    log "✅ Rollback complete. Old color remains active."
    exit 1
  fi

  sleep 3
done

echo "$NEW_COLOR" > "$ACTIVE_FILE"

log "⏳ Waiting before stopping old color..."
sleep 20

log "🧹 Stopping old color: $OLD_COLOR"
if [ -f "$OLD_ENV_FILE" ]; then
  WEB_PORT="$OLD_PORT" docker compose \
    --env-file "$OLD_ENV_FILE" \
    -p "community_savings_$OLD_COLOR" \
    -f docker-compose.app.yml down || true
else
  WEB_PORT="$OLD_PORT" docker compose \
    -p "community_savings_$OLD_COLOR" \
    -f docker-compose.app.yml down || true
fi

log "♻️ Updating Celery workers..."
docker compose -f docker-compose.workers.yml \
  --env-file "$NEW_ENV_FILE" \
  up -d --build --force-recreate

log "🧹 Cleaning unused Docker images..."
docker image prune -f

trap - ERR

log "✅ Safe blue-green deployment completed successfully!" 