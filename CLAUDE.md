# CLAUDE.md — VoiceScreen MVP

> Этот файл читается Claude Code при работе с репозиторием. Сохраняй его в актуальном виде.

## Что это

**VoiceScreen** — голосовой AI-агент для первичного скрининга кандидатов на массовых позициях (курьеры, кассиры, комплектовщики). Клиент (HR) загружает список откликов — агент обзванивает, задаёт анкету, возвращает шорт-лист.

## Стадия проекта

MVP, part-time разработка. **Оптимизация — на скорость MVP, а не на архитектурную чистоту.** Упрощения приветствуются, преждевременные абстракции — нет.

## Технологический стек

- **Язык:** Python 3.11
- **Веб-фреймворк:** FastAPI + Uvicorn
- **БД:** PostgreSQL 15 (через SQLAlchemy 2.x async)
- **Очереди:** Redis + Celery
- **STT:** Yandex SpeechKit (streaming)
- **LLM:** OpenRouter (шлюз к моделям: Gemini Flash, GPT-4o-mini, Claude Haiku и др.)
- **TTS:** Yandex SpeechKit (голоса `alena`, `ermil`)
- **Телефония:** Voximplant (VoxEngine-сценарий + WebSocket-стриминг аудио)
- **Хранилище записей:** Yandex Object Storage (S3-совместимое)
- **Клиентский интерфейс на MVP:** Telegram-бот (веб-кабинет — позже)
- **Хостинг:** Yandex Cloud VM (`voicescreen`, 111.88.251.139), Ubuntu 24.04, Docker Compose

## Окружение разработки

Гибридный режим:

- **Claude Code CLI** и правки файлов — на домашнем Win11 (`c:\Users\kobel\VoiceScreen\VoiceScreen\`).
- **Выполнение** (docker, make, запуск приложения) — на VM через VS Code Remote-SSH (алиас `voicescreen`).
- **Синхронизация** — через git (`git@github.com:PavelKobe/VoiceScreen.git`): правим на Win11 → push → на VM pull.
- **.env** вне git, копируется через `scp` отдельно.

Причина: Anthropic API заблокирован из Yandex Cloud (РФ), поэтому Claude Code CLI нельзя запустить на VM. Приложение использует OpenRouter — он из РФ доступен, на VM всё работает.

## Структура репозитория

```text
voicescreen/
├── CLAUDE.md                  # ← ты здесь
├── pyproject.toml             # зависимости и конфиги инструментов
├── Makefile                   # все команды запуска
├── Dockerfile                 # сборка образа
├── docker-compose.yml         # Postgres + Redis + API + Worker + Bot
├── alembic.ini                # конфиг миграций
├── alembic/                   # Alembic миграции
├── .env.example               # шаблон переменных окружения
├── app/                       # основное приложение
│   ├── CLAUDE.md              # контекст приложения
│   ├── main.py                # FastAPI app
│   ├── config.py              # pydantic-settings
│   ├── api/                   # FastAPI роутеры
│   │   ├── candidates.py      # загрузка CSV, получение кандидата
│   │   ├── calls.py           # данные звонков, записи
│   │   └── webhooks.py        # вебхуки от Voximplant
│   ├── core/                  # ядро диалога
│   │   ├── CLAUDE.md          # контекст ядра
│   │   ├── stt.py             # Yandex SpeechKit STT
│   │   ├── tts.py             # Yandex SpeechKit TTS
│   │   ├── llm.py             # OpenAI GPT-4o-mini клиент
│   │   ├── scenario.py        # загрузчик YAML-сценариев
│   │   ├── dialog.py          # оркестратор диалога
│   │   └── prompts/           # промпты для LLM
│   ├── telephony/             # интеграция с Voximplant
│   │   ├── CLAUDE.md          # контекст телефонии
│   │   ├── voximplant.py      # Management API клиент (создание звонков)
│   │   └── voxengine/         # JS-сценарии для VoxEngine
│   │       └── screening.js   # диалог: connect → WebSocket stream → hangup
│   ├── db/                    # БД
│   │   ├── CLAUDE.md          # контекст БД
│   │   ├── models.py          # SQLAlchemy модели
│   │   └── session.py         # async session factory
│   ├── workers/               # фоновые задачи
│   │   ├── CLAUDE.md          # контекст воркеров
│   │   ├── celery_app.py      # конфиг Celery
│   │   └── tasks.py           # задачи: звонки, финализация
│   └── bot/                   # Telegram-бот для HR
│       ├── CLAUDE.md          # контекст бота
│       ├── __main__.py        # точка входа
│       └── handlers.py        # команды бота
├── scenarios/                 # YAML-анкеты для вакансий
│   └── courier_screening.yaml # пример: скрининг курьера
├── scripts/                   # CLI-утилиты
│   └── test_call.py           # отладочный звонок
└── docs/                      # планирующие документы
```

## Команды

```bash
make install       # pip install + pre-commit hooks
make db-up         # поднять Postgres + Redis в Docker
make db-migrate    # накатить миграции Alembic
make dev           # запустить API в режиме разработки
make worker        # запустить Celery-воркер
make bot           # запустить Telegram-бот
make test          # pytest
make test-call     # сделать отладочный звонок
make format        # ruff + black
make lint          # проверка кода
```

## Конвенции кода

- **Async везде**, где делаем I/O. SQLAlchemy 2.x async, httpx async, FastAPI async.
- **Типизация строгая.** Все публичные функции с аннотациями.
- **Форматирование:** `ruff` + `black` (конфиги в `pyproject.toml`).
- **Логирование:** `structlog` в JSON-формате. Не использовать `print()`.
- **Секреты:** только через переменные окружения и `pydantic-settings`. Никогда не коммитить `.env`.
- **Ошибки внешних API:** всегда с retry через `tenacity` (3 попытки, экспоненциальный backoff).
- **Миграции БД:** только через Alembic.

## Что НЕ делать (сознательные упрощения MVP)

- Не добавлять Kubernetes / service mesh. Docker Compose достаточно.
- Не писать свой STT/TTS. Только API.
- Не делать микросервисы. Один монолит, один Dockerfile.
- Не добавлять GraphQL. REST + webhooks.
- Не добавлять фронтенд-кабинет. На MVP только Telegram-бот.
- Не абстрагировать LLM/STT/TTS в интерфейсы без второй реализации.

## Критичные вещи

1. Первая фраза агента обязана содержать уведомление о записи и opt-out (152-ФЗ).
2. Логирование транскриптов — в БД сразу по ходу диалога.
3. Rate-limit: не более 3 попыток на кандидата, 9:00–21:00 локально.
4. Промпты для LLM живут в `app/core/prompts/` и `scenarios/`, не в коде.

## Текущий приоритет

**Сквозной звонок с YAML-анкетой и записью в БД.** Всё остальное — после.

## Прогресс

См. `ROADMAP.md` — чекбоксы обновляются по мере выполнения задач. Фаза 0 (скелет) завершена.
