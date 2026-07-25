"""Кастомные OAuth2-клиенты для провайдеров, которых нет в httpx-oauth.

Здесь Yandex (обычный OAuth 2.0) и VK ID (OAuth 2.1 с PKCE).
Google берём готовым: `from httpx_oauth.clients.google import GoogleOAuth2`.

Каждый клиент обязан уметь `get_id_email(access_token) -> (id, email|None)` —
именно это fastapi-users кладёт в OAuthAccount.

Дополнительно в этом модуле лежит НЕОБЯЗАТЕЛЬНЫЙ интерфейс расширений
(`OAuthClientExtras` + функции-хелперы внизу файла). Он нужен, чтобы роутер
не знал про особенности конкретных провайдеров: клиент сам объявляет, нужен
ли ему PKCE, какие query-параметры колбэка обязательны и как обменивать код.
Клиенты без этих атрибутов (Yandex, Google) работают по обычному потоку.
"""
import base64
import hashlib
import secrets
from typing import Any, cast

from httpx_oauth.exceptions import GetIdEmailError, GetProfileError
from httpx_oauth.oauth2 import BaseOAuth2, GetAccessTokenError, OAuth2Token


# ── PKCE (RFC 7636) ──────────────────────────────────────────────────
def generate_code_verifier() -> str:
    """code_verifier: строка 43–128 символов из [a-zA-Z0-9_-].

    `token_urlsafe(64)` даёт ~86 символов ровно из нужного алфавита.
    """
    return secrets.token_urlsafe(64)


