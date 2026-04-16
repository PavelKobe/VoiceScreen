# Настройка переменных окружения (.env)

```bash
cp .env.example .env
```

Заполни каждую секцию по инструкции ниже.

---

## 1. OpenRouter (LLM)

Используем OpenRouter как единый шлюз к моделям (GPT-4o-mini, Claude, Gemini и др.)

**Где получить:**
1. Зайди на https://openrouter.ai/
2. Зарегистрируйся (Google/GitHub)
3. Перейди в https://openrouter.ai/keys → **Create Key**
4. Скопируй ключ `sk-or-v1-...`

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=google/gemini-2.5-flash-preview
```

**Выбор модели** — меняй `OPENROUTER_MODEL`:
| Модель | ID для .env | Цена (input/output за 1M токенов) |
|---|---|---|
| Gemini 2.5 Flash | `google/gemini-2.5-flash-preview` | Дёшево, быстро |
| GPT-4o-mini | `openai/gpt-4o-mini` | ~$0.15 / $0.60 |
| Claude Haiku 4.5 | `anthropic/claude-haiku-4.5` | ~$0.80 / $4.00 |
| Claude Sonnet 4 | `anthropic/claude-sonnet-4` | ~$3.00 / $15.00 |

Актуальные цены: https://openrouter.ai/models

---

## 2. Yandex Cloud (SpeechKit STT + TTS)

**Где получить:**
1. Зайди в https://console.yandex.cloud/
2. Создай платёжный аккаунт (есть грант ~4000 руб. для новых)
3. Создай каталог (folder) → скопируй **Folder ID**
4. Перейди в **Сервисные аккаунты** → создай аккаунт с ролями `ai.speechkit-stt.user` + `ai.speechkit-tts.user`
5. Создай **API-ключ** для этого сервисного аккаунта

```env
YANDEX_CLOUD_API_KEY=AQVNxxxxxxxxxxxx
YANDEX_CLOUD_FOLDER_ID=b1gxxxxxxxxxxxx
```

**Документация:** https://yandex.cloud/ru/docs/speechkit/

---

## 3. Telegram Bot

**Где получить:**
1. Открой Telegram, найди @BotFather
2. Отправь `/newbot`
3. Введи имя бота (например: `VoiceScreen Bot`)
4. Введи username (например: `voicescreen_bot`)
5. Скопируй токен

```env
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 4. Mango Office (телефония)

**Где получить:**
1. Зайди на https://www.mango-office.ru/
2. Зарегистрируйся, подключи тариф (от 2500 руб./мес, есть тестовый период)
3. В личном кабинете → **Интеграции** → **API** → получи API Key + Secret
4. Там же → **Номера** → скопируй свой номер

```env
MANGO_API_KEY=xxxxxxxxxxxx
MANGO_API_SECRET=xxxxxxxxxxxx
MANGO_FROM_NUMBER=74951234567
```

**Документация API:** https://www.mango-office.ru/support/api/

**Альтернатива на старте:** Novofon (Zadarma) — дешевле, API проще. Можно начать без Mango, подключить позже.

---

## 5. Yandex Object Storage (S3 для записей)

**Где получить:**
1. В том же Yandex Cloud → **Object Storage** → создай бакет `voicescreen-recordings`
2. Сервисный аккаунт → роль `storage.editor`
3. Создай **статический ключ доступа** (Access Key + Secret Key)

```env
YOS_ACCESS_KEY=YCAJExxxxxxxxxxxx
YOS_SECRET_KEY=YCPxxxxxxxxxxxx
YOS_BUCKET=voicescreen-recordings
YOS_ENDPOINT=https://storage.yandexcloud.net
```

---

## 6. Database + Redis

По умолчанию — локальный Docker. Менять не нужно, если используешь `make db-up`.

```env
DATABASE_URL=postgresql+asyncpg://voicescreen:devpassword@localhost:5432/voicescreen
POSTGRES_PASSWORD=devpassword
REDIS_URL=redis://localhost:6379/0
```

---

## Порядок получения ключей (что делать первым)

| # | Сервис | Время | Нужно для |
|---|---|---|---|
| 1 | OpenRouter | 2 мин | Тестирование диалогов без звонков |
| 2 | Telegram Bot | 2 мин | Интерфейс для HR-клиентов |
| 3 | Yandex Cloud | 10 мин | STT/TTS + Object Storage |
| 4 | Mango Office | 1–2 дня | Реальные звонки (можно отложить) |

**Минимум для первого запуска:** OpenRouter + Telegram. Остальное можно подключить позже.
