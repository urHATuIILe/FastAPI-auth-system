#Накидал кода для выдачи админки
import asyncio
from app.database import TORTOISE_CONFIG
from tortoise import Tortoise

from loguru import logger


async def make_admin():
    await Tortoise.init(config=TORTOISE_CONFIG)

    from app.models.user import User
    from app.models.role import Role

    user = await User.get_or_none(email="admin@test.com")
    if not user:
        logger.error("Пользователь admin@test.com не найден! Сначала зарегистрируйтесь.")
        return

    role = await Role.get_or_none(name="admin")
    if not role:
        logger.error("Роль admin не найдена!")
        return

    await user.roles.clear()
    await user.roles.add(role)

    logger.success(f"ПОЛЬЗОВАТЕЛЬ {user.email} ТЕПЕРЬ АДМИН!")
    logger.info(f"   ID: {user.id}")
    logger.info(f"   Email: {user.email}")
    logger.info(f"   Имя: {user.full_name}")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(make_admin())