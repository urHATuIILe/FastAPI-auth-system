
from pydantic_settings import BaseSettings
from functools import lru_cache
from loguru import logger


class Settings(BaseSettings):
    app_name: str = "Auth System"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "auth_system"

    @property
    def database_url(self) -> str:
        return f"postgres://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


    jwt_secret: str = "Поменять нужно будет на сикрет кей"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

logger.remove()
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="100 MB",
    retention="7 days",
    level="DEBUG" if settings.debug else "INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
)
logger.add(lambda msg: print(msg, end=""), level="INFO", format="{time:HH:mm:ss} | {level:<8} | {message}")