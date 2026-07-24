"""Настройки auth — читаются из окружения / .env."""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MongoDB. Railway отдаёт строку подключения в MONGO_URL — принимаем оба
    # имени, чтобы на Railway ничего не прописывать вручную.
    mongodb_uri: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URL"),
    )
    mongo_db: str = "vedic"

    # JWT
    jwt_secret: str = "change-me-generate-a-long-random-string"
    jwt_lifetime_seconds: int = 3600

    # OAuth-провайдеры (заполняются позже; пустые = провайдер выключен)
    yandex_client_id: str = ""
    yandex_client_secret: str = ""
    vk_client_id: str = ""
    vk_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Telegram Login Widget
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    # URLs
    oauth_redirect_base: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"


settings = Settings()
