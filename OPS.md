# VoiceScreen — Operations Cheatsheet

Гибридный setup: разработка на Win11 (Claude Code, git), исполнение на Yandex Cloud VM через VS Code Remote-SSH. Всё боевое — в Docker Compose на VM.

> Секретов в этом файле нет. Все ключи — в `.env` на VM (gitignored).

---

## 1. Доступ к VM

```bash
ssh ubuntu@voicescreen   # alias настроен в ~/.ssh/config
```

Рабочая директория на VM: `~/VoiceScreen`.

`/etc/hosts` на VM содержит маппинг `postgres → 127.0.0.1`, `redis → 127.0.0.1` — нужно для запуска alembic/uvicorn/celery вне Docker.

---

## 2. Структура проекта

```
~/VoiceScreen/
├── app/
│   ├── api/              # FastAPI роутеры
│   │   ├── deps.py       # auth: get_current_client (X-API-Key), require_admin (X-Admin-Key)
│   │   ├── router.py     # сборка всех роутеров под /api/v1
│   │   ├── clients.py    # POST /clients (admin)
│   │   ├── vacancies.py  # POST /vacancies (client)
│   │   ├── candidates.py # POST /upload, GET /{id}
│   │   ├── calls.py      # GET /calls, GET /calls/{id}, GET /calls/{id}/recording
│   │   ├── webhooks.py   # Voximplant callbacks
│   │   └── ws.py         # WebSocket /ws/call (VoxEngine ↔ backend)
│   ├── core/             # dialog, llm, stt, tts, scoring
│   ├── db/               # session.py, models.py
│   ├── workers/          # Celery (initiate_call и др.)
│   ├── bot/              # Telegram bot (aiogram)
│   ├── telephony/        # Voximplant integration
│   ├── config.py         # pydantic-settings
│   └── main.py           # FastAPI app entrypoint
├── alembic/              # миграции
├── files/                # шаблоны (candidates_template.xlsx)
├── scripts/              # утилиты (make_candidates_template.py)
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env                  # секреты (не коммитить!)
```

Префикс API: `/api/v1` (через nginx наружу — `https://voxscreen.ru/api/v1/...`).

---

## 3. Docker Compose

### Сервисы

| Сервис   | Что делает                          | Порт  |
|----------|-------------------------------------|-------|
| api      | uvicorn + FastAPI (`--reload`)      | 8000  |
| worker   | Celery воркер                       | —     |
| bot      | Telegram bot (aiogram)              | —     |
| postgres | PostgreSQL 15                       | 5432  |
| redis    | Redis 7 (брокер Celery + кэш)       | 6379  |

Код примонтирован volume'ом `./:/app` — uvicorn `--reload` подхватывает изменения без рестарта контейнера.

### Команды

```bash
cd ~/VoiceScreen

# Поднять всё
docker compose up -d

# Остановить всё
docker compose down

# Перезапустить только api (без пересборки)
docker compose restart api

# Пересобрать образ (нужно при изменении pyproject.toml/Dockerfile)
docker compose up -d --build api worker bot

# Состояние контейнеров
docker compose ps

# Логи
docker compose logs --tail=50 api
docker compose logs -f api          # follow
docker compose logs --tail=200 api | grep -viE "wp-admin|wordpress|PROPFIND"  # без ботов-сканеров
```

### Заглянуть внутрь контейнера

```bash
docker compose exec api bash
docker compose exec postgres psql -U voicescreen -d voicescreen
docker compose exec redis redis-cli
```

---

## 4. БД и миграции

### Подключиться к Postgres

С VM-хоста (через смапленый /etc/hosts):
```bash
psql -h postgres -U voicescreen -d voicescreen
# пароль: devpassword (см. .env)
```

Из контейнера:
```bash
docker compose exec postgres psql -U voicescreen -d voicescreen
```

### Применить миграции

```bash
source .venv/bin/activate
# дождаться pg_isready, если только что подняли postgres
until pg_isready -h postgres -U voicescreen; do sleep 1; done
make db-migrate    # alembic upgrade head
```

### Создать новую миграцию

```bash
source .venv/bin/activate
alembic revision --autogenerate -m "описание"
# проверить сгенерированный файл, потом:
make db-migrate
```

---

## 5. Workflow редактирования

### Вариант A — правка прямо на VM (для мелких правок)

