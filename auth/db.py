"""Подключение к MongoDB и инициализация Beanie.

Beanie 2.0 использует нативный async-драйвер PyMongo (AsyncMongoClient),
motor больше не нужен. Клиент ленивый — реальное соединение открывается
при первой операции (init_beanie создаёт индексы).
"""
from beanie import init_beanie
from pymongo import AsyncMongoClient

from .config import settings
from .models import User

# serverSelectionTimeoutMS=5000 — чтобы старт без доступной базы не висел
# 30 секунд (дефолт), а быстро падал в толерантный except в main.lifespan.
client: AsyncMongoClient = AsyncMongoClient(
    settings.mongodb_uri, serverSelectionTimeoutMS=5000
)


async def init_db() -> None:
    await init_beanie(database=client[settings.mongo_db], document_models=[User])
