"""fastapi-users: менеджер, JWT-бэкенд и зависимости доступа."""
from typing import Optional

from beanie import PydanticObjectId
from fastapi import Depends, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_beanie import BeanieUserDatabase, ObjectIDIDMixin

from .config import settings
from .models import OAuthAccount, User


async def get_user_db():
    # Передаём OAuthAccount → включает поддержку соц-логинов.
    yield BeanieUserDatabase(User, OAuthAccount)


class UserManager(ObjectIDIDMixin, BaseUserManager[User, PydanticObjectId]):
    reset_password_token_secret = settings.jwt_secret
    verification_token_secret = settings.jwt_secret

    async def on_after_register(self, user: User, request=None):
        # Место под приветственное письмо / аналитику.
        print(f"[auth] зарегистрирован пользователь {user.email} (id={user.id})")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# ── JWT bearer (фронт — статичная SPA, серверных сессий нет) ──────────
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.jwt_secret,
        lifetime_seconds=settings.jwt_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, PydanticObjectId](get_user_manager, [auth_backend])

# ── Зависимости для роутов ───────────────────────────────────────────
current_active_user = fastapi_users.current_user(active=True)
optional_current_user = fastapi_users.current_user(active=True, optional=True)


def require_plan(*plans: str):
    """Гейт по тарифу для эндпоинта. Роль admin проходит всегда.

    Пример: `user = Depends(require_plan("premium"))`.
    Пока нигде не навешан — публичные калькуляторы остаются открытыми.
    """
    allowed = set(plans)

    async def checker(user: User = Depends(current_active_user)) -> User:
        if user.role != "admin" and user.plan not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Ваш тариф не даёт доступа к этой функции",
            )
        return user

    return checker
