# CLAUDE.md — app/telephony/

Интеграция с телефонией (Voximplant).

## Модули

- `voximplant.py` — клиент Voximplant Management API: инициация звонка через `StartScenarios` (`originate_call`), завершение через `StopScenarios` (`hangup_call`).
- `voxengine/screening.js` — JS-сценарий для VoxEngine: дозвон кандидату, открытие WebSocket к нашему backend, воспроизведение TTS, hangup по команде.

## Правила

- Используем только реальные, зарегистрированные номера. Подменные запрещены.
- Воксэнжин-сценарии лежат в `voxengine/` и деплоятся отдельно в Voximplant (через UI или API).
- ID звонка в БД — `voximplant_call_id` (по факту `call_session_history_id`).
- Вебхуки Voximplant / HTTP-колбэки из VoxEngine приходят в `app/api/webhooks.py`, здесь только клиент API.
- При добавлении нового провайдера — сначала обсуждение, не код.

## TODO

- Реализовать WebSocket-эндпоинт на FastAPI (`app/api/ws.py`) для приёма аудио из VoxEngine.
- Стриминг из WebSocket в SpeechKit STT и обратно TTS-ответов в звонок.
