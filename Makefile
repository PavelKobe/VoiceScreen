.PHONY: install db-up db-down db-migrate dev worker bot test simulate-dialog format lint sync \
	web-install web-dev web-build web-deploy

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

simulate-dialog:
	python scripts/simulate_dialog.py --phone=$(PHONE) --scenario=$(SCENARIO)

format:
	ruff check --fix .
	black .

lint:
	ruff check .
	black --check .
	mypy app/

# === Web (SPA) ===
web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

# Деплой статики на VM. Хост-алиас 'voicescreen' должен быть в ~/.ssh/config.
web-deploy: web-build
	rsync -avz --delete web/dist/ voicescreen:/var/www/voxscreen-app/