```bash
ssh ubuntu@voicescreen
cd ~/VoiceScreen
nano app/api/clients.py
# uvicorn --reload подхватит автоматически
git add ... && git commit && git push
```

### Вариант B — Win11 → git → VM (для больших изменений)

```bash
# на Win11
cd c:\Users\kobel\VoiceScreen
# правки в редакторе
git add ... && git commit && git push

# на VM
cd ~/VoiceScreen
git pull --ff-only
# uvicorn --reload подхватит
```

### `.env` и CRLF

После `scp .env` с Win11 на VM — почистить `\r`:
```bash
sed -i 's/\r$//' .env
```
(Если правишь nano прямо на VM — `\r` не появятся.)

---

## 6. Pre-commit hooks

Установлены: `ruff` (lint), `ruff-format`, `trim trailing whitespace`, `fix end of files`, `check yaml`, `check for added large files`.

Если коммит падает на хуках:
1. **`ruff` — `B008` `Depends in defaults`** — не должно случаться, в `pyproject.toml` есть `extend-immutable-calls` для FastAPI.
2. **`ruff-format` reformatted** — хук переформатировал файл, но не застейджил. Просто `git add <file>` и коммит ещё раз.
3. **`E501` Line too long** — разнеси длинную строку (для декораторов FastAPI — multi-line).

Никогда не используй `--no-verify` для обхода — лучше понять, что сломалось.

---

## 7. Онбординг нового клиента (runbook)

Сценарий: с нуля до первого обзвона. Все шаги — на VM с `~/VoiceScreen` или с любой машины через `https://voxscreen.ru/api/v1`. Нужен `ADMIN_API_KEY` из `.env`.

### Шаг 1. Создать клиента (admin)

```bash
curl -X POST https://voxscreen.ru/api/v1/clients \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"ООО Ромашка","tariff":"start"}'
```

Ответ содержит `api_key` — **сохрани его сразу**, второй раз не отдадим.

```bash
export CLIENT_API_KEY='<тот_что_пришёл>'
```

### Шаг 2. Передать `api_key` клиенту

Любым защищённым каналом (зашифрованный архив / сообщение, удаляемое после прочтения). Не Telegram-чат.

### Шаг 3. Создать вакансию

Можно за клиента (если онбординг ручной), либо клиент сам:

```bash
curl -X POST https://voxscreen.ru/api/v1/vacancies \
  -H "X-API-Key: $CLIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Курьер","scenario_name":"courier_screening","pass_score":6.0}'
```

`scenario_name` валидируется по содержимому каталога `scenarios/*.yaml` — неизвестное имя даст 400 с перечислением допустимых. Сейчас доступен только `courier_screening`. Запиши `id` вакансии из ответа.

```bash
export VACANCY_ID=<id>
```

### Шаг 4. Подготовить файл кандидатов

Шаблон: `files/candidates_template.xlsx` (или csv). Колонки:

- `phone` — формат `+7XXXXXXXXXX`
- `fio` — ФИО полностью
- `source` *(опционально)* — откуда отклик (`hh`, `avito`, …)

### Шаг 5. Загрузить кандидатов (без обзвона)

```bash
curl -X POST "https://voxscreen.ru/api/v1/candidates/upload?vacancy_id=$VACANCY_ID&start=false" \
  -H "X-API-Key: $CLIENT_API_KEY" \
  -F "file=@candidates.xlsx"
# → {"created":N, "duplicates":N, "invalid":[...], "enqueued":0}
```

Проверить, что `invalid` пуст. Если нет — поправить файл и перезалить (дубли по телефону отсеются автоматически).

### Шаг 6. Запустить обзвон

Опция A — пнуть Celery-таски на всех `pending` кандидатов вакансии (рекомендуется для контроля):

```bash
docker compose exec api python -c \
  "from app.workers.tasks import initiate_call; \
   import asyncio; from app.db.session import async_session; \
   from app.db.models import Candidate; \
   from sqlalchemy import select; \
   async def run(): \
     async with async_session() as s: \
       cs = (await s.execute(select(Candidate).where(Candidate.vacancy_id==$VACANCY_ID, Candidate.status=='pending'))).scalars().all(); \
       for c in cs: initiate_call.delay(c.id); \
       print(f'enqueued {len(cs)}'); \
   asyncio.run(run())"
```

