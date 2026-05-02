#!/bin/bash
set -e
echo "=== BG-BOT v5 Setup ==="
[ ! -f .env ] && cp .env.example .env && echo "Created .env"
cd backend && pip install -r requirements.txt && cd ..
cd worker && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..
echo "=== Setup complete ==="
