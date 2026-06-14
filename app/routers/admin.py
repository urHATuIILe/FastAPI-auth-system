
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List
from loguru import logger

from app.schemas.user import UserProfileResponse
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


def admin_required():
    async def check_admin(current_user: User = Depends(get_current_user)):
        user_roles = await current_user.roles.all().values_list('name', flat=True)
        roles_list = list(user_roles)

        if "admin" not in roles_list:
            logger.warning(
                f"Доступ запрещён | user={current_user.email} | "
                f"roles={roles_list} | required=admin"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещён. Требуется роль admin"
            )

        logger.debug(f"Admin доступ подтверждён | user={current_user.email}")
        return current_user

    return check_admin


@router.get(
    "/users",
    response_model=List[UserProfileResponse],
    summary="Список всех пользователей",
    description="Возвращает список ВСЕХ пользователей (включая неактивных). Только для admin.",
    responses={
        200: {"description": "Список пользователей"},
        401: {"description": "Требуется авторизация"},
        403: {"description": "Доступ запрещён (только admin)"}
    },
    tags=["Admin"]
)
async def list_all_users(
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(20, ge=1, le=100, description="Количество записей"),
    current_user: User = Depends(admin_required())
):
    logger.info(
        f"Admin запрос списка пользователей | admin={current_user.email} | "
        f"skip={skip} | limit={limit}"
    )

    users = await User.all().offset(skip).limit(limit)

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

    logger.success(f"Выдано пользователей: {len(result)}")
    return result


@router.put(
    "/users/{user_id}/role",
    response_model=UserProfileResponse,
    summary="Изменить роль пользователя",
    description="Назначает или изменяет роль пользователя. Только для admin.",
    responses={
        200: {"description": "Роль изменена"},
        401: {"description": "Требуется авторизация"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Пользователь не найден"},
        400: {"description": "Роль не существует"}
    },
    tags=["Admin"]
)
async def change_user_role(
    user_id: str,
    role_name: str = Query(..., description="Новая роль: admin, user, viewer"),
    current_user: User = Depends(admin_required())
):
    logger.info(
        f"Запрос изменения роли | admin={current_user.email} | "
        f"target={user_id} | new_role={role_name}"
    )

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    role = await Role.get_or_none(name=role_name.lower())
    if not role:
        available_roles = await Role.all().values_list('name', flat=True)
        raise HTTPException(
            status_code=400,
            detail=f"Роль '{role_name}' не существует. Доступные: {', '.join(available_roles)}"
        )

    await user.roles.clear()
    await user.roles.add(role)

    logger.success(
        f"Роль изменена | user={user.email} → {role_name} | by={current_user.email}"
    )

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


@router.get(
    "/roles",
    summary="Список ролей",
    description="Возвращает все доступные роли в системе.",
    responses={
        200: {"description": "Список ролей"},
        403: {"description": "Доступ запрещён"}
    },
    tags=["Admin"]
)
async def list_roles(current_user: User = Depends(admin_required())):
    roles = await Role.all()

    logger.info(f"Список ролей запрошен | admin={current_user.email}")

    return [
        {"name": r.name, "description": r.description}
        for r in roles
    ]


@router.get(
    "/permissions",
    summary="Список разрешений",
    description="Возвращает все доступные разрешения в системе.",
    responses={
        200: {"description": "Список разрешений"},
        403: {"description": "Доступ запрещён"}
    },
    tags=["Admin"]
)
async def list_permissions(current_user: User = Depends(admin_required())):
    permissions = await Permission.all()

    logger.info(f"Список разрешений запрошен | admin={current_user.email}")

    return [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "module": p.module,
            "description": p.description
        }
        for p in permissions
    ]


@router.get(
    "/stats",
    summary="Статистика системы",
    description="Возвращает базовую статистику по пользователям, ролям и разрешениям.",
    responses={
        200: {"description": "Статистика"},
        403: {"description": "Доступ запрещён"}
    },
    tags=["Admin"]
)
async def get_system_stats(current_user: User = Depends(admin_required())):
    total_users = await User.all().count()
    active_users = await User.filter(is_active=True).count()
    inactive_users = await User.filter(is_active=False).count()

    total_roles = await Role.all().count()
    total_perms = await Permission.all().count()

    stats = {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users
        },
        "roles": {
            "total": total_roles
        },
        "permissions": {
            "total": total_perms
        }
    }

    logger.info(f"Статистика запрошена | admin={current_user.email}")

    return stats