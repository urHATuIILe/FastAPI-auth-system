
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserProfileResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    patronymic: Optional[str] = None
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    roles: list[str] = []

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):

    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        example="Иван"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        example="Петров"
    )
    patronymic: Optional[str] = Field(
        None,
        max_length=100,
        example="Иванович"
    )
    email: Optional[EmailStr] = Field(
        None,
        example="newemail@example.com"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "patronymic": "Иванович",
                    "email": "newemail@example.com"
                },
                {
                    "first_name": "Новое имя"
                }
            ]
        }
    }