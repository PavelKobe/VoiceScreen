# Шпаргалка команд VoiceScreen

Все команды на VM запускаются от пользователя `ubuntu`, с Win11 — из
PowerShell в `c:\Users\kobel\VoiceScreen\VoiceScreen\`.

---

## 0. Универсальный утренний рецепт ☀️

Эту последовательность можно гонять **каждое утро или после любого
перерыва** — работает и когда VM перезагружали, и когда контейнеры
не выключались. Подтягивает свежий код и поднимает/перезапускает
api+worker с новым кодом.

```bash
ssh voicescreen
cd ~/VoiceScreen
git pull
docker compose up -d
```

Если в `pyproject.toml` появились новые pip-зависимости — после `git pull`
дополнительно пересобрать образ:

```bash
docker compose build api worker
docker compose up -d api worker
```

Если в репе появились новые миграции:

```bash
docker compose exec -w /app -e PYTHONPATH=/app api alembic upgrade head
```

В большинстве случаев хватает четырёх строк выше — миграции/build нужны
редко, и Claude напоминает об этом в конце сообщений с пушем.

---

## 1. Запуск сервисов после остановки / рестарта VM

```bash
ssh voicescreen
cd ~/VoiceScreen

# 1. Поднять все Docker-контейнеры (postgres, redis, api, worker, bot)
docker compose up -d

# 2. Проверить состояние
docker compose ps

# 3. Накатить миграции БД (на случай если в репе появились новые)
docker compose exec -w /app -e PYTHONPATH=/app api alembic upgrade head

# 4. Убедиться что api поднялся чисто
docker compose logs api --tail=20 | grep -iE "startup|error"
# ожидаем: Application startup complete, без traceback'ов

# 5. Сертификат HTTPS (Let's Encrypt) обновляется автоматически certbot'ом,
#    но если nginx упал после рестарта VM — поднять:
sudo systemctl status nginx
sudo systemctl start nginx        # если не запущен

# 6. Проверить что фронт и API отвечают
curl -I https://voxscreen.ru/health
curl -I https://app.voxscreen.ru/
```

Если api/worker не поднимаются — посмотри логи сервиса по очереди:

```bash
docker compose logs postgres --tail=20
docker compose logs redis --tail=20
docker compose logs worker --tail=30 | grep -iE "error|connect|ready"
```

---

## 2. Деплой новой версии

### 2.1 Если изменения только в бэкенде (Python)

```bash
ssh voicescreen
cd ~/VoiceScreen
git pull

# Если в pyproject.toml появились новые зависимости — пересобрать образ
# (без новых depends можно пропустить и сделать только restart)
docker compose build api worker

# Применить новые миграции (если есть)
docker compose exec -w /app -e PYTHONPATH=/app api alembic upgrade head

# Перезапустить контейнеры (`up -d` вместо `restart`,
# чтобы новые env-переменные из .env подхватились)
docker compose up -d api worker

# Проверить
docker compose logs api --tail=20 | grep -iE "startup|error"
```

### 2.2 Если изменения только во фронте (web/)

С Win11 в PowerShell:

```powershell
cd C:\Users\kobel\VoiceScreen\VoiceScreen\web

# 1. Собрать
npm run build

# 2. Залить статику на VM
ssh voicescreen "rm -rf /var/www/voxscreen-app/*"
scp -r dist/* voicescreen:/var/www/voxscreen-app/
ssh voicescreen "chmod -R u+rwX,go+rX /var/www/voxscreen-app/"

# 3. В браузере на app.voxscreen.ru — Ctrl+F5 для очистки кеша
```

### 2.3 Если изменения и там и там

Сначала бэк (§2.1), потом фронт (§2.2). Порядок важен — UI может
ходить в новые ручки, которых ещё нет в старом бэке.

### 2.4 Если правил VoxEngine `screening.js`

⚠️ Этот файл **не** деплоится через `git pull` — он исполняется на стороне
Voximplant, не на нашей VM.

1. На Win11 открыть `app/telephony/voxengine/screening.js`.
2. Скопировать всё содержимое (Ctrl+A → Ctrl+C).
3. [manage.voximplant.com](https://manage.voximplant.com) →
   Applications → `voicescreen` → Scenarios.
4. Открыть существующий сценарий → выделить весь код → удалить → вставить
   новое содержимое → **Save**.

Без этого шага фикс на VM не подействует, потому что VoxEngine исполняет
свою копию кода у Voximplant.

---

## Полезное при деплое

```bash
# увидеть логи api/worker онлайн
docker compose logs -f api worker | grep -viE "wp-admin|wordpress|PROPFIND"

# полный рестарт всего стека (nuclear option)
docker compose down && docker compose up -d

# очистить старые образы после нескольких --build
docker image prune -f

# проверка миграций
docker compose exec postgres psql -U voicescreen -d voicescreen -c \
  "SELECT version_num FROM alembic_version;"

# создать пользователя кабинета
ADMIN=$(grep '^ADMIN_API_KEY=' .env | cut -d= -f2-)
curl -X POST https://voxscreen.ru/api/v1/clients/3/users \
  -H "X-Admin-Key: $ADMIN" -H "Content-Type: application/json" \
  -d '{"email":"hr@example.com","password":"smoke123","role":"client_admin"}'
```

См. также `OPS.md` — полная операционная шпаргалка.
