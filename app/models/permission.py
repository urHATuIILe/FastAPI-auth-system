
from tortoise.models import Model
from tortoise import fields


class Permission(Model):

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    code = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    module = fields.CharField(max_length=50)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "permissions"