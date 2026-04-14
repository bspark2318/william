#!/bin/bash
set -e

PI_HOST="pi@192.168.1.234"
PI_DIR="/home/pi/Deployment/william"
CONTAINERS="william-backend william-frontend cloudflared-william"

echo "=== Syncing config to Raspberry Pi ==="
ssh "$PI_HOST" "mkdir -p \"$PI_DIR\""
scp docker-compose.yml "$PI_HOST:$PI_DIR/"

echo "=== Deploying to Raspberry Pi ==="
ssh "$PI_HOST" "cd $PI_DIR && \
  mkdir -p data; \
  rm -f data/newsletter.db; \
  sudo chown -R 1000:1000 data; \
  sudo chmod -R u+rwX data; \
  docker compose pull && \
  docker compose up -d --force-recreate && \
  docker image prune -f"
