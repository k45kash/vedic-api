"""Сборка auth-роутов в один APIRouter.

Фундамент: JWT login/logout, регистрация, сброс/подтверждение пароля,
управление своим профилем. Соц-провайдеры (VK / Yandex / Google) и
Telegram-эндпоинт подключаются здесь же — см. TODO ниже.
"""
from fastapi import APIRouter

from .models import UserCreate, UserRead, UserUpdate
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

# TODO (следующий шаг): соц-провайдеры
#   - Yandex / Google: fastapi_users.get_oauth_router(client, auth_backend, secret)
#   - VK: кастомный httpx-oauth клиент → тот же get_oauth_router
#   - Telegram: отдельный POST /auth/telegram (проверка HMAC по bot-токену)
