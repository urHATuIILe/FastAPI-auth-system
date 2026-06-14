
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List
from loguru import logger

from app.schemas.user import UserProfileResponse
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.utils.rbac import check_permission, has_permission

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=List[UserProfileResponse],
    summary="Список пользователей",
    description="Возвращает список активных пользователей. Требует разрешения 'users:read'.",
    responses={
        200: {"description": "Список пользователей"},
        401: {"description": "Требуется авторизация"},
        403: {"description": "Доступ запрещён (нужно users:read)"}
    }
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(check_permission("users:read"))
):
    logger.info(
        f"Запрос списка пользователей | user={current_user.email} | "
        f"skip={skip} | limit={limit}"
    )

    users = await User.all().filter(is_active=True).offset(skip).limit(limit)

    result = []
    for u in users:
        roles = await u.roles.all().values_list('name', flat=True)
        result.append({
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "patronymic": u.patronymic,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat(),
            "roles": list(roles)
        })

    return result


@router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    summary="Профиль по ID",
    responses={
        200: {"description": "Профиль найден"},
        404: {"description": "Пользователь не найден"}
    }
)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    user = await User.get_or_none(id=user_id, is_active=True)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    roles = await user.roles.all().values_list('name', flat=True)
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
        "roles": list(roles)
    }


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
    description="Мягкое удаление. Владелец может удалить себя, или нужно разрешение 'users:delete'.",
    responses={
        204: {"description": "Пользователь удалён"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Пользователь не найден"}
    }
)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    can_delete = False

    if str(current_user.id) == user_id:
        can_delete = True
        reason = "владелец аккаунта"

    if not can_delete:
        if await has_permission(current_user, "users:delete"):
            can_delete = True
            reason = "разрешение users:delete"

    if not can_delete:
        logger.warning(
            f"Запрещено удаление | initiator={current_user.email} | target={user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалять только свой аккаунт (или требуется разрешение users:delete)"
        )

    await user.soft_delete()

    logger.info(
        f"Пользователь удалён | deleted={user.email} | "
        f"by={current_user.email} | reason={reason}"
    )

    return None