"""Модель пользователя (Beanie/Mongo) и Pydantic-схемы fastapi-users."""
from typing import List, Optional

from beanie import Document, PydanticObjectId
from fastapi_users import schemas
from fastapi_users_db_beanie import BaseOAuthAccount, BeanieBaseUser
from pydantic import Field


class OAuthAccount(BaseOAuthAccount):
    """Привязанный соц-аккаунт (VK / Yandex / Google). Telegram сюда же."""


class User(BeanieBaseUser, Document):
    # Уровни доступа: тариф и роль (под будущий гейтинг)
    plan: str = "free"   # free | premium | ...
    role: str = "user"   # user | admin
    oauth_accounts: List[OAuthAccount] = Field(default_factory=list)

    class Settings(BeanieBaseUser.Settings):
        name = "users"


# ── Схемы API ────────────────────────────────────────────────────────
class UserRead(schemas.BaseUser[PydanticObjectId]):
    plan: str
    role: str


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    # plan/role НАМЕРЕННО не здесь: self-service PATCH /users/me не должен
    # позволять поднять себе тариф/роль. Меняется отдельным admin-роутом.
    pass