Опция B — `start=true` при upload (`...&start=true`) — обзвон стартует сразу. Удобно, но не даёт сверить файл перед звонками.

### Шаг 7. Мониторинг

```bash
# логи api в реальном времени
docker compose logs -f api

# список звонков по клиенту
curl "https://voxscreen.ru/api/v1/calls?limit=20" -H "X-API-Key: $CLIENT_API_KEY"

# детали звонка с транскриптом
curl "https://voxscreen.ru/api/v1/calls/<call_id>" -H "X-API-Key: $CLIENT_API_KEY"

# скачать запись
curl -L "https://voxscreen.ru/api/v1/calls/<call_id>/recording" \
  -H "X-API-Key: $CLIENT_API_KEY" -o rec.mp3
```

### Шаг 8. Корректировки вакансии

```bash
# поднять/опустить порог
curl -X PATCH https://voxscreen.ru/api/v1/vacancies/$VACANCY_ID \
  -H "X-API-Key: $CLIENT_API_KEY" -H "Content-Type: application/json" \
  -d '{"pass_score":7.0}'

# переименовать
curl -X PATCH https://voxscreen.ru/api/v1/vacancies/$VACANCY_ID \
  -H "X-API-Key: $CLIENT_API_KEY" -H "Content-Type: application/json" \
  -d '{"title":"Курьер пеший (Москва)"}'

# деактивировать (soft delete; новые звонки не ставятся)
curl -X DELETE https://voxscreen.ru/api/v1/vacancies/$VACANCY_ID \
  -H "X-API-Key: $CLIENT_API_KEY"

# вернуть в активные
curl -X PATCH https://voxscreen.ru/api/v1/vacancies/$VACANCY_ID \
  -H "X-API-Key: $CLIENT_API_KEY" -H "Content-Type: application/json" \
  -d '{"active":true}'
```

### Шаг 9. Отчёт по вакансии

```bash
curl https://voxscreen.ru/api/v1/vacancies/$VACANCY_ID/report \
  -H "X-API-Key: $CLIENT_API_KEY"
# → {
#   "vacancy_id": ..., "title": ...,
#   "candidates_total": ..., "calls_total": ..., "calls_with_score": ...,
#   "by_decision": {"pass": N, "review": N, "reject": N},
#   "avg_score": 6.34
# }
```

`calls_total` — звонки с `finished_at`; `calls_with_score` — из них прошедшие LLM-оценку. `avg_score` усредняется только по scored. Если ни одного звонка ещё не было — `avg_score: null`, `by_decision: {}`.

### Чек-лист (распечатать перед запуском пилота)

- [ ] `ADMIN_API_KEY` под рукой
- [ ] Клиент создан, `api_key` сохранён в KeePass/1Password
- [ ] Вакансия создана, `pass_score` согласован с HR
- [ ] Файл кандидатов прошёл валидацию (`invalid: []`)
- [ ] Сделан 1 пробный звонок на свой номер (через `make test-call` или ручной upload одного кандидата с твоим номером + `start=true`)
- [ ] Запись и транскрипт пробного звонка прослушаны
- [ ] АОН-брендинг номера запущен / в процессе (иначе ответ-рейт просядет)
- [ ] Обзвон запущен, логи `docker compose logs -f api` смотрятся

---

## 8. Тестовые curl'ы

> Все примеры на `localhost:8000` — через VM-tunnel или с самой VM. Снаружи — `https://voxscreen.ru/api/v1/...`.

### Создать клиента (admin)

```bash
curl -X POST http://localhost:8000/api/v1/clients \
  -H "X-Admin-Key: <ADMIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name":"ClientName","tariff":"start"}'
# → 201 {"id":..., "name":..., "tariff":..., "api_key":"<СОХРАНИ>"}
```

`api_key` отдаётся **только при создании**. Если потерял — `POST /clients/{id}/rotate-key` (см. ниже).

### Перевыпустить api_key (admin)

```bash
curl -X POST http://localhost:8000/api/v1/clients/<id>/rotate-key \
  -H "X-Admin-Key: $ADMIN_API_KEY"
# → 200 {"id":..., "api_key":"<новый>"}
```

Старый ключ инвалидируется немедленно. Передать новый клиенту защищённым каналом.

### Создать вакансию (client)

