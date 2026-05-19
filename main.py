"""
FastAPI сервер для ведической астрологии.

Запуск:
    .venv/bin/python -m uvicorn main:app --reload --port 8000

Документация:
    http://localhost:8000/docs
"""

import os
from datetime import date, datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import pytz
from timezonefinder import TimezoneFinder

from Panchangam import calc_panchang
from nakshatra_calculator import calculate
from nakshatra_calendar import calc_calendar
from sade_sati import calc_sade_sati

app = FastAPI(title="Vedic Astrology API", version="1.0.0")

_tz_finder = TimezoneFinder()

# Разрешаем запросы с фронтенда (любой origin во время разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Модели запросов ────────────────────────────────────────────────────────

class PanchangRequest(BaseModel):
    date_start: date
    date_end: date
    tz: float
    lat: float = 0.0
    lon: float = 0.0
    elev_m: float = 0.0


class HoroscopeRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    tz: float
    lat: float
    lon: float


class CalendarRequest(BaseModel):
    date_start: date
    date_end: date
    tz: float
    lat: float = 0.0
    lon: float = 0.0
    step_h: float = 1.0
    prec_sec: float = 1.0


class SadeSatiRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int = 12
    minute: int = 0
    tz: float
    lat: float = 0.0
    lon: float = 0.0
    search_from: Optional[date] = None
    search_to:   Optional[date] = None


# ─── Эндпоинты ──────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return {"status": "ok", "message": "Vedic Astrology API работает"}


@app.get("/sade-sati")
def sade_sati_page():
    return FileResponse(os.path.join(STATIC_DIR, "sade-sati.html"))


@app.get("/app")
def app_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/tz")
def resolve_tz(lat: float, lon: float,
               year: int, month: int, day: int,
               hour: int = 12, minute: int = 0):
    """Возвращает IANA-зону и offset для координат на конкретную дату.

    Учитывает исторические переходы — декретное время в СССР, отмену
    летнего времени в России в 2011, возврат на «зимнее» в 2014 и т.п.
    """
    tz_name = _tz_finder.timezone_at(lng=lon, lat=lat)
    if not tz_name:
        raise HTTPException(404, "Часовой пояс по этим координатам не определён")
    try:
        tz = pytz.timezone(tz_name)
        local = tz.localize(datetime(year, month, day, hour, minute), is_dst=None)
    except pytz.exceptions.AmbiguousTimeError:
        local = pytz.timezone(tz_name).localize(
            datetime(year, month, day, hour, minute), is_dst=False)
        return {"tz_name": tz_name,
                "offset_hours": local.utcoffset().total_seconds() / 3600,
                "ambiguous": True,
                "note": "Перевод часов осенью — взято зимнее время"}
    except pytz.exceptions.NonExistentTimeError:
        raise HTTPException(400, "Это время не существует — был перевод часов вперёд")
    offset = local.utcoffset().total_seconds() / 3600
    return {
        "tz_name":      tz_name,
        "offset_hours": offset,
        "offset_str":   f"UTC{offset:+g}",
        "is_dst":       bool(local.dst()),
    }


@app.get("/api/debug")
def debug():
    import os, sys
    from nakshatra_calculator import EPHE_PATH
    ephe_files = []
    try:
        ephe_files = os.listdir(EPHE_PATH)
    except Exception as e:
        ephe_files = [str(e)]
    import swisseph as swe
    from datetime import datetime, timezone
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    now = datetime.now(timezone.utc)
    jd_now = swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60)
    aya_now = swe.get_ayanamsa_ut(jd_now)
    return {
        "python": sys.version,
        "ephe_path": EPHE_PATH,
        "ephe_files": sorted(ephe_files),
        "sidm_lahiri_const": int(swe.SIDM_LAHIRI),
        "aya_now": round(aya_now, 6),
        "aya_now_date": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


@app.post("/api/panchang")
def panchang(req: PanchangRequest):
    """Панчанг: титхи, мухурты, хоры за период."""
    try:
        result = calc_panchang(
            date_start=req.date_start,
            date_end=req.date_end,
            tz=req.tz,
            lat=req.lat,
            lon=req.lon,
            elev_m=req.elev_m,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/horoscope")
def horoscope(req: HoroscopeRequest):
    """Гороскоп: накшатра, лагна, планеты по дате и месту рождения."""
    try:
        result = calculate(
            year=req.year,
            month=req.month,
            day=req.day,
            hour=req.hour,
            minute=req.minute,
            tz=req.tz,
            lat=req.lat,
            lon=req.lon,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calendar")
def calendar(req: CalendarRequest):
    """Календарь транзитов Луны по накшатрам за период."""
    try:
        result = calc_calendar(
            date_start=req.date_start,
            date_end=req.date_end,
            tz=req.tz,
            lat=req.lat,
            lon=req.lon,
            step_h=req.step_h,
            prec_sec=req.prec_sec,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sade-sati")
def sade_sati(req: SadeSatiRequest):
    """Сади Сати + Аштама Шани + Кантака Шани по дате рождения.

    По умолчанию ищет периоды от даты рождения до +120 лет.
    """
    try:
        result = calc_sade_sati(
            year=req.year, month=req.month, day=req.day,
            hour=req.hour, minute=req.minute,
            tz=req.tz, lat=req.lat, lon=req.lon,
            search_from=req.search_from,
            search_to=req.search_to,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
