
from tortoise.models import Model
from tortoise import fields
from passlib.context import CryptContext
from datetime import datetime
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Model):

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    email = fields.CharField(max_length=255, unique=True, index=True)
    password_hash = fields.CharField(max_length=255, null=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    patronymic = fields.CharField(max_length=100, null=True)
    is_active = fields.BooleanField(default=True)
    is_verified = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)
    roles = fields.ManyToManyField("models.Role", related_name="users", through="user_roles")

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.email}"

    @property
    def full_name(self) -> str:
        if self.patronymic:
            return f"{self.last_name} {self.first_name} {self.patronymic}"
        return f"{self.last_name} {self.first_name}"

    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)

    async def soft_delete(self):
        self.is_active = False
        self.deleted_at = datetime.utcnow()
        await self.save(update_fields=["is_active", "deleted_at"])