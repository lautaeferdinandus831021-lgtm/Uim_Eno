#!/bin/bash
set -e
cd "$(dirname "$0")/../.."
docker compose -f infra/docker/docker-compose.yml up -d --build
echo "Frontend: http://localhost:3000"
echo "API:      http://localhost:8000"
echo "Health:   http://localhost:8000/health"
