# CLAUDE.md — app/core/

Ядро диалоговой системы VoiceScreen.

## Модули

- `stt.py` — Yandex SpeechKit STT. Распознавание речи кандидата.
- `llm.py` — LLM клиент через OpenRouter (OpenAI-совместимый API). Используется ТОЛЬКО для финального scoring'а после звонка, не в петле turn'ов.
- `scenario.py` — загрузчик сценариев (DB + lazy seed из `scenarios/*.yaml`), `build_greeting`, `build_system_prompt` (для scoring'а).
- `dialog.py` — `DialogSession`: скриптовый FSM по списку вопросов. LLM не вызывается. Один failsafe-повтор на невнятный ASR.
- `scoring.py` — `score_call`: единственный LLM-вызов в звонке, делается после `call_ended`.
- `prompts/` — шаблоны промптов (пока генерируются динамически в `scenario.py`).

TTS делает Voximplant напрямую через `call.say(text, VoiceList.Yandex.Neural.ru_RU_alena)` в `app/telephony/voxengine/screening.js`. Бэкенд шлёт только текст.

## Критичные правила

- **Перед изменением `dialog.py`** — прогнать `make test-call` до и после.
- В петле звонка не должно быть сетевых LLM-вызовов: латентность ответа диктуется только ASR endpointing + Voximplant TTS (~500–800 мс).
- Финальный `score_call` использует `build_system_prompt` + полный transcript.

## Поток данных одного звонка

```text
Audio in -> Yandex ASR (Voximplant) -> user_text via WebSocket
user_text -> DialogSession.process_candidate_reply() -> next scripted question
reply text -> {"type":"say"} -> Voximplant call.say -> Yandex TTS
... (повторяется по списку вопросов) ...
call_ended -> score_call(scenario, transcript) -> persist score/decision
```
