
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db, close_db, TORTOISE_CONFIG
from tortoise import Tortoise
from app.services.jwt_service import JWTService
from app.services.auth_service import AuthService
from app.routers import auth as auth_router
from app.routers import users as users_router
from app.routers import admin as admin_router
from app.utils.dependencies import set_jwt_service
from app.routers.auth import set_auth_service

jwt_service = JWTService(
    secret_key=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
)
auth_service = AuthService()
auth_service.set_jwt(jwt_service)


class TortoiseInitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        from tortoise import connections
        try:
            if connections.get("default"):
                return await call_next(request)
        except Exception:
            pass
        await Tortoise.init(config=TORTOISE_CONFIG)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск Auth System...")

    set_jwt_service(jwt_service)
    set_auth_service(auth_service)

    await init_db()

    await seed_data()

    logger.success("Auth System запущен!")
    yield
    logger.info("Остановка...")
    await close_db()


app = FastAPI(
    title="Auth System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Операции аутентификации: регистрация, вход, выход, профиль"
        },
        {
            "name": "Users",
            "description": "Управление пользователями (с проверкой прав)"
        },
        {
            "name": "Admin",
            "description": "Администрирование системы (только для role=admin)"
        },
        {
            "name": "Home",
            "description": "Главная страница"
        }
    ]
)

app.add_middleware(TortoiseInitMiddleware)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(admin_router.router)


@app.get("/", tags=["Home"])
async def root():
    return {
        "message": "Auth System",
        "docs": "/docs",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "register": "POST /api/v1/auth/register",
                "login": "POST /api/v1/auth/login",
                "logout": "POST /api/v1/auth/logout",
                "profile_get": "GET /api/v1/auth/me",
                "profile_update": "PUT /api/v1/auth/me",
                "refresh": "POST /api/v1/auth/refresh"
            },
            "users": {
                "list": "GET /api/v1/users/",
                "get": "GET /api/v1/users/{user_id}",
                "delete": "DELETE /api/v1/users/{user_id}"
            },
            "admin": {
                "users_list": "GET /api/v1/admin/users",
                "change_role": "PUT /api/v1/admin/users/{user_id}/role?role_name=admin",
                "roles": "GET /api/v1/admin/roles",
                "permissions": "GET /api/v1/admin/permissions",
                "stats": "GET /api/v1/admin/stats"
            }
        }
    }


async def seed_data():
    from app.models.role import Role
    from app.models.permission import Permission

    logger.info("Создание начальных данных...")

    roles = [
        {"name": "admin", "description": "Полный доступ ко всем ресурсам"},
        {"name": "user", "description": "Обычный пользователь"},
        {"name": "viewer", "description": "Только чтение"},
    ]

    for r in roles:
        existing = await Role.get_or_none(name=r["name"])
        if not existing:
            await Role.create(**r)
            logger.debug(f"Роль создана: {r['name']}")
        else:
            logger.debug(f"Роль уже существует: {r['name']}")

    perms = [
        {"name": "Просмотр пользователей", "code": "users:read", "module": "users"},
        {"name": "Создание пользователей", "code": "users:create", "module": "users"},
        {"name": "Удаление пользователей", "code": "users:delete", "module": "users"},
        {"name": "Просмотр ресурсов", "code": "resources:read", "module": "resources"},
    ]

    for p in perms:
        existing = await Permission.get_or_none(code=p["code"])
        if not existing:
            await Permission.create(**p)
            logger.debug(f"Разрешение создано: {p['code']}")
        else:
            logger.debug(f"Разрешение уже существует: {p['code']}")

    logger.success("Начальные данные готовы")