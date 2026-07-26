"""
FastAPI сервер для ведической астрологии.

Запуск:
    .venv/bin/python -m uvicorn main:app --reload --port 8000

Документация:
    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pytz
from timezonefinder import TimezoneFinder

from Panchangam import calc_panchang
from nakshatra_calculator import calculate
from nakshatra_calendar import calc_calendar
from sade_sati import calc_sade_sati
from varga import calc_vargas, navamsa_chart, pada_wheel
from vimshottari import calc_vimshottari

from auth.db import init_db
from auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация Mongo/Beanie. Толерантно к ошибке: если база ещё не
    # поднята (например, не задан MONGODB_URI) — публичные калькуляторы
    # продолжают работать, недоступны будут только auth-эндпоинты.
    try:
        await init_db()
        print("[auth] MongoDB подключена, Beanie инициализирован")
    except Exception as e:
        print(f"[auth] init_db не удался ({e}); auth выключен, публичный API работает")
    yield


app = FastAPI(title="Vedic Astrology API", version="1.0.0", lifespan=lifespan)

_tz_finder = TimezoneFinder()

# Разрешаем запросы с фронтенда (любой origin во время разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты авторизации: регистрация, JWT-логин, профиль (соц-логины — следующим шагом)
app.include_router(auth_router)


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


class DashaRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int = 12
    minute: int = 0
    tz: float
    lat: float = 0.0
    lon: float = 0.0
    # 1 — маха-даши, 2 — с антар-дашами, 3+ — пратьянтар и глубже.
    levels: int = 2


class VargaRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    tz: float
    lat: float
    lon: float
    # Какие вибхаги считать. None — все поддерживаемые: 1, 2, 3, 7, 9, 10, 12.
    vargas: Optional[List[int]] = None


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

@app.get("/")
def root():
    return {"status": "ok", "message": "Vedic Astrology API работает"}


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
    # С нутацией — ровно то значение, которое вычитают расчётные модули
    # (см. `nakshatra_calculator.get_aya`). Диагностика обязана показывать
    # используемое число, иначе при разборе расхождений она уводит в сторону.
    aya_now = swe.get_ayanamsa_ex_ut(jd_now, swe.FLG_SWIEPH)[1]
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
        # Текущий период Вимшоттари — только он, без дерева периодов.
        # Полное дерево весит ~40 КБ и нужно далеко не на каждом экране,
        # поэтому оно живёт отдельным /api/dasha, а здесь лежит ровно
        # столько, сколько нужно плитке «текущая маха-даша».
        try:
            birth = datetime(req.year, req.month, req.day, req.hour, req.minute)
            result["dasha_current"] = calc_vimshottari(
                result["moon_sid"], birth, levels=2
            )["current"]
        except Exception as e:
            # Даши не должны ронять весь гороскоп — он самоценен.
            result["dasha_current"] = None
            result["dasha_error"] = str(e)

        # Навамша (D9) — единственная варга, которая едет вместе с гороскопом.
        # Причина: без неё фронт не может ни раскрасить круг 108 пад, ни
        # показать варготтаму, а варготтама — свойство планеты В ЭТОЙ карте,
        # запрашивать его вторым походом в сеть незачем.
        # Цена измерена: 6719 → 8028 Б, то есть +1309 Б (+19%). Блок урезан
        # до невыводимого (см. `varga.navamsa_chart`) — полный весил 3,8 КБ.
        # Остальные вибхаги живут в /api/varga: там весь набор — 19 КБ,
        # втрое больше самого гороскопа, и нужен он точечно.
        try:
            result["navamsa"] = navamsa_chart(
                result["planets"], result["lagna"]["sid_asc"]
            )
        except Exception as e:
            # Как и с дашами: варга не должна ронять гороскоп.
            result["navamsa"] = None
            result["navamsa_error"] = str(e)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/varga")
def varga(req: VargaRequest):
    """Дивизиональные карты (варги): D1, D2 хора, D3, D7, D9, D10, D12.

    Отдельно от `/api/horoscope`: весь набор — около 19 КБ, втрое больше
    самого гороскопа, а нужен он точечно, на экране «варги». Навамша (D9)
    при этом сознательно дублируется в гороскопе — она нужна почти везде
    (круг 108 пад, варготтама), и второй запрос ради неё был бы лишним.

    `vargas` — список номеров; по умолчанию считаются все поддерживаемые.
    """
    try:
        h = calculate(
            year=req.year, month=req.month, day=req.day,
            hour=req.hour, minute=req.minute,
            tz=req.tz, lat=req.lat, lon=req.lon,
        )
        result = calc_vargas(h["planets"], h["lagna"]["sid_asc"], req.vargas)
        # Долготы, от которых посчитаны все варги. Знаки D1 уже лежат в
        # charts["D1"], поэтому здесь только то, чего там нет, — градус.
        # Без него варгу нельзя перепроверить руками, а это ровно то, чем
        # астролог занимается с дивизиональными картами.
        result["positions"] = {
            "lagna": {"sid": round(h["lagna"]["sid_asc"], 6),
                      "deg_in_sign_dms": h["lagna"]["deg_in_sign_dms"]},
            "planets": [
                {"name": p["name"], "sid": p["sid"],
                 "deg_in_sign_dms": p["deg_in_sign_dms"]}
                for p in h["planets"]
            ],
        }
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/varga/pada-wheel")
def varga_pada_wheel():
    """Таблица 108 пад → знак навамши. От даты и места не зависит.

    Разбиение самого зодиака: 27 накшатр × 4 пады = 108 = 12 знаков × 9
    навамш, границы совпадают точно. Нужна кругу пад из
    `content/chart_geometry.json` → `pada_wheel`, в том числе флагу
    варготтамы у секторов.
    """
    return {"padas": pada_wheel(), "vargottama_count": 12}


@app.post("/api/dasha")
def dasha(req: DashaRequest):
    """Периоды Вимшоттари: маха-даши и вложенные антар-даши.

    Отдельно от `/api/horoscope`, потому что полное дерево тяжёлое, а нужно
    не всегда. `levels`: 1 — только маха-даши, 2 — с антар-дашами, глубже —
    пратьянтар и далее.
    """
    try:
        h = calculate(
            year=req.year, month=req.month, day=req.day,
            hour=req.hour, minute=req.minute,
            tz=req.tz, lat=req.lat, lon=req.lon,
        )
        birth = datetime(req.year, req.month, req.day, req.hour, req.minute)
        return calc_vimshottari(h["moon_sid"], birth, levels=req.levels)
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
