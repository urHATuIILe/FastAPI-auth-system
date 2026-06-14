
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from loguru import logger


class JWTService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        # Валидация ключа через loguru
        if len(secret_key) < 32:
            logger.warning(
                f"Секретный ключ слишком короткий ({len(secret_key)} символов)! "
                f"Рекомендуется минимум 32 символа."
            )

        logger.success(
            f"JWT сервис инициализирован (algorithm={algorithm}, "
            f"access={access_token_expire_minutes}min, refresh={refresh_token_expire_days}days)"
        )

    def _get_now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def create_access_token(
        self,
        user_id: str,
        *,
        email: Optional[str] = None,
        roles: Optional[list] = None,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        now = self._get_now_utc()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": str(int(now.timestamp() * 1000))
        }

        if email:
            payload["email"] = email

        if roles:
            payload["roles"] = roles

        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(
            f"Access токен создан | user_id={user_id} | "
            f"expires={expire.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return token

    def create_refresh_token(
        self,
        user_id: str,
        *,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        now = self._get_now_utc()
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": str(int(now.timestamp() * 1000))
        }

        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(
            f"Refresh токен создан | user_id={user_id} | "
            f"expires={expire.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return token

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            logger.debug(f"Токен успешно декодирован | type={payload.get('type')}")
            return payload

        except jwt.ExpiredSignatureError:
            error_msg = "Токен истёк"
            logger.warning(f"{error_msg}")
            raise ValueError(error_msg)

        except jwt.JWTError as e:
            error_msg = f"Неверный токен: {str(e)}"
            logger.warning(f"{error_msg}")
            raise ValueError(error_msg)

    def verify_token_type(self, token: str, expected_type: str) -> Dict[str, Any]:
        payload = self.decode_token(token)

        token_type = payload.get("type")

        if token_type != expected_type:
            error_msg = (
                f"Неверный тип токена: ожидается '{expected_type}', "
                f"получен '{token_type}'"
            )
            logger.warning(f"{error_msg}")
            raise ValueError(error_msg)

        logger.debug(
            f"Тип токена верифицирован | expected={expected_type} | actual={token_type}"
        )
        return payload

    def get_user_id_from_token(self, token: str) -> str:
        payload = self.decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            error_msg = "В токене отсутствует 'sub' (user_id)"
            logger.error(f"{error_msg}")
            raise ValueError(error_msg)

        logger.debug(f"Извлечён user_id={user_id} из токена")
        return user_id

    def get_token_expiration(self, token: str) -> datetime:
        payload = self.decode_token(token)
        exp_timestamp = payload.get("exp")

        if not exp_timestamp:
            error_msg = "В токене отсутствует 'exp' (expiration)"
            logger.error(f"{error_msg}")
            raise ValueError(error_msg)

        expiration = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        logger.debug(f"Токен истекает: {expiration.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        return expiration

    def is_token_expired(self, token: str) -> bool:
        try:
            self.decode_token(token)
            logger.debug("Токен ещё активен")
            return False
        except ValueError as e:
            if "истёк" in str(e).lower():
                logger.debug("Токен истёк")
                return True
            raise


def create_jwt_service(secret_key: str, **kwargs) -> JWTService:
    return JWTService(secret_key=secret_key, **kwargs)

if __name__ == "__main__":

    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <level>{message}</level>",
        colorize=True
    )
