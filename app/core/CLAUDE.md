# CLAUDE.md — app/core/

Ядро диалоговой системы VoiceScreen.

## Модули

- `stt.py` — Yandex SpeechKit STT. Распознавание речи кандидата.
- `tts.py` — Yandex SpeechKit TTS. Синтез голоса агента (голос `alena`).
- `llm.py` — LLM клиент через OpenRouter (OpenAI-совместимый API). Модель настраивается в `.env`.
- `scenario.py` — загрузчик YAML-сценариев из `scenarios/`, построение system prompt.
- `dialog.py` — `DialogSession` — оркестратор одного разговора. Управляет очерёдностью, историей, завершением.
- `prompts/` — шаблоны промптов (пока генерируются динамически в `scenario.py`).

## Критичные правила

- **Перед изменением `dialog.py`** — прогнать `make test-call` до и после.
- System prompt генерируется из YAML-сценария, не хардкодится.
- Все вызовы внешних API (STT/TTS/LLM) — с retry через `tenacity`.
- Латентность полного круга STT -> LLM -> TTS должна быть < 1.5 сек.

## Поток данных одного звонка

```text
Audio in -> stt.recognize_audio() -> text
text + history -> llm.get_next_reply() -> reply text
reply text -> tts.synthesize_speech() -> audio out
```
