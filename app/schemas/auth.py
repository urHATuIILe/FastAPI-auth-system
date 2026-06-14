
from pydantic import BaseModel, Field, field_validator
from pydantic import EmailStr
from typing import Optional


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, example="StrongPass123!")
    password_confirm: str = Field(..., example="StrongPass123!")
    first_name: str = Field(..., min_length=1, max_length=100, example="Иван")
    last_name: str = Field(..., min_length=1, max_length=100, example="Петров")
    patronymic: Optional[str] = Field(None, max_length=100, example="Иванович")

    @field_validator('password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Пароли не совпадают')
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., example="StrongPass123!")


class TokenResponse(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOi...")
    refresh_token: str = Field(..., example="eyJhbGciOi...")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., example=1800, description="секунд")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., example="eyJhbGciOi...")