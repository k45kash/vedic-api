"""Соц-логины (Yandex / VK ID / Google) для SPA-фронтенда.

Почему не штатный `fastapi_users.get_oauth_router`: его callback отдаёт JSON
с токеном прямо в браузер — пользователь остаётся на голой странице API.
Нам нужно вернуть человека на фронт, поэтому callback здесь всегда делает
302-редирект на `{frontend_url}/auth/callback` и передаёт результат во
ФРАГМЕНТЕ URL (после `#`): фрагмент не уходит на сервер и не оседает в
логах/реферерах, в отличие от query-параметров.

Провайдер включается только если он настроен в settings. Не настроен —
роуты просто не регистрируются, приложение поднимается как обычно.

Бэкенд stateless (серверных сессий нет), поэтому весь контекст входа живёт
в подписанном state-JWT: nonce + при необходимости PKCE-verifier. Провайдер
возвращает нам этот state обратно, подпись гарантирует, что его не подменили.

Особенности отдельных провайдеров (PKCE, лишние параметры колбэка, свой
алфавит state) живут в auth/oauth_clients.py и подключаются через хуки —
в этом файле не должно появляться `if provider == "vk"`.

Telegram сюда не входит: он не OAuth (Login Widget + проверка HMAC). В
/auth/providers мы отдаём только имя бота, чтобы фронт мог отрисовать виджет.
"""
import secrets
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt, generate_jwt
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.exceptions import HTTPXOAuthError
from httpx_oauth.oauth2 import BaseOAuth2
from pydantic import BaseModel

from .config import settings
from .oauth_clients import (
    VKIDOAuth2,
    YandexOAuth2,
    client_required_callback_params,
    client_requires_pkce,
    compute_code_challenge,
    decode_state_from,
    encode_state_for,
    exchange_authorization_code,
    generate_code_verifier,
)
from .users import get_jwt_strategy, get_user_manager

# Аудитория и срок жизни state-токена (защита от CSRF на редиректе).
STATE_TOKEN_AUDIENCE = "vedic:oauth-state"
STATE_TOKEN_LIFETIME_SECONDS = 600  # 10 минут — на один вход хватает с запасом
# Ключ, под которым PKCE-verifier едет внутри подписанного state.
STATE_CODE_VERIFIER_KEY = "cv"


# ── Схемы ответов ────────────────────────────────────────────────────
class ProvidersResponse(BaseModel):
    """Что показывать на экране входа.

    `providers` — активные OAuth-провайдеры (Telegram сюда НЕ входит).
    `telegram_bot` — имя бота для Login Widget или None, если не настроен;
    фронту неоткуда узнать его самому.
    """

    providers: list[str]
    telegram_bot: str | None = None


class AuthorizeResponse(BaseModel):
    """URL, куда фронту нужно увести пользователя."""

    authorization_url: str


# ── Фабрика клиентов ─────────────────────────────────────────────────
def _build_clients() -> dict[str, BaseOAuth2]:
    """Собирает клиентов только для настроенных провайдеров."""
    clients: dict[str, BaseOAuth2] = {}

    if settings.yandex_client_id and settings.yandex_client_secret:
        clients["yandex"] = YandexOAuth2(
            settings.yandex_client_id, settings.yandex_client_secret
        )

    # VK ID — публичный клиент: секрета в протоколе нет вообще, защита PKCE.
    # Поэтому включаем по одному vk_client_id. Если vk_client_secret всё же
    # задан, он уедет как service_token («конфиденциальные» приложения).
    if settings.vk_client_id:
        clients["vk"] = VKIDOAuth2(settings.vk_client_id, settings.vk_client_secret)

    if settings.google_client_id and settings.google_client_secret:
        clients["google"] = GoogleOAuth2(
            settings.google_client_id, settings.google_client_secret
        )

    return clients


#: Клиенты активных провайдеров: {"yandex": <client>, ...}
oauth_clients: dict[str, BaseOAuth2] = _build_clients()

#: Имена активных провайдеров в стабильном порядке.
enabled_providers: list[str] = list(oauth_clients)


def get_enabled_providers() -> list[str]:
    """Имена включённых OAuth-провайдеров (для main.py / диагностики)."""
    return list(enabled_providers)


# ── Вспомогательное ──────────────────────────────────────────────────
def _redirect_uri(provider: str) -> str:
    """Куда провайдер вернёт пользователя. Ровно этот URL нужно прописать
    в настройках приложения на стороне провайдера."""
    return f"{settings.oauth_redirect_base.rstrip('/')}/auth/{provider}/callback"


def _frontend_callback() -> str:
    return f"{settings.frontend_url.rstrip('/')}/auth/callback"


def _generate_state_token(code_verifier: str | None = None) -> str:
    """Подписанный одноразовый state: случайный nonce, короткий срок жизни
    и (для PKCE-провайдеров) сам code_verifier.

    Хранить verifier между /authorize и /callback негде — сессий нет. Класть
    его в state безопасно: строка подписана нашим jwt_secret, подделать или
    прочитать-и-переиспользовать чужую нельзя, живёт она минуты.
    """
    payload: dict[str, str] = {
        "nonce": secrets.token_urlsafe(16),
        "aud": STATE_TOKEN_AUDIENCE,
    }
    if code_verifier:
        payload[STATE_CODE_VERIFIER_KEY] = code_verifier
    return generate_jwt(payload, settings.jwt_secret, STATE_TOKEN_LIFETIME_SECONDS)


