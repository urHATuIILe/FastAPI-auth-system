
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.models.user import User
from app.services.jwt_service import JWTService

security = HTTPBearer(auto_error=False)

_jwt_service: JWTService = None


def set_jwt_service(svc: JWTService):
    global _jwt_service
    _jwt_service = svc


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    global _jwt_service

    if not credentials:
        raise HTTPException(status_code=401, detail="Требуется авторизация (Bearer token)")

    if _jwt_service is None:
        raise HTTPException(status_code=500, detail="Сервис не инициализирован")

    try:
        payload = _jwt_service.verify_token_type(credentials.credentials, "access")
        user = await User.get_or_none(id=payload["sub"], is_active=True)
        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден или деактивирован")
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))