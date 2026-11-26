"""Режим долгот для одного расчёта и всех поисков границ внутри него."""
from contextvars import ContextVar
from typing import Literal

import swisseph as swe

PositionMode = Literal["apparent", "geometric"]
_mode = ContextVar("position_mode", default="apparent")


def calculate_in_mode(mode: PositionMode, calculator, *args, **kwargs):
    token = _mode.set(mode)
    try:
        return calculator(*args, **kwargs)
    finally:
        _mode.reset(token)


def longitude_flags() -> int:
    return swe.FLG_SWIEPH | (swe.FLG_TRUEPOS if _mode.get() == "geometric" else 0)
