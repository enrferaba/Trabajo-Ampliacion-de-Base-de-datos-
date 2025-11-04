PROJECT_NAME=biblioteca-abd

.PHONY: up down logs test lint format seed

up:
docker compose up -d --build

down:
docker compose down -v

logs:
docker compose logs -f

test:
docker compose run --rm web pytest

lint:
docker compose run --rm web pre-commit run --all-files

format:
docker compose run --rm web black . && docker compose run --rm web isort .

seed:
docker compose run --rm web python manage.py seed_data
