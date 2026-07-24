"""Авторизация: self-hosted fastapi-users + MongoDB (Beanie), JWT.

Провайдеры (VK / Yandex / Google / Telegram) подключаются отдельно —
см. auth/router.py. Фундамент здесь: модель User, менеджер, JWT-бэкенд,
зависимости current_active_user / require_plan для будущего гейтинга.
"""
