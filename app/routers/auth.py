
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from loguru import logger

from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest,
    TokenResponse, RefreshTokenRequest
)
from app.schemas.user import UserProfileResponse, UserUpdateRequest
from app.services.auth_service import AuthService
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

_auth_service: AuthService = None


def set_auth_service(svc: AuthService):
    global _auth_service
    _auth_service = svc

@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт новый аккаунт. После регистрации нужно войти через /login.",
    responses={
        201: {"description": "Пользователь успешно создан"},
        409: {"description": "Email уже зарегистрирован"},
        422: {"description": "Ошибка валидации данных"}
    }
)
async def register(data: UserRegisterRequest):
    if _auth_service is None:
        raise HTTPException(500, "Сервис не готов")

    try:
        user = await _auth_service.register(data)
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "patronymic": user.patronymic,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat(),
            "roles": []
        }
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
    description="Возвращает JWT access_token и refresh_token. Используйте access_token в заголовке Authorization: Bearer <token>.",
    responses={
        200: {"description": "Успешный вход, токены получены"},
        401: {"description": "Неверный email или пароль"}
    }
)
async def login(data: UserLoginRequest):
    if _auth_service is None:
        raise HTTPException(500, "Сервис не готов")

    try:
        result = await _auth_service.login(data)

        logger.info(
            f"Успешный вход | email={data.email} | "
            f"token_type=bearer | expires_in={result.expires_in}s"
        )

        return result

    except ValueError as e:
        logger.warning(f"Ошибка входа | email={data.email} | error={e}")
        raise HTTPException(status_code=401, detail=str(e))

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Выход из системы",
    description="Выход авторизованного пользователя из системы.",
    responses={
        200: {
            "description": "Успешный выход из системы",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Вы успешно вышли из системы",
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "admin@test.com",
                        "logged_out_at": "2025-11-05T21:55:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Требуется авторизация",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    },
    tags=["Authentication"]
)
async def logout(current_user: User = Depends(get_current_user)):

    user_roles = await current_user.roles.all().values_list('name', flat=True)

    logger.info(
        f"Пользователь вышел из системы | "
        f"user_id={current_user.id} | "
        f"email={current_user.email} | "
        f"name={current_user.full_name} | "
        f"roles={list(user_roles)}"
    )

    response_data = {
        "message": "Вы успешно вышли из системы",
        "user_id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "logged_out_at": datetime.utcnow().isoformat() + "Z",
        "note": (
            "Токены остаются валидными до истечения срока. "
            "Можно реализовать их удаление через blacklist."
        )
    }

    logger.success(f"Logout успешен | user={current_user.email}")

    return response_data

@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Обновить профиль",
    description="Редактирование данных своего профиля (ФИО, email). Можно обновлять частично - только те поля, которые переданы.",
    responses={
        200: {
            "description": "Профиль успешно обновлён",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "newemail@example.com",
                        "first_name": "Иван",
                        "last_name": "Петров",
                        "patronymic": "Иванович",
                        "full_name": "Петров Иван Иванович",
                        "is_active": True,
                        "is_verified": False,
                        "created_at": "2025-11-05T20:00:00Z",
                        "roles": ["user"]
                    }
                }
            }
        },
        401: {"description": "Требуется авторизация"},
        409: {"description": "Email уже занят другим пользователем"},
        422: {"description": "Ошибка валидации данных"}
    },
    tags=["Authentication"]
)
async def update_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user)
):

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления. Передайте хотя бы одно поле."
        )

    logger.info(
        f"Обновление профиля | user_id={current_user.id} | "
        f"email={current_user.email} | fields_to_update={list(update_data.keys())}"
    )

    # Проверка email на уникальность (если его меняют)
    if 'email' in update_data:
        new_email = update_data['email'].lower()

        existing_user = await User.get_or_none(
            email=new_email,
            is_active=True
        ).exclude(id=current_user.id)

        if existing_user:
            logger.warning(
                f"Email уже занят | requested_email={new_email} | "
                f"owner_id={existing_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email {new_email} уже зарегистрирован другим пользователем"
            )

        update_data['email'] = new_email

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await current_user.save()

    roles = await current_user.roles.all().values_list('name', flat=True)

    logger.success(
        f"Профиль обновлён | user_id={current_user.id} | "
        f"new_email={current_user.email} | updated_fields={list(update_data.keys())}"
    )

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "patronymic": current_user.patronymic,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "roles": list(roles)
    }

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токенов",
    description="Меняет устаревший access_token на новый по refresh_token.",
    responses={
        200: {"description": "Токены обновлены"},
        401: {"description": "Refresh токен невалиден или истёк"}
    }
)
async def refresh_token(data: RefreshTokenRequest):
    if _auth_service is None:
        raise HTTPException(500, "Сервис не готов")

    try:
        new_tokens = await _auth_service.refresh_tokens(data.refresh_token)

        logger.debug("Токены успешно обновлены")
        return new_tokens

    except ValueError as e:
        logger.warning(f"Ошибка обновления токенов: {e}")
        raise HTTPException(status_code=401, detail=str(e))


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Мой профиль",
    description="Возвращает профиль текущего авторизованного пользователя. Требует заголовок Authorization: Bearer <token>.",
    responses={
        200: {"description": "Профиль пользователя"},
        401: {"description": "Токен отсутствует или недействителен"}
    }
)
async def get_me(current_user: User = Depends(get_current_user)):
    roles = await current_user.roles.all().values_list('name', flat=True)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "patronymic": current_user.patronymic,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "roles": list(roles)
    }