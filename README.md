# Auth System — система аутентификации и авторизации на FastAPI

Backend-приложение, реализующее полный цикл аутентификации и авторизации пользователей с собственной системой разграничения доступа на основе ролей (RBAC) и разрешений (permissions).

Решение не использует готовые «коробочные» механизмы фреймворков (Django/DRF и т. п.) — вся логика разграничения прав написана самостоятельно в соответствии с требованиями технического задания.

## Возможности

- Регистрация, логин и логаут пользователя (email + пароль)
- Обновление профиля (ФИО, email) авторизованным пользователем
- Мягкое удаление аккаунта (`is_active=False`) — как самим пользователем, так и администратором
- JWT-аутентификация (access + refresh токены) с проверкой типа токена
- Собственная RBAC: роли (`admin`, `user`, `viewer`) и разрешения (например, `users:read`, `users:delete`)
- Администрирование: просмотр всех пользователей (включая неактивных), назначение и изменение ролей, просмотр ролей и разрешений, статистика системы
- Автоматическое создание начальных данных (роли и разрешения) при первом запуске
- Логирование значимых действий через `loguru` с ротацией файлов

## Стек технологий

| Компонент            | Технология                         |
| -------------------- | ---------------------------------- |
| Web-фреймворк        | FastAPI                            |
| ORM                  | Tortoise ORM                       |
| База данных          | PostgreSQL (asyncpg)               |
| Аутентификация       | JWT (python-jose), access + refresh|
| Хеширование паролей  | passlib (bcrypt)                   |
| Валидация данных      | Pydantic v2                        |
| Конфигурация          | Pydantic Settings + `.env`         |
| Логирование           | loguru                             |
| ASGI-сервер          | Uvicorn                            |

## Структура проекта

```
.
├── run.py                      # точка входа (uvicorn)
├── make_admin.py               # выдать роль admin пользователю admin@test.com
├── requirements.txt
├── .env.example                # шаблон переменных окружения
└── app/
    ├── main.py                 # инициализация FastAPI, БД, начальных данных
    ├── config.py               # настройки (Pydantic Settings)
    ├── database.py             # конфигурация Tortoise ORM
    ├── models/                 # ORM-модели: user, role, permission
    ├── schemas/                # Pydantic-схемы: auth, user
    ├── routers/                # эндпоинты: auth, users, admin
    ├── services/               # бизнес-логика: auth_service, jwt_service
    ├── utils/                  # dependencies, rbac
    └── middleware/
```

## Схема базы данных

Три основные таблицы (`users`, `roles`, `permissions`) и две промежуточные для связей многие-ко-многим.

### Таблица `users`

| Поле           | Тип          | Описание                              |
| -------------- | ------------ | ------------------------------------- |
| id             | UUID (PK)    | Уникальный идентификатор              |
| email          | string(255)  | Email, уникальный, индекс             |
| password_hash  | string(255)  | Хеш пароля (bcrypt)                   |
| first_name     | string(100)  | Имя                                   |
| last_name      | string(100)  | Фамилия                               |
| patronymic     | string(100)  | Отчество (опционально)                |
| is_active      | boolean      | Активен (мягкое удаление)             |
| is_verified    | boolean      | Подтверждён ли email (задел на будущее)|
| is_superuser   | boolean      | Флаг суперпользователя (резерв)       |
| created_at     | datetime     | Дата создания                         |
| updated_at     | datetime     | Дата обновления                       |
| deleted_at     | datetime     | Дата мягкого удаления (опционально)   |

### Таблица `roles`

| Поле        | Тип         | Описание           |
| ----------- | ----------- | ------------------ |
| id          | int (PK)    |                    |
| name        | string(50)  | Уникальное имя роли|
| description | text        | Описание           |
| is_active   | boolean     | Активна ли роль    |
| created_at  | datetime    |                    |

### Таблица `permissions`

| Поле        | Тип          | Описание                          |
| ----------- | ------------ | --------------------------------- |
| id          | int (PK)     |                                   |
| name        | string(100)  | Человекочитаемое имя              |
| code        | string(100)  | Уникальный код (напр. `users:read`)|
| description | text         |                                   |
| module      | string(50)   | Модуль (`users`, `resources` …)   |
| created_at  | datetime     |                                   |

### Связи многие-ко-многим

- `user_roles` — связывает `users` и `roles` (у пользователя может быть несколько ролей)
- `role_permissions` — связывает `roles` и `permissions` (у роли может быть несколько разрешений)

Связи реализованы через `ManyToManyField` Tortoise ORM.

## Система разграничения прав (собственная RBAC)

При регистрации пользователь получает роль `user` по умолчанию. Роль `admin` имеет все права без явного назначения разрешений — это заложено в логике `check_permission`.

Каждое действие проверяется через зависимости FastAPI:

