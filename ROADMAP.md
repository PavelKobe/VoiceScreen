# ROADMAP — VoiceScreen MVP

> Обновляется по мере выполнения задач. Чекбоксы = реальный прогресс.

---

## Фаза 0: Скелет проекта

- [x] Структура репозитория (app/, scenarios/, scripts/, docs/)
- [x] pyproject.toml, Makefile, Dockerfile, docker-compose.yml
- [x] .env.example с переменными окружения
- [x] Alembic — async конфиг миграций
- [x] SQLAlchemy модели: Client, Vacancy, Candidate, Call, CallTurn
- [x] FastAPI — main.py + healthcheck + роутеры (candidates, calls, webhooks)
- [x] Ядро: stt.py, tts.py, llm.py, scenario.py, dialog.py
- [x] Mango Office API клиент (originate, hangup, verify) — будет заменён на Voximplant (см. Фазу 1)
- [x] Celery + Redis — задачи (initiate_call, finalize_call, schedule_pending)
- [x] Telegram-бот — скелет команд (/start, /register, /upload, /status, /report)
- [x] YAML-сценарий: courier_screening.yaml (7 вопросов)
- [x] Скрипт test_call.py
- [x] CLAUDE.md на каждом уровне (7 шт.)
- [x] Git-репозиторий инициализирован

---

## Фаза 1: Рабочий сквозной звонок (Неделя 2–3)

- [x] .env заполнен реальными ключами — OpenRouter, Yandex SpeechKit, Voximplant, Yandex S3 (ключи готовы; Telegram отложен из-за блока YC→api.telegram.org)
- [x] Миграция телефонии Mango → Voximplant: `voximplant.py`, `voxengine/screening.js`, webhooks и Celery-таски обновлены (b1c3d4e5f601)
- [x] `make install` — зависимости установлены
- [x] `make db-up` — Postgres + Redis запущены
- [x] Первая Alembic миграция (autogenerate из моделей)
- [x] `make dev` — API стартует без ошибок
- [x] Voximplant WebSocket — VoxEngine открывает WS к `/api/v1/ws/call`, протокол start/user_text/say/hangup работает
- [x] Audio pipeline: ASR в VoxEngine → текст → LLM → TTS Yandex Alena (через VoxEngine `call.say`) — сквозняк работает
- [ ] Object Storage: загрузка записей в Yandex S3 с signed URLs (сейчас храним Voximplant signed URL)
- [x] Сквозной тестовый звонок — реальный live-call 2026-04-25 через `/upload?start=true` отработал end-to-end
- [x] Логирование call_turns в БД по ходу диалога (не в конце) — `_append_turn` пишется на каждый turn в `ws.py`

---

## Фаза 2: Пилотная готовность (Неделя 3–4)

- [x] HTTP API `/candidates/upload` — bulk-загрузка xlsx/csv с auth по `X-API-Key`, нормализацией телефона, дедупом и опциональным авто-обзвоном (`?start=true`). Прогнан live-test 2026-04-25.
- [x] X-API-Key auth + tenant-scoping на `/calls` и `/candidates` через JOIN на `Vacancy.client_id`.
- [ ] Минимальный CRUD: `POST /clients` (генерит api_key), `POST /vacancies` — чтобы перестать создавать через psql.
- [ ] Telegram-бот: `/register` — создание Client в БД (заблокирован YC→api.telegram.org, обход не выбран)
- [ ] Telegram-бот: `/upload` — парсинг CSV, создание Candidate записей (та же блокировка)
- [ ] Telegram-бот: уведомления о прошедших скрининг (автоматом после finalize_call)
- [ ] `finalize_call` task: скачать запись в S3, уведомить HR (scoring + recording_url уже работают отдельно)
- [ ] Таймзоны: учёт часового пояса кандидата в schedule_pending_calls
- [ ] Rate-limit: max 3 попытки, 9:00–21:00 по местному времени
- [ ] Автодозвон: повторный звонок при занято/недоступно
- [ ] QA: 50 тестовых звонков (друзья, коллеги, сам себе)
- [ ] **АОН-брендинг номера** (антиспам): подать заявку в Яндекс АОН (voice-promotion.ru), Kaspersky Who Calls, GetContact Business — чтобы `+74951086575` определялся как «Рога и Олеся», а не «Спам». Без брендинга ответ-рейт будет в разы ниже.
- [ ] **ЧЕКПОИНТ:** Call Completion Rate >= 50%

---

## Фаза 3: Первый пилот с клиентом (Неделя 4)

- [ ] Клиент найден и согласился на пилот
- [ ] Конфиг сценария под реальную вакансию клиента
- [ ] Запуск на реальных кандидатах
- [ ] Ежедневный ручной QA всех звонков
- [ ] Итерации промптов каждый день
- [ ] **ЧЕКПОИНТ:** клиент говорит «полезно»

---

## Фаза 4: Продуктовые улучшения (Дни 31–60)

- [ ] Веб-кабинет (Next.js) — таблица кандидатов + плеер записей
- [ ] Интеграция с hh.ru API (автоимпорт откликов)
- [ ] Экспорт в Excel / Google Sheets
- [ ] Несколько вакансий у одного клиента
- [ ] Гибкое расписание обзвона (рабочие часы + часовой пояс)
- [ ] Кейс первого пилота в PDF (метрики до/после)
- [ ] **ЧЕКПОИНТ:** MRR >= 80 000 ₽, подписан минимум 1 контракт на 3+ мес

---

## Фаза 5: Масштабирование до $3–4k MRR (Дни 61–90)

- [ ] Партнёрская программа с кадровыми агентствами (20% от MRR)
- [ ] Шаблоны анкет под вертикали (доставка, розница, склады)
- [ ] Webhook-интеграция с CRM (Bitrix24, amoCRM)
- [ ] White-label для кадровых агентств
- [ ] A/B тесты голосов и формулировок
- [ ] Аналитика по вакансии (% завершения, точки обрыва)
- [ ] **ЧЕКПОИНТ:** MRR $3 000–4 000, 10–15 платящих клиентов, churn <= 10%

---

## Нетехнические задачи (параллельно)

- [ ] ИП / ООО открыто, расчётный счёт работает
- [ ] Уведомление в Роскомнадзор подано
- [ ] Политика обработки ПДн опубликована на сайте
- [ ] Типовой договор поручения готов
- [ ] Оферта опубликована
- [ ] Номер зарегистрирован на ИП (Voximplant)
- [ ] Список из 30 компаний-кандидатов на пилот
- [ ] 10 холодных сообщений HRD отправлено
- [ ] 5 глубоких интервью с HR массового найма проведено
