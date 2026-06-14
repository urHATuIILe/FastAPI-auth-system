
from fastapi import Depends, HTTPException, status
from typing import List, Optional
from loguru import logger

from app.models.user import User
from app.utils.dependencies import get_current_user


def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: User = Depends(get_current_user)):
        user_roles = await current_user.roles.all().values_list('name', flat=True)
        user_roles_list = list(user_roles)

        has_access = any(role in allowed_roles for role in user_roles_list)

        if not has_access:
            logger.warning(
                f"Доступ запрещён | user={current_user.email} | "
                f"roles={user_roles_list} | required={allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуются роли: {', '.join(allowed_roles)}"
            )

        return current_user

    return role_checker


def require_admin():
    return require_roles(["admin"])


def check_permission(permission_code: str):
    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_roles = await current_user.roles.all()

        # Admin имеет всё
        for role_obj in user_roles:
            if role_obj.name == "admin":
                return current_user

        has_permission = False
        user_role_names = []

        for role_obj in user_roles:
            user_role_names.append(role_obj.name)

            perm_exists = await role_obj.permissions.filter(
                code=permission_code
            ).exists()

            if perm_exists:
                has_permission = True
                break

        if not has_permission:
            logger.warning(
                f"Нет разрешения | user={current_user.email} | "
                f"roles={user_role_names} | required_perm={permission_code}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав. Требуется разрешение: {permission_code}"
            )

        return current_user

    return permission_checker

async def get_user_roles(user: User) -> List[str]:
    roles = await user.roles.all().values_list('name', flat=True)
    return list(roles)


async def has_role(user: User, role_name: str) -> bool:
    roles = await get_user_roles(user)
    return role_name in roles


async def has_permission(user: User, permission_code: str) -> bool:
    if await has_role(user, "admin"):
        return True

    user_roles = await user.roles.all()

    for role in user_roles:
        has_perm = await role.permissions.filter(code=permission_code).exists()
        if has_perm:
            return True

    return False