- `Depends(get_current_user)` — проверяет JWT и возвращает объект `User`
- `Depends(require_roles(["admin"]))` — проверяет наличие одной из перечисленных ролей
- `Depends(check_permission("users:read"))` — проверяет конкретное разрешение (с учётом привилегии admin)

### Роли (создаются автоматически)

| Роль   | Описание                       |
| ------ | ------------------------------ |
| admin  | Полный доступ ко всем ресурсам |
| user   | Обычный пользователь           |
| viewer | Только чтение (задел на будущее)|

### Разрешения

| Имя                   | Код                | Модуль    |
| --------------------- | ------------------ | --------- |
| Просмотр пользователей| `users:read`       | users     |
| Создание пользователей| `users:create`     | users     |
| Удаление пользователей| `users:delete`     | users     |
| Просмотр ресурсов     | `resources:read`   | resources |

## API эндпоинты

Базовый префикс: `/api/v1`. Интерактивная документация OpenAPI: `http://localhost:8000/docs`.

### Аутентификация и профиль (`/auth`)

| Метод | Эндпоинт          | Описание                                  | Доступ              |
| ----- | ----------------- | ----------------------------------------- | ------------------- |
| POST  | `/auth/register`  | Регистрация нового пользователя           | публичный           |
| POST  | `/auth/login`     | Вход, получение access + refresh токенов  | публичный           |
| POST  | `/auth/logout`    | Выход (клиент удаляет токены)             | get_current_user    |
| GET   | `/auth/me`        | Получить свой профиль                     | get_current_user    |
| PUT   | `/auth/me`        | Обновить свои данные (ФИО, email)         | get_current_user    |
| POST  | `/auth/refresh`   | Обновить access-токен по refresh-токену   | публичный (refresh) |

### Пользователи (`/users`)

| Метод  | Эндпоинт           | Описание                                   | Доступ                       |
| ------ | ------------------ | ------------------------------------------ | ---------------------------- |
| GET    | `/users/`          | Список активных пользователей (пагинация)  | `users:read`                 |
| GET    | `/users/{user_id}` | Профиль пользователя по ID                 | get_current_user             |
| DELETE | `/users/{user_id}` | Мягкое удаление                            | владелец или `users:delete`  |

### Администрирование (`/admin`) — только роль `admin`

| Метод | Эндпоинт                              | Описание                                       |
| ----- | ------------------------------------- | ---------------------------------------------- |
| GET   | `/admin/users`                        | Список всех пользователей (вкл. неактивных)    |
| PUT   | `/admin/users/{user_id}/role?role_name=` | Назначить новую роль пользователю           |
| GET   | `/admin/roles`                        | Список всех ролей                              |
| GET   | `/admin/permissions`                  | Список всех разрешений                         |
| GET   | `/admin/stats`                        | Статистика (число пользователей/ролей/прав)    |

## Установка и запуск

### 1. Требования

- Python 3.10+
- PostgreSQL

### 2. Клонирование

```bash
git clone https://github.com/urHATuIILe/FastAPI-auth-sistem.git
cd FastAPI-auth-sistem
```

### 3. Виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
```

### 4. Зависимости

```bash
pip install -r requirements.txt
```

### 5. Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

Сгенерировать `JWT_SECRET` можно так:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> `.env` содержит секреты и **не должен попадать в git** — храните в репозитории только `.env.example`. Для production укажите `DEBUG=False`.

### 6. Запуск

```bash
python run.py
```

При старте автоматически создаются таблицы в БД и заполняются начальные роли (`admin`, `user`, `viewer`) и разрешения.

### 7. Создание первого администратора

Зарегистрируйте пользователя с email `admin@test.com` через `/auth/register`, затем выполните:

```bash
python make_admin.py
```

Скрипт назначит этому пользователю роль `admin`.

## Примеры запросов

Регистрация:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPass123!",
    "password_confirm": "StrongPass123!",
    "first_name": "Иван",
    "last_name": "Петров",
    "patronymic": "Иванович"
  }'
```

Вход:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "StrongPass123!"}'
```

Ответ:

```json
{"access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 1800}
```

Список пользователей (требуется `users:read`):

```bash
curl -X GET http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <access_token>"
```

Назначение роли (админ):

```bash
curl -X PUT "http://localhost:8000/api/v1/admin/users/<user_id>/role?role_name=admin" \
  -H "Authorization: Bearer <admin_access_token>"
```

## Что реализовано

- Собственная аутентификация: JWT (access + refresh), регистрация, логин, логаут, обновление профиля
- Мягкое удаление через флаг `is_active=False`
- Собственная RBAC с ролями и разрешениями, проверки через зависимости FastAPI
- API администратора для управления ролями пользователей
- Корректные ответы `401` / `403` при отсутствии аутентификации или прав
- Чёткое разделение аутентификации (кто ты) и авторизации (что тебе можно)
