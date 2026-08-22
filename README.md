# Baza VPN

Backend MVP коммерческого Telegram-бота для VPN-сервиса.

Проект пока intentionally простой: FastAPI + aiogram + PostgreSQL + SQLAlchemy async + Alembic. Реальные VPN-серверы, реальные платежи, webhook и сложная инфраструктура на этом этапе не подключены.

## Что есть сейчас

- Telegram-бот на `aiogram 3`.
- FastAPI-приложение с endpoint для healthcheck и будущей ссылки подключения.
- PostgreSQL через async SQLAlchemy.
- Alembic migrations для структуры БД.
- Сервисный слой, чтобы бизнес-логика не жила в Telegram handlers.
- Тесты на users, trial, subscriptions, devices, payments и VPN-заглушку.

## Где находится User

Модель пользователя находится в `app/models/user.py`.

Она описывает таблицу `users`:

- `id` — внутренний integer primary key.
- `telegram_id` — уникальный Telegram ID.
- `username` — Telegram username, может быть пустым.
- `first_name` — имя из Telegram, может быть пустым.
- `created_at` — когда пользователь создан.
- `updated_at` — когда пользователь последний раз обновлён.
- `status` — `active` или `blocked`.
- `blocked_at` — когда пользователь был заблокирован, если применимо.

Статусы пользователя находятся в `app/enums.py`, enum `UserStatus`. Это помогает не разбрасывать строки вроде `"active"` и `"blocked"` по проекту.

## Где находится работа с БД

Базовое подключение к БД находится в `app/database.py`.

Там создаются:

- async SQLAlchemy engine;
- async session factory;
- dependency `get_session()` для FastAPI.

Модели лежат в `app/models/`.

Репозитории лежат в `app/repositories/`. Они отвечают за простые операции с БД:

- найти пользователя по `id`;
- найти пользователя по `telegram_id`;
- добавить пользователя;
- получить подписку, устройства, платежи.

Например, работа с таблицей `users` находится в `app/repositories/user_repository.py`.

## Где находится бизнес-логика

Бизнес-логика лежит в `app/services/`.

Для пользователей основной файл — `app/services/user_service.py`.

`UserService` отвечает за:

- создание пользователя;
- защиту от дублей по `telegram_id`;
- обновление `username` и `first_name` при повторном входе;
- блокировку и разблокировку пользователя.

Важно: Telegram handler не должен сам делать SQL-запросы. Handler вызывает service, а service использует repository.

## Где находится Telegram handler

Telegram handlers находятся в `app/bot/handlers/`.

`/start` находится в `app/bot/handlers/start.py`.

Сейчас `/start` работает так:

1. Telegram присылает update.
2. `cmd_start()` получает `message.from_user`.
3. Handler вызывает `UserService.create(...)`.
4. `UserService` ищет пользователя по `telegram_id`.
5. Если пользователя нет, создаёт его.
6. Если пользователь уже есть, не создаёт дубль и обновляет `username` / `first_name`.
7. Handler проверяет подписку через `SubscriptionService`.
8. Если подписки нет, показывает приветствие и кнопку trial.
9. Если подписка есть, показывает главный экран.

Trial не создаётся автоматически на `/start`. Он создаётся только после кнопки «Попробовать бесплатно».

## Где находится FastAPI

FastAPI-приложение создаётся в `app/main.py`.

API routes находятся в `app/api/routes/`.

Сейчас есть:

- `GET /health` — проверка, что приложение живо;
- `GET /s/{token}` — endpoint будущей ссылки подключения для Happ.

Запуск polling для Telegram-бота тоже происходит из `app/main.py`, если задан `BOT_TOKEN`.

## Как данные проходят от Telegram до PostgreSQL

Короткая цепочка для `/start`:

```text
Telegram
  -> aiogram Dispatcher
  -> app/bot/handlers/start.py
  -> UserService
  -> UserRepository
  -> AsyncSession SQLAlchemy
  -> PostgreSQL table users
```

На практике это выглядит так:

1. Пользователь пишет `/start`.
2. aiogram вызывает handler `cmd_start`.
3. Middleware из `app/bot/middlewares/db.py` создаёт async DB session и сервисы.
4. Handler вызывает `user_service.create(...)`.
5. `UserService` проверяет, есть ли пользователь с таким `telegram_id`.
6. Если нет — создаёт строку в `users`.
7. Если есть — возвращает существующую строку и обновляет публичные данные профиля.
8. SQLAlchemy отправляет изменения в PostgreSQL.
9. Middleware делает `commit`, если handler завершился без ошибки.

## Alembic migrations

Миграции лежат в `alembic/versions/`.

Текущие миграции:

- `0001_initial.py` — базовые таблицы проекта.
- `0002_add_user_updated_at.py` — добавляет `users.updated_at`.

Применить миграции:

```powershell
alembic upgrade head
```

Создать новую миграцию вручную:

```powershell
alembic revision -m "short description"
```

## Настройка окружения

Скопируй пример:

```powershell
copy .env.example .env
```

Минимально нужно заполнить:

- `APP_ENV` — `development`, `test` или `production`;
- `BOT_TOKEN`;
- `DATABASE_URL`;
- `SECRET_KEY`;
- `SUPPORT_USERNAME`;
- `SUBSCRIPTION_BASE_URL`.
- `ALLOWED_HOSTS` — домены, с которых можно обращаться к FastAPI.

В `production` приложение откажется стартовать, если критичные значения пустые или небезопасные.

Секреты нельзя коммитить. Файл `.env` уже добавлен в `.gitignore`.

## Запуск через Docker

```powershell
docker compose up --build
```

Compose поднимет:

- PostgreSQL;
- Redis;
- приложение FastAPI + Telegram polling.

## Локальный запуск без Docker

Установить зависимости:

```powershell
python -m pip install -e ".[dev]"
```

Применить миграции:

```powershell
alembic upgrade head
```

Запустить приложение:

```powershell
uvicorn app.main:app --reload
```

## Тесты

Запуск:

```powershell
python -m pytest -q
```

Тесты используют in-memory SQLite, чтобы быстро проверять бизнес-логику без локального PostgreSQL. Production-код при этом рассчитан на PostgreSQL через `DATABASE_URL`.
