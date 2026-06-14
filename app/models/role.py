
from tortoise.models import Model
from tortoise import fields


class Role(Model):

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    permissions = fields.ManyToManyField("models.Permission", related_name="roles", through="role_permissions")

    class Meta:
        table = "roles"