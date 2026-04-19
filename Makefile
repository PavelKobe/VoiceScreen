.PHONY: install db-up db-down db-migrate dev worker bot test test-call format lint sync

install:
	pip install -e ".[dev]"
	pre-commit install

db-up:
	docker compose up -d postgres redis

db-down:
	docker compose down

db-migrate:
	alembic upgrade head

db-revision:
	alembic revision --autogenerate -m "$(msg)"

sync:
	bash scripts/sync_vm.sh

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

bot:
	python -m app.bot

test:
	pytest -v

test-call:
	python scripts/test_call.py --phone=$(PHONE) --scenario=$(SCENARIO)

format:
	ruff check --fix .
	black .

lint:
	ruff check .
	black --check .
	mypy app/
