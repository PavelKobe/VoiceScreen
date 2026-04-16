# CLAUDE.md — app/

Основной пакет приложения VoiceScreen.

## Структура

- `main.py` — FastAPI application, точка входа для `uvicorn`
- `config.py` — все настройки через `pydantic-settings`, читает `.env`
- `api/` — HTTP-эндпоинты (REST)
- `core/` — ядро: STT, TTS, LLM, оркестратор диалога
- `telephony/` — интеграция с телефонией (Mango Office)
- `db/` — SQLAlchemy модели и сессии
- `workers/` — Celery-задачи для фоновой обработки
- `bot/` — Telegram-бот для HR-клиентов

## Правила

- Весь I/O — async (httpx, SQLAlchemy async, aiogram).
- Логирование только через `structlog`, не `print()`.
- Секреты — только из `settings` (`app.config`), не хардкодить.
- Внешние API вызывать с `tenacity` retry.
- Новые модули добавлять как подпакеты с `__init__.py`.
