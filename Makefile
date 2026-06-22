.PHONY: up build down start lint format typecheck test seed check

# Docker
build:
	docker compose build

up:
	docker compose up -d

start:
	docker compose up --build -d

down:
	docker compose down

# Backend quality
lint:
	uv run ruff check app tests

format:
	uv run ruff format app tests

typecheck:
	uv run mypy app

test:
	uv run pytest --cov=app

# Data
seed:
	uv run python scripts/seed.py

# Run all checks in one shot
check: format lint typecheck test
