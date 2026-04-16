# CLAUDE.md — app/db/

Слой базы данных VoiceScreen.

## Модули

- `models.py` — SQLAlchemy 2.x модели: `Client`, `Vacancy`, `Candidate`, `Call`, `CallTurn`.
- `session.py` — async session factory, FastAPI dependency `get_session`.

## Модели (схема)

```
clients (id, name, tg_chat_id, tariff, active)
  └── vacancies (id, client_id, title, scenario_name, pass_score, active)
       └── candidates (id, vacancy_id, phone, fio, source, status)
            └── calls (id, candidate_id, started_at, duration, recording_url, transcript, score, decision, attempt)
                 └── call_turns (id, call_id, speaker, text, audio_url, order)
```

## Правила

- Миграции только через Alembic (`make db-migrate`, `make db-revision msg="..."`)
- Все операции async через `AsyncSession`.
- Руками в БД ничего не менять.
