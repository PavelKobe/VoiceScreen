# CLAUDE.md — app/workers/

Фоновые задачи на Celery.

## Модули

- `celery_app.py` — конфигурация Celery (брокер Redis, timezone Moscow).
- `tasks.py` — задачи:
  - `initiate_call` — инициировать звонок кандидату через Voximplant. Уважает лимит попыток (`settings.call_max_attempts`); при `attempts_count >= max` помечает кандидата `status='exhausted'` и не звонит.
  - `finalize_call` — после звонка: скачать запись, загрузить в S3, посчитать score, уведомить HR.
  - `fetch_recording` — загружает запись из Voximplant и кладёт в YOS.

## Планировщик

Beat-задачи нет. Окно `[9:00, 21:00)` `Europe/Moscow` соблюдается через
`apply_async(eta=next_dispatch_time(...))`:

- bulk-кнопка (`POST /vacancies/{id}/dispatch`) ставит задачи с `eta`,
  при необходимости сдвинутым на ближайшие 9:00.
- `webhook /call_failed` сам ставит retry с `eta = now + backoff`,
  где `backoff = settings.call_retry_backoff_minutes[attempts_count - 1]`,
  снова через `next_dispatch_time` (если время попадает за пределы окна).

Конфиг — в `app/config.py` (`call_*` поля), утилита окна — в
`app/core/dispatch_window.py`.

## Правила

- Все задачи — идемпотентные (можно перезапустить без побочных эффектов).
- `acks_late=True` — задача подтверждается после выполнения, не до.
- Rate-limit на исходящие звонки: не более `settings.call_max_attempts` попыток на кандидата.
- Окно звонков: `[settings.call_window_start_hour, settings.call_window_end_hour)` локального времени `settings.call_timezone`.
- Каждая задача создаёт fresh async engine через `_task_session()` — нельзя переиспользовать глобальный из `app.db.session`.