def _redirect_success(token: str, provider: str) -> RedirectResponse:
    """302 на фронт с приложенным JWT во фрагменте URL."""
    url = f"{_frontend_callback()}#token={quote(token, safe='')}&provider={provider}"
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


def _redirect_error(message: str) -> RedirectResponse:
    """302 на фронт с текстом ошибки — но НЕ 500: человек должен вернуться
    на сайт и увидеть понятное объяснение."""
    url = f"{_frontend_callback()}#error={quote(message, safe='')}"
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


# ── Роутер ───────────────────────────────────────────────────────────
router = APIRouter()


@router.get("/auth/providers", response_model=ProvidersResponse, tags=["auth"])
async def list_providers() -> ProvidersResponse:
    """Что рисовать на экране входа: соц-кнопки и Telegram-виджет."""
    return ProvidersResponse(
        providers=get_enabled_providers(),
        telegram_bot=settings.telegram_bot_username or None,
    )


def _register_provider_routes(provider: str, client: BaseOAuth2) -> None:
    """Регистрирует пару /authorize + /callback для одного провайдера."""

    @router.get(
        f"/auth/{provider}/authorize",
        name=f"oauth:{provider}.authorize",
        response_model=AuthorizeResponse,
        tags=["auth"],
        summary=f"Ссылка на авторизацию через {provider}",
    )
    async def authorize() -> AuthorizeResponse:
        # PKCE — только там, где клиент его требует (сейчас VK ID).
        code_verifier = generate_code_verifier() if client_requires_pkce(client) else None
        state = _generate_state_token(code_verifier)

        authorization_url = await client.get_authorization_url(
            _redirect_uri(provider),
            # Некоторые провайдеры ограничивают алфавит state (VK: без точек),
            # поэтому даём клиенту возможность его перекодировать.
            state=encode_state_for(client, state),
            code_challenge=(
                compute_code_challenge(code_verifier) if code_verifier else None
            ),
            code_challenge_method="S256" if code_verifier else None,
        )
        return AuthorizeResponse(authorization_url=authorization_url)

    @router.get(
        f"/auth/{provider}/callback",
        name=f"oauth:{provider}.callback",
        tags=["auth"],
        summary=f"Возврат от {provider}: всегда 302 на фронтенд",
        response_class=RedirectResponse,
    )
    async def callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
        user_manager=Depends(get_user_manager),
    ) -> RedirectResponse:
        # 1. Пользователь нажал «отказать» или провайдер вернул ошибку.
        if error:
            return _redirect_error(error_description or f"{provider}: {error}")

        if not code or not state:
            return _redirect_error("Провайдер не вернул код авторизации")

        # 2. Проверяем свой state: алфавит провайдера → подпись → срок.
        try:
            state_data = decode_jwt(
                decode_state_from(client, state),
                settings.jwt_secret,
                [STATE_TOKEN_AUDIENCE],
            )
        except jwt.ExpiredSignatureError:
            return _redirect_error("Время на вход истекло, попробуйте ещё раз")
        except (jwt.PyJWTError, ValueError):
            return _redirect_error("Некорректный запрос авторизации")

        # 3. Собираем дополнительные параметры колбэка, если провайдер их
        #    требует (VK ID: device_id).
        extra: dict[str, str] = {}
        for param in client_required_callback_params(client):
            value = request.query_params.get(param)
            if not value:
                return _redirect_error(
                    f"{provider}: в ответе нет обязательного параметра {param}"
                )
            extra[param] = value

        # 4. Меняем код на токен и вытаскиваем id/email аккаунта.
        try:
            token = await exchange_authorization_code(
                client,
                code,
                _redirect_uri(provider),
                code_verifier=state_data.get(STATE_CODE_VERIFIER_KEY),
                # Провайдеру возвращаем ровно ту строку state, что он прислал.
                state=state,
                extra=extra,
            )
        except HTTPXOAuthError:
            return _redirect_error(f"{provider}: не удалось получить токен доступа")

        access_token = token.get("access_token")
        if not access_token:
            return _redirect_error(f"{provider}: пустой ответ сервиса авторизации")

        try:
            account_id, account_email = await client.get_id_email(access_token)
        except HTTPXOAuthError:
            return _redirect_error(f"{provider}: не удалось получить данные профиля")

        if not account_email:
            return _redirect_error(
                "Провайдер не передал e-mail. Разрешите доступ к e-mail "
                "или войдите другим способом"
            )

        # 5. Находим/создаём пользователя. associate_by_email=True —
        #    вход через разные провайдеры с одним e-mail ведёт в один аккаунт.
        try:
            user = await user_manager.oauth_callback(
                provider,
                access_token,
                account_id,
                account_email,
                token.get("expires_at"),
                token.get("refresh_token"),
                request,
                associate_by_email=True,
            )
        except UserAlreadyExists:
            return _redirect_error("Пользователь с таким e-mail уже существует")
        except Exception:  # noqa: BLE001 — наружу отдаём редирект, не 500
            return _redirect_error("Не удалось завершить вход, попробуйте позже")

        if not user.is_active:
            return _redirect_error("Учётная запись отключена")

        # 6. Выдаём собственный JWT приложения и возвращаем человека на фронт.
        app_token = await get_jwt_strategy().write_token(user)
        await user_manager.on_after_login(user, request)
        return _redirect_success(app_token, provider)


for _provider, _client in oauth_clients.items():
    _register_provider_routes(_provider, _client)


__all__ = ["router", "enabled_providers", "get_enabled_providers", "oauth_clients"]
