"""Общая настройка тестов расчётного ядра.

Тесты пишутся против ЭТАЛОНА, а не против текущего вывода: сверяемся либо со
Swiss Ephemeris напрямую, либо с внешними калькуляторами, либо с внутренней
непротиворечивостью модулей между собой. Смысл в том, чтобы ловить тихие
дефекты — те, что не роняют сервис, а просто выдают неверное число.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def swe():
    """Swiss Ephemeris с путём к эфемеридам и режимом Лахири."""
    import swisseph as _swe
    from nakshatra_calculator import EPHE_PATH

    _swe.set_ephe_path(EPHE_PATH)
    _swe.set_sid_mode(_swe.SIDM_LAHIRI)
    return _swe


@pytest.fixture(scope="session")
def content_dir() -> Path:
    """Контентная база коллеги (лежит внутри фронтенда — см. docs/PLAN.md)."""
    return ROOT / "frontend-nuxt" / "content"


# Контрольная карта, на которой сверялись вручную с Prokerala и Serennu:
# 15 июня 1990, 14:30, Москва. Летом 1990 Москва жила по UTC+4 (MSD).
BIRTH_MOSCOW_1990 = dict(
    year=1990, month=6, day=15, hour=14, minute=30,
    tz=4.0, lat=55.7558, lon=37.6173,
)
