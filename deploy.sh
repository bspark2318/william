#!/bin/bash
set -e

PI_HOST="pi@192.168.1.234"
PI_DIR="/home/pi/Deployment/william"
CONTAINERS="william-backend william-frontend cloudflared-william"

echo "=== Building ARM64 backend ==="
docker build -t bspark2318/william-backend:arm64 --platform linux/arm64 -f backend/Dockerfile backend

echo "=== Building ARM64 frontend ==="
docker build -t bspark2318/william-frontend:arm64 --platform linux/arm64 -f frontend/Dockerfile frontend

echo "=== Pushing to Docker Hub ==="
docker push bspark2318/william-backend:arm64
docker push bspark2318/william-frontend:arm64

echo "=== Syncing config to Raspberry Pi ==="
ssh "$PI_HOST" "mkdir -p \"$PI_DIR\""
scp docker-compose.yml "$PI_HOST:$PI_DIR/"

echo "=== Deploying to Raspberry Pi ==="
ssh "$PI_HOST" "cd $PI_DIR && \
  mkdir -p data; \
  sudo chown -R 1000:1000 data; \
  sudo chmod -R u+rwX data; \
  docker stop $CONTAINERS 2>/dev/null || true; \
  docker rm $CONTAINERS 2>/dev/null || true; \
  docker pull bspark2318/william-backend:arm64 && \
  docker pull bspark2318/william-frontend:arm64 && \
  docker compose up -d --force-recreate && \
  docker image prune -f"
