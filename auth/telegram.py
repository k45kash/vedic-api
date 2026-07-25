"""Вход через Telegram Login Widget.

Telegram — НЕ OAuth2: виджет на фронте отдаёт готовый объект
`{id, first_name, last_name?, username?, photo_url?, auth_date, hash}`,
подписанный ботом. Наша задача — проверить подпись и выдать свой JWT,
тот же самый, что и `/auth/jwt/login`.

Алгоритм проверки (https://core.telegram.org/widgets/login-legacy):
    data_check_string = все поля КРОМЕ hash в виде "key=value",
                        отсортированные по ключу, склеенные через "\\n"
    secret_key        = SHA256(<bot_token>)          ← бинарный дайджест
    if hex(HMAC_SHA256(data_check_string, secret_key)) == hash: данные от Telegram

Плюс проверка свежести `auth_date` — документация прямо рекомендует её,
чтобы перехваченный один раз объект нельзя было переиспользовать вечно.
"""
import hashlib
import hmac
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users import exceptions as fu_exceptions
from pydantic import BaseModel, ConfigDict

from .config import settings
from .users import UserManager, get_jwt_strategy, get_user_manager

router = APIRouter(prefix="/auth", tags=["auth"])

# Имя провайдера в User.oauth_accounts — по нему ищем существующего юзера.
OAUTH_NAME = "telegram"

# Синтетический домен для e-mail. Хотелось бы «telegram.local», но `.local`
# — special-use имя, и pydantic EmailStr (email-validator) его отвергает,
# из-за чего сломалась бы отдача UserRead. Берём нейтральный несуществующий
# домен: почта на него никогда не отправляется, пароль у таких аккаунтов
# случайный и пользователю не известен.
EMAIL_DOMAIN = "telegram.login"

# Максимальный возраст подписи Telegram — 24 часа.
AUTH_MAX_AGE_SECONDS = 24 * 60 * 60
# Допуск на расхождение часов сервера и Telegram (объект «из будущего»).
CLOCK_SKEW_SECONDS = 5 * 60

# У Telegram нет access_token — виджет его не выдаёт. Кладём заглушку,
# т.к. поле обязательно в схеме OAuthAccount fastapi-users.
FAKE_ACCESS_TOKEN = "telegram-login-widget"


class TelegramAuthData(BaseModel):
    """Полезная нагрузка Telegram Login Widget.

    `extra="allow"` не случайно: Telegram может добавить новые поля, и они
    участвуют в подписи. Отбрасывать их нельзя — иначе data_check_string
    не сойдётся и валидный вход будет отвергнут.
    """

    model_config = ConfigDict(extra="allow")

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


def build_data_check_string(data: Dict[str, Any]) -> str:
    """Собрать data_check_string: "key=value" без hash, сортировка по ключу."""
    pairs = sorted((k, v) for k, v in data.items() if k != "hash")
    return "\n".join(f"{key}={value}" for key, value in pairs)


def verify_telegram_hash(data: Dict[str, Any], bot_token: str) -> bool:
    """Проверить подпись объекта Telegram Login Widget.

    `data` — словарь всех полученных полей, включая `hash`.
    Сравнение через `hmac.compare_digest` — постоянное время, чтобы по
    задержке ответа нельзя было подбирать хэш побайтово.
    """
    received_hash = str(data.get("hash", ""))
    if not received_hash:
        return False

    data_check_string = build_data_check_string(data)
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_hash, received_hash)


def is_auth_date_fresh(auth_date: int, now: Optional[int] = None) -> bool:
    """Свежесть подписи: не старше 24 часов и не «из будущего»."""
    now = int(time.time()) if now is None else now
    age = now - auth_date
    return -CLOCK_SKEW_SECONDS <= age <= AUTH_MAX_AGE_SECONDS


@router.post("/telegram", summary="Вход через Telegram Login Widget")
async def telegram_login(
    payload: TelegramAuthData,
    user_manager: UserManager = Depends(get_user_manager),
) -> Dict[str, str]:
    """Проверить подпись Telegram и выдать JWT.

    Ответ идентичен `/auth/jwt/login`: `{"access_token": ..., "token_type": "bearer"}`.
    """
    # Провайдер выключен, если токен бота не задан — приложение при этом
    # продолжает работать, ломается только этот эндпоинт.
    if not settings.telegram_bot_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Вход через Telegram не настроен",
        )

    # exclude_none: Telegram не присылает пустые поля вовсе, и в подписи
    # их тоже нет. by_alias не нужен — имена полей совпадают с виджетом.
    data = payload.model_dump(exclude_none=True)

    if not verify_telegram_hash(data, settings.telegram_bot_token):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Подпись Telegram недействительна",
        )

    if not is_auth_date_fresh(payload.auth_date):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Данные авторизации Telegram устарели, повторите вход",
        )

    # Найти-или-создать. Используем штатный `oauth_callback` менеджера,
    # а не прямую работу с Beanie: он ищет юзера по (oauth_name, account_id)
    # — т.е. повторный вход тем же Telegram-аккаунтом идемпотентен, — а при
    # создании сам генерирует случайный пароль (secrets.token_urlsafe внутри
    # password_helper.generate()) и хэширует его тем же password_helper,
    # что и обычная регистрация.
    #
    # associate_by_email=False намеренно: иначе тот, кто заранее
    # зарегистрируется на синтетический адрес tg<id>@..., перехватил бы
    # аккаунт реального владельца Telegram-профиля.
    account_email = f"tg{payload.id}@{EMAIL_DOMAIN}"
    try:
        user = await user_manager.oauth_callback(
            oauth_name=OAUTH_NAME,
            access_token=FAKE_ACCESS_TOKEN,
            account_id=str(payload.id),
            account_email=account_email,
            associate_by_email=False,
            # Личность подтверждена самим Telegram, а подтверждать
            # синтетический e-mail нечем и незачем.
            is_verified_by_default=True,
        )
    except fu_exceptions.UserAlreadyExists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Аккаунт с таким адресом уже существует",
        )

    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Учётная запись заблокирована",
        )

    token = await get_jwt_strategy().write_token(user)
    return {"access_token": token, "token_type": "bearer"}