```bash
curl -X POST http://localhost:8000/api/v1/vacancies \
  -H "X-API-Key: <api_key клиента>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Курьер","scenario_name":"courier_screening","pass_score":6.0}'
# → 201 {"id":..., "client_id":..., ...}
```

### Список / детали / правка вакансий

```bash
# список своих вакансий
curl "http://localhost:8000/api/v1/vacancies?active=true" -H "X-API-Key: <key>"

# одна вакансия
curl http://localhost:8000/api/v1/vacancies/<id> -H "X-API-Key: <key>"

# partial update (любая комбинация title/pass_score/active)
curl -X PATCH http://localhost:8000/api/v1/vacancies/<id> \
  -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d '{"pass_score":7.0}'

# soft delete (active=false, идемпотентно)
curl -X DELETE http://localhost:8000/api/v1/vacancies/<id> -H "X-API-Key: <key>"
```

### Загрузить кандидатов

```bash
curl -X POST "http://localhost:8000/api/v1/candidates/upload?vacancy_id=<id>&start=false" \
  -H "X-API-Key: <api_key клиента>" \
  -F "file=@candidates.xlsx"
# → 200 {"created":..., "duplicates":..., "invalid":[...], "enqueued":...}
```

`start=true` сразу пнёт обзвон через Celery (нужен поднятый worker и Voximplant).

### Получить кандидата

```bash
curl http://localhost:8000/api/v1/candidates/<id> \
  -H "X-API-Key: <api_key клиента>"
```

### Список звонков / запись

```bash
curl "http://localhost:8000/api/v1/calls?limit=10" -H "X-API-Key: <key>"
curl "http://localhost:8000/api/v1/calls/<id>" -H "X-API-Key: <key>"
curl -L "http://localhost:8000/api/v1/calls/<id>/recording" -H "X-API-Key: <key>" -o rec.mp3
```

### Негативные кейсы (sanity)

```bash
# 401: missing X-API-Key
curl -i -X POST http://localhost:8000/api/v1/vacancies -H "Content-Type: application/json" -d '{"title":"x","scenario_name":"y"}'

# 403: invalid api key
curl -i -X POST http://localhost:8000/api/v1/vacancies -H "X-API-Key: nope" -H "Content-Type: application/json" -d '{"title":"x","scenario_name":"y"}'

# 403: invalid admin key
curl -i -X POST http://localhost:8000/api/v1/clients -H "X-Admin-Key: nope" -H "Content-Type: application/json" -d '{"name":"x"}'
```

---

## 9. VoxEngine сценарий (Voximplant)

Файл: `app/telephony/voxengine/screening.js`. Это **JS-код, который выполняется на стороне Voximplant**, не на нашем сервере. Он запускается их StartScenarios (rule привязан к приложению `voicescreen`).

### Поток звонка

1. `app/workers/tasks.py:initiate_call` → Voximplant API → стартует сценарий с `customData` (JSON: `to_number`, `candidate_id`, `scenario`, `ws_url`, `call_id`, `ws_auth_token`).
2. VoxEngine звонит на `to_number` через `callPSTN`.
3. На `Connected` — `call.record()` (запись для последующего fetch_recording) и открывает WS на наш бэкенд (`wss://voxscreen.ru/api/v1/ws/call`).
4. ASR — на стороне Voximplant через `ASRProfileList.Yandex.ru_RU`. Распознанный текст летит в WS как `{"type":"user_text", "text":...}`.
5. Бэкенд отвечает `{"type":"say", "text":...}` → VoxEngine озвучивает через `VoiceList.Yandex.Neural.ru_RU_alena` (Alena).
6. Бэкенд завершает диалог — шлёт `{"type":"hangup"}`, VoxEngine кладёт трубку.

### WS-протокол (между VoxEngine и нашим `app/api/ws.py`)

**VoxEngine → backend:**
- `{type:"start", call_id, candidate_id, scenario, to_number, ws_auth_token}` — первый кадр после открытия WS
- `{type:"user_text", text}` — фраза кандидата (после ASR)
- `{type:"call_ended", reason}` — звонок завершился (`disconnected` / `failed:<code>`)

**backend → VoxEngine:**
- `{type:"say", text}` — озвучить ответ агента
- `{type:"hangup"}` — завершить звонок

### Обновление сценария на Voximplant

