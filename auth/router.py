"""Сборка auth-роутов в один APIRouter.

Фундамент: JWT login/logout, регистрация, сброс/подтверждение пароля,
управление своим профилем. Плюс соц-логины (OAuth2: Yandex / VK / Google),
вход через Telegram (не OAuth — Login Widget + HMAC) и админские операции.
"""
from fastapi import APIRouter

from .admin import router as admin_router
from .models import UserCreate, UserRead, UserUpdate
from .oauth import router as oauth_router
from .telegram import router as telegram_router
from .users import auth_backend, fastapi_users

router = APIRouter()

# JWT: POST /auth/jwt/login, POST /auth/jwt/logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
# Регистрация: POST /auth/register
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
# Сброс пароля: POST /auth/forgot-password, /auth/reset-password
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
# Подтверждение email: POST /auth/request-verify-token, /auth/verify
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
# Профиль: GET/PATCH /users/me, админские /users/{id}
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Соц-логины: GET /auth/providers, /auth/{provider}/authorize и /callback.
# Пути заданы внутри модуля целиком, поэтому без prefix. Провайдеры без
# настроек просто не регистрируются.
router.include_router(oauth_router)

# Вход через Telegram: POST /auth/telegram (prefix задан внутри модуля).
# Работает только если задан TELEGRAM_BOT_TOKEN, иначе отдаёт 503.
router.include_router(telegram_router)

# Админские операции: GET /admin/users, PATCH /admin/users/{id}.
# Единственное место, где меняются plan и role.
router.include_router(admin_router)
