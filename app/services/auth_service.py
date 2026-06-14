
from loguru import logger
from app.models.user import User
from app.models.role import Role
from app.services.jwt_service import JWTService
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse


class AuthService:

    def __init__(self):
        self.jwt = None

    def set_jwt(self, jwt_svc: JWTService):

        self.jwt = jwt_svc

    async def register(self, data: UserRegisterRequest) -> User:
        if self.jwt is None:
            raise ValueError("JWT сервис не инициализирован")

        existing = await User.get_or_none(email=data.email.lower())
        if existing:
            raise ValueError(f"Email {data.email} уже зарегистрирован")

        user = User(
            email=data.email.lower(),
            first_name=data.first_name,
            last_name=data.last_name,
            patronymic=data.patronymic,
            is_active=True
        )
        user.set_password(data.password)
        await user.save()

        role = await Role.get_or_none(name="user")
        if role:
            await user.roles.add(role)

        logger.success(f"Пользователь создан: {user.email}")
        return user

    async def login(self, data: UserLoginRequest) -> TokenResponse:
        if self.jwt is None:
            raise ValueError("JWT сервис не инициализирован")

        user = await User.get_or_none(email=data.email.lower())
        if not user or not user.verify_password(data.password):
            raise ValueError("Неверный email или пароль")
        if not user.is_active:
            raise ValueError("Аккаунт деактивирован")

        roles = await user.roles.all().values_list('name', flat=True)

        access = self.jwt.create_access_token(str(user.id), email=user.email, roles=list(roles))
        refresh = self.jwt.create_refresh_token(str(user.id))

        logger.success(f"Вход: {data.email}")
        return TokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in=self.jwt.access_token_expire_minutes * 60)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        try:
            payload = self.jwt.verify_token_type(refresh_token, "refresh")
            user = await User.get_or_none(id=payload["sub"], is_active=True)
            if not user:
                raise ValueError("Пользователь не найден")

            roles = await user.roles.all().values_list('name', flat=True)
            access = self.jwt.create_access_token(str(user.id), email=user.email, roles=list(roles))
            refresh_new = self.jwt.create_refresh_token(str(user.id))

            return TokenResponse(access_token=access, refresh_token=refresh_new, token_type="bearer", expires_in=self.jwt.access_token_expire_minutes * 60)
        except ValueError as e:
            raise ValueError(f"Ошибка обновления: {e}")