# VoiceScreen

Голосовой AI-агент для скрининга кандидатов на массовых позициях.

## Быстрый старт

### 1. Требования
- Python 3.11+
- Docker + Docker Compose
- Аккаунты: Yandex Cloud (SpeechKit), OpenAI, Mango Office, Telegram Bot API

### 2. Установка

```bash
git clone <repo>
cd voicescreen
cp .env.example .env
# заполни .env своими ключами
make install
make db-up
make db-migrate
```

### 3. Отладочный звонок

```bash
# В одном терминале:
make dev

# В другом терминале:
make worker

# В третьем (для тестового звонка на свой номер):
make test-call PHONE=+79991234567 SCENARIO=courier_screening
```

### 4. Telegram-бот для клиента

```bash
make bot
```

Отправь `/start` боту — он покажет меню загрузки кандидатов и получения отчётов.

## Структура проекта

Смотри `CLAUDE.md` в корне и подкаталогах.

## Документация

- `docs/ROADMAP.md` — план разработки
- `docs/PLANNING.md` — стратегия, продажи, юнит-экономика
- `docs/LEGAL.md` — 152-ФЗ и правовые требования

## Статус

🚧 MVP в разработке. Следующая веха: сквозной звонок с YAML-анкетой.