Файл `screening.js` хранится в репе для версионирования, но **исполняется только в Voximplant**. После правки нужно вручную залить в их UI:

1. manage.voximplant.com → Applications → `voicescreen` → Scenarios
2. Найти сценарий, привязанный к нужной rule (см. `VOXIMPLANT_RULE_ID`).
3. Заменить код на актуальный из `screening.js`, сохранить.
4. Тестовый звонок через `initiate_call.delay(<candidate_id>)` или через `/upload?start=true`.

⚠️ **Не коммитить разные версии `screening.js` без синхронизации с Voximplant** — рассинхрон легко не заметить.

### Известные ограничения

- TTS на стороне Voximplant (Alena). Если упрёмся в их лимиты — fallback на наш SpeechKit через WS-стрим (см. комментарий в шапке `screening.js`).
- ASR `singleUtterance: false` — стрим, но партиалы мы не используем, только финальные `Result`.
- `record()` создаёт запись на стороне Voximplant; URL подтягивается через `fetch_recording` ретраем (см. `app/telephony/`).

---

## 10. Внешние сервисы

| Сервис             | Где                                        | Что хранит                          |
|--------------------|-------------------------------------------|-------------------------------------|
| Voximplant         | voximplant.com (VOXIMPLANT_*)             | приложение, rule, номер, сценарий   |
| Yandex SpeechKit   | YANDEX_CLOUD_API_KEY                      | TTS Alena, STT                       |
| Yandex Object Storage | YOS_*                                  | бакет с записями звонков            |
| OpenRouter         | OPENROUTER_API_KEY                        | LLM (`openai/gpt-4o-mini`, RU IP блочит google/*) |
| Telegram Bot       | TELEGRAM_BOT_TOKEN (через @BotFather)     | бот для оповещений                  |
| reg.ru             | домен `voxscreen.ru`                      | nginx + TLS                         |

⚠️ **`api.telegram.org` заблокирован с YC VM** — обход ещё не выбран. Бот не работает.

---

## 11. Типичные проблемы

### `ModuleNotFoundError` при старте api

Образ устарел — пересобрать:
```bash
docker compose up -d --build api worker bot
```

### `curl: Failed to connect to localhost port 8000`

Контейнер api не запущен или упал. Проверить:
```bash
docker compose ps
docker compose logs --tail=80 api
```

### Pydantic ругается на отсутствующее поле в Settings

В `app/config.py` для нового env'а нужно поле с типом и дефолтом:
```python
admin_api_key: str = ""
```
Иначе pydantic упадёт на старте.

### `uvicorn` не подхватывает изменения

- Проверь, что в `docker-compose.yml` для api есть `volumes: - .:/app` и команда c `--reload`.
- Иногда WatchFiles глючит на симлинках — рестартани: `docker compose restart api`.

### LLM возвращает 4xx

- Проверь `OPENROUTER_MODEL` в `.env` — для RU IP не используем `google/gemini-*`.
- Обычно работает `openai/gpt-4o-mini`.

---

## 12. Памятка по секретам

Все секреты — в `.env` на VM. **Никогда** не коммить `.env` и не выкладывай в чаты/issue/PR.

Список ключей и где ротейтить:
- `ADMIN_API_KEY` — генерируется локально (`secrets.token_urlsafe(32)`), правится в `.env`
- `WS_AUTH_TOKEN` — то же
- `OPENROUTER_API_KEY` — openrouter.ai → Keys
- `TELEGRAM_BOT_TOKEN` — `/revoke` через @BotFather
- `YANDEX_CLOUD_API_KEY` — Yandex Cloud Console → Service Accounts → Keys
- `YOS_ACCESS_KEY` / `YOS_SECRET_KEY` — там же, статические access keys
- `VOXIMPLANT_API_KEY` — manage.voximplant.com → Settings → API Keys

После ротации любого ключа:
1. Обновить `.env` на VM (`nano .env`)
2. `docker compose up -d` (compose подхватит новый env при перезапуске; `restart` иногда нет — лучше `up -d`)
3. Если ключ менялся для api — проверить, что `Application startup complete`

---

## 13. Полезные ссылки

- API внешний: `https://voxscreen.ru/api/v1`
- WS для VoxEngine: `wss://voxscreen.ru/api/v1/ws/call`
- Voximplant сценарий: см. `app/telephony/`
