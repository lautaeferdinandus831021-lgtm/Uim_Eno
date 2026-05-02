.PHONY: dev up down logs test setup deploy

dev:
	docker compose -f infra/docker/docker-compose.yml up -d postgres redis
	sleep 2
	cd backend && PYTHONPATH=.. uvicorn app.main:app --reload --port 8000 &
	cd worker && PYTHONPATH=.. celery -A worker.app.celery_app worker --loglevel=info &
	cd frontend && npm run dev

up:
	docker compose -f infra/docker/docker-compose.yml up -d --build

down:
	docker compose -f infra/docker/docker-compose.yml down

logs:
	docker compose -f infra/docker/docker-compose.yml logs -f

setup:
	bash infra/scripts/setup.sh

deploy:
	bash infra/scripts/deploy.sh

test:
	cd backend && PYTHONPATH=.. pytest ../tests/ -v