def compute_code_challenge(code_verifier: str) -> str:
    """S256-челлендж: BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) без паддинга."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _b64url_encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode("utf-8")


# ── Необязательный интерфейс расширений ──────────────────────────────
class OAuthClientExtras:
    """Хуки, которые клиент может переопределить под свои особенности.

    Роутер обращается к ним через функции-хелперы внизу модуля, поэтому
    подмешивать этот класс необязательно: клиенты без него получают
    поведение по умолчанию (обычный OAuth 2.0 без PKCE).
    """

    #: Нужен ли PKCE: роутер сгенерирует code_verifier/code_challenge.
    requires_pkce: bool = False

    #: Query-параметры колбэка, без которых обмен кода невозможен
    #: (например, device_id у VK ID). Роутер их провалидирует и прокинет.
    required_callback_params: tuple[str, ...] = ()

    def encode_state(self, state: str) -> str:
        """Преобразовать наш state перед отправкой провайдеру.

        Нужно там, где провайдер ограничивает алфавит state.
        """
        return state

    def decode_state(self, raw_state: str) -> str:
        """Обратное преобразование для state, пришедшего в колбэке.

        Raises:
            ValueError: state повреждён.
        """
        return raw_state

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        *,
        code_verifier: str | None = None,
        state: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> OAuth2Token:
        """Обмен кода на токен с провайдер-специфичными добавками."""
        raise NotImplementedError


# ── Yandex ───────────────────────────────────────────────────────────
# Документация: https://yandex.ru/dev/id/doc/ru/
YANDEX_AUTHORIZE_ENDPOINT = "https://oauth.yandex.ru/authorize"
YANDEX_ACCESS_TOKEN_ENDPOINT = "https://oauth.yandex.ru/token"
YANDEX_PROFILE_ENDPOINT = "https://login.yandex.ru/info"


class YandexOAuth2(BaseOAuth2[dict[str, Any]]):
    """Яндекс ID (классический OAuth 2.0, authorization code).

    Особенности:
      * профиль отдаётся по `https://login.yandex.ru/info?format=json`
        с нестандартным заголовком `Authorization: OAuth <token>`
        (не `Bearer`!);
      * scope обычно задаётся в настройках приложения на oauth.yandex.ru,
        поэтому по умолчанию мы его не передаём (base_scopes=None).
        Для email нужны права `login:email` (и `login:info` для id).
    """

    display_name = "Yandex"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
        name: str = "yandex",
    ):
        super().__init__(
            client_id,
            client_secret,
            YANDEX_AUTHORIZE_ENDPOINT,
            YANDEX_ACCESS_TOKEN_ENDPOINT,
            # refresh-токен обменивается на том же /token
            YANDEX_ACCESS_TOKEN_ENDPOINT,
            name=name,
            base_scopes=scopes,
            token_endpoint_auth_method="client_secret_post",
        )

    async def get_profile(self, token: str) -> dict[str, Any]:
        """Сырой ответ ручки login.yandex.ru/info."""
        async with self.get_httpx_client() as client:
            response = await client.get(
                YANDEX_PROFILE_ENDPOINT,
                params={"format": "json"},
                headers={**self.request_headers, "Authorization": f"OAuth {token}"},
            )

            if response.status_code >= 400:
                raise GetProfileError(response=response)

            return cast(dict[str, Any], response.json())

    async def get_id_email(self, token: str) -> tuple[str, str | None]:
        try:
            profile = await self.get_profile(token)
        except GetProfileError as e:
            raise GetIdEmailError(response=e.response) from e

        # `id` — числовая строка, `default_email` может отсутствовать,
        # если приложению не выдали право login:email.
        return str(profile["id"]), profile.get("default_email")


# ── VK ID ────────────────────────────────────────────────────────────
# Документация (актуальная, OAuth 2.1):
# https://id.vk.ru/about/business/go/docs/ru/vkid/latest/vk-id/connection/api-integration/api-description
#
# Легаси-поток на oauth.vk.com («email прямо в ответе на обмен кода»)
# ВК отключает — здесь его больше нет.
#
# Ключевые отличия VK ID от обычного OAuth 2.0:
#   * PKCE обязателен (code_challenge S256 + code_verifier);
#   * `device_id` приходит в query колбэка вместе с `code`/`state`
#     и обязателен при обмене кода;
#   * `state` обязателен И в authorize, И в теле обмена кода, минимум
#     32 символа из алфавита [a-zA-Z0-9_-] — точка в него НЕ входит,
#     поэтому «сырой» JWT туда класть нельзя (см. encode_state);
#   * `client_secret` не используется вообще. Приложение публичное,
#     защита — PKCE. Для «конфиденциальных» приложений вместо секрета
#     передаётся `service_token` из настроек приложения (опционально);
#   * email отдаётся только ручкой /oauth2/user_info при scope `email`.
VKID_AUTHORIZE_ENDPOINT = "https://id.vk.ru/authorize"
VKID_ACCESS_TOKEN_ENDPOINT = "https://id.vk.ru/oauth2/auth"
VKID_USER_INFO_ENDPOINT = "https://id.vk.ru/oauth2/user_info"
VKID_BASE_SCOPES = ["vkid.personal_info", "email"]


class VKIDOAuth2(OAuthClientExtras, BaseOAuth2[dict[str, Any]]):
    """VK ID (OAuth 2.1 + PKCE)."""

    display_name = "VK ID"
    requires_pkce = True
    required_callback_params = ("device_id",)

    def __init__(
        self,
        client_id: str,
        client_secret: str = "",
        scopes: list[str] | None = None,
        name: str = "vk",
    ):
        """
        Args:
            client_id: ID приложения из кабинета VK ID.
            client_secret: НЕ используется как OAuth-секрет. Если заполнен,
                уезжает как `service_token` (нужен только «конфиденциальным»
                приложениям). Пустая строка — нормальный режим.
        """
        super().__init__(
            client_id,
            client_secret,
            VKID_AUTHORIZE_ENDPOINT,
            VKID_ACCESS_TOKEN_ENDPOINT,
            # refresh тоже идёт на /oauth2/auth, но требует device_id, который
            # мы не храним → отключаем, чтобы не звать заведомо ломаный запрос.
            None,
            name=name,
            base_scopes=scopes if scopes is not None else VKID_BASE_SCOPES,
            token_endpoint_auth_method="client_secret_post",
        )
        self.service_token = client_secret or None

    # -- state: VK не принимает точки, а наш state — это JWT ----------
    def encode_state(self, state: str) -> str:
        """JWT → base64url без паддинга (алфавит [A-Za-z0-9_-], длина > 32)."""
        return _b64url_encode(state)

    def decode_state(self, raw_state: str) -> str:
        try:
            return _b64url_decode(raw_state)
        except Exception as e:  # noqa: BLE001 — наружу отдаём один тип ошибки
            raise ValueError("VK ID: повреждённый state") from e

    # -- обмен кода --------------------------------------------------
    async def get_access_token(
        self, code: str, redirect_uri: str, code_verifier: str | None = None
    ) -> OAuth2Token:
        # Базовая сигнатура httpx-oauth не умеет передать device_id/state,
        # без которых VK ID код не примет. Пользуйтесь exchange_code().
        raise GetAccessTokenError(
            "VK ID требует device_id и state — используйте exchange_code()"
        )

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        *,
        code_verifier: str | None = None,
        state: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> OAuth2Token:
        extra = extra or {}
        device_id = extra.get("device_id")
        if not device_id:
            raise GetAccessTokenError("VK ID: в колбэке нет device_id")
        if not code_verifier:
            raise GetAccessTokenError("VK ID: потерян code_verifier (PKCE)")
        if not state:
            raise GetAccessTokenError("VK ID: потерян state")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "device_id": device_id,
            # VK требует вернуть ту же строку состояния, что ушла в authorize.
            "state": state,
        }
        if self.service_token:
            data["service_token"] = self.service_token

        async with self.get_httpx_client() as client:
            # Content-Type: application/x-www-form-urlencoded (httpx ставит сам
            # для data=...). client_secret здесь не передаётся намеренно.
            response = await client.post(
                self.access_token_endpoint,
                data=data,
                headers=self.request_headers,
            )
            payload = self.get_json(response, exc_class=GetAccessTokenError)

            if response.status_code >= 400 or "error" in payload:
                raise GetAccessTokenError(
                    str(
                        payload.get("error_description")
                        or payload.get("error")
                        or "VK ID: не удалось обменять код на токен"
                    ),
                    response,
                )

            return OAuth2Token(payload)

    # -- профиль -----------------------------------------------------
    async def get_profile(self, token: str) -> dict[str, Any]:
        """POST /oauth2/user_info → {"user": {...}}."""
        async with self.get_httpx_client() as client:
            response = await client.post(
                VKID_USER_INFO_ENDPOINT,
                data={"access_token": token, "client_id": self.client_id},
                headers=self.request_headers,
            )

            if response.status_code >= 400:
                raise GetProfileError(response=response)

            payload = cast(dict[str, Any], response.json())
            if "error" in payload:
                raise GetProfileError(
                    str(payload.get("error_description") or payload["error"]),
                    response=response,
                )

            return payload

    async def get_id_email(self, token: str) -> tuple[str, str | None]:
        try:
            profile = await self.get_profile(token)
        except GetProfileError as e:
            raise GetIdEmailError(e.message, response=e.response) from e

        user = profile.get("user") or {}
        user_id = user.get("user_id")
        if user_id is None:
            raise GetIdEmailError("VK ID: в ответе user_info нет user_id")

        # email придёт только при выданном праве `email` и только если он
        # у пользователя вообще привязан — иначе None, это допустимо.
        return str(user_id), user.get("email")


# ── Хелперы для роутера (duck typing, без знания о провайдерах) ──────
def client_requires_pkce(client: BaseOAuth2) -> bool:
    return bool(getattr(client, "requires_pkce", False))


def client_required_callback_params(client: BaseOAuth2) -> tuple[str, ...]:
    return tuple(getattr(client, "required_callback_params", ()))


def encode_state_for(client: BaseOAuth2, state: str) -> str:
    encode = getattr(client, "encode_state", None)
    return encode(state) if encode else state


def decode_state_from(client: BaseOAuth2, raw_state: str) -> str:
    """Raises: ValueError — state повреждён."""
    decode = getattr(client, "decode_state", None)
    return decode(raw_state) if decode else raw_state


async def exchange_authorization_code(
    client: BaseOAuth2,
    code: str,
    redirect_uri: str,
    *,
    code_verifier: str | None = None,
    state: str | None = None,
    extra: dict[str, str] | None = None,
) -> OAuth2Token:
    """Обмен кода на токен: через хук клиента, иначе — обычный OAuth 2.0."""
    hook = getattr(client, "exchange_code", None)
    if hook is not None:
        return await hook(
            code,
            redirect_uri,
            code_verifier=code_verifier,
            state=state,
            extra=extra or {},
        )
    return await client.get_access_token(code, redirect_uri, code_verifier)


__all__ = [
    "YandexOAuth2",
    "VKIDOAuth2",
    "OAuthClientExtras",
    "generate_code_verifier",
    "compute_code_challenge",
    "client_requires_pkce",
    "client_required_callback_params",
    "encode_state_for",
    "decode_state_from",
    "exchange_authorization_code",
]
