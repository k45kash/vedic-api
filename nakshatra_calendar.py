"""
╔═══════════════════════════════════════════════════════════════════╗
║   КАЛЕНДАРЬ НАКШАТР ЛУНЫ — транзиты за выбранный период          ║
╚═══════════════════════════════════════════════════════════════════╝

Вычисляет точное время входа/выхода Луны из каждой накшатры
и каждой пады. Поиск переходов — бинарное деление, точность ±1 сек.

Установка:  pip install pyswisseph

Запуск:
    python nakshatra_calendar.py                                  — ввод
    python nakshatra_calendar.py --examples                       — примеры
    python nakshatra_calendar.py --period 2026-01-01 2026-01-15 3 55.75 37.62
"""

import math
import sys
from datetime import datetime, timedelta, date

try:
    import swisseph as swe
    USE_SWISSEPH = True
    import os as _os
    # ephe/ лежит рядом со скриптом; SE_EPHE_PATH переопределяет если нужно
    EPHE_PATH = _os.environ.get(
        "SE_EPHE_PATH",
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ephe")
    )
    swe.set_ephe_path(EPHE_PATH)
    swe.set_sid_mode(swe.SIDM_LAHIRI)   # глобальный режим — задаётся один раз
except ImportError:
    USE_SWISSEPH = False
    print("⚠  pyswisseph не установлен. pip install pyswisseph\n")

# ═══════════════════════════════════════════════════════════
#  СПРАВОЧНИК НАКШАТР
# ═══════════════════════════════════════════════════════════

NAKSHATRAS = [
    {"num":1,  "name":"Ashwini",        "ru":"Ашвини",          "lord":"Кету",     "gana":"Devata"},
    {"num":2,  "name":"Bharani",        "ru":"Бхарани",         "lord":"Венера",   "gana":"Manushya"},
    {"num":3,  "name":"Krittika",       "ru":"Криттика",        "lord":"Солнце",   "gana":"Rakshasa"},
    {"num":4,  "name":"Rohini",         "ru":"Рохини",          "lord":"Луна",     "gana":"Manushya"},
    {"num":5,  "name":"Mrigashira",     "ru":"Мригашира",       "lord":"Марс",     "gana":"Devata"},
    {"num":6,  "name":"Ardra",          "ru":"Ардра",           "lord":"Раху",     "gana":"Manushya"},
    {"num":7,  "name":"Punarvasu",      "ru":"Пунарвасу",       "lord":"Юпитер",   "gana":"Devata"},
    {"num":8,  "name":"Pushya",         "ru":"Пушья",           "lord":"Сатурн",   "gana":"Devata"},
    {"num":9,  "name":"Ashlesha",       "ru":"Ашлеша",          "lord":"Меркурий", "gana":"Rakshasa"},
    {"num":10, "name":"Magha",          "ru":"Магха",           "lord":"Кету",     "gana":"Rakshasa"},
    {"num":11, "name":"Purvaphalguni",  "ru":"Пурва Пхалгуни",  "lord":"Венера",   "gana":"Manushya"},
    {"num":12, "name":"Uttaraphalguni", "ru":"Уттара Пхалгуни", "lord":"Солнце",   "gana":"Manushya"},
    {"num":13, "name":"Hasta",          "ru":"Хаста",           "lord":"Луна",     "gana":"Devata"},
    {"num":14, "name":"Chitra",         "ru":"Читра",           "lord":"Марс",     "gana":"Rakshasa"},
    {"num":15, "name":"Swati",          "ru":"Свати",           "lord":"Раху",     "gana":"Devata"},
    {"num":16, "name":"Vishakha",       "ru":"Вишакха",         "lord":"Юпитер",   "gana":"Rakshasa"},
    {"num":17, "name":"Anuradha",       "ru":"Анурадха",        "lord":"Сатурн",   "gana":"Devata"},
    {"num":18, "name":"Jyeshtha",       "ru":"Джьештха",        "lord":"Меркурий", "gana":"Rakshasa"},
    {"num":19, "name":"Mula",           "ru":"Мула",            "lord":"Кету",     "gana":"Rakshasa"},
    {"num":20, "name":"Purvashadha",    "ru":"Пурвашадха",      "lord":"Венера",   "gana":"Manushya"},
    {"num":21, "name":"Uttarashadha",   "ru":"Уттарашадха",     "lord":"Солнце",   "gana":"Manushya"},
    {"num":22, "name":"Shravana",       "ru":"Шравана",         "lord":"Луна",     "gana":"Devata"},
    {"num":23, "name":"Dhanishtha",     "ru":"Дхаништха",       "lord":"Марс",     "gana":"Rakshasa"},
    {"num":24, "name":"Shatabhisha",    "ru":"Шатабхиша",       "lord":"Раху",     "gana":"Rakshasa"},
    {"num":25, "name":"Purvabhadra",    "ru":"Пурвабхадра",     "lord":"Юпитер",   "gana":"Manushya"},
    {"num":26, "name":"Uttarabhadra",   "ru":"Уттарабхадра",    "lord":"Сатурн",   "gana":"Devata"},
    {"num":27, "name":"Revati",         "ru":"Ревати",          "lord":"Меркурий", "gana":"Devata"},
]

NK_SIZE   = 360.0 / 27      # 13.3333…°
PADA_SIZE = NK_SIZE / 4     #  3.3333…°

# ═══════════════════════════════════════════════════════════
#  УТИЛИТЫ ВРЕМЕНИ
# ═══════════════════════════════════════════════════════════

def dt_to_jd(dt: datetime) -> float:
    """datetime (UTC naive) → Julian Day."""
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1; m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

def jd_to_dt_utc(jd: float) -> datetime:
    """Julian Day → datetime UTC."""
    jd2 = jd + 0.5
    Z = int(jd2); F = jd2 - Z
    A = Z if Z < 2299161 else (lambda a: Z + 1 + a - int(a / 4))(int((Z - 1867216.25) / 36524.25))
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    df   = B - D - int(30.6001 * E) + F
    day  = int(df); frac = df - day
    hf   = frac * 24; h = int(hf)
    mf   = (hf - h) * 60; mn = int(mf)
    sec  = int((mf - mn) * 60 + 0.5)
    mon  = E - 1 if E < 14 else E - 13
    yr   = C - 4716 if mon > 2 else C - 4715
    # overflow
    if sec >= 60:  sec -= 60; mn += 1
    if mn  >= 60:  mn  -= 60; h  += 1
    if h   >= 24:  h   -= 24; day += 1
    return datetime(yr, mon, day, h, mn, sec)

def jd_to_local(jd: float, tz: float) -> datetime:
    """JD → local datetime."""
    return jd_to_dt_utc(jd) + timedelta(hours=tz)

def fmt_dt(dt: datetime, show_date: bool) -> str:
    """Форматирование: 'ДД.ММ ЧЧ:ММ:СС' или 'ЧЧ:ММ:СС'."""
    if show_date:
        return dt.strftime("%d.%m %H:%M:%S")
    return dt.strftime("%H:%M:%S")

def fmt_range(dt_s: datetime, dt_e: datetime) -> str:
    """'дата? время → дата? время' — дата у конца только если другой день."""
    s = dt_s.strftime("%d.%m.%Y %H:%M:%S")
    same_day = dt_s.date() == dt_e.date()
    e = dt_e.strftime("%H:%M:%S") if same_day else dt_e.strftime("%d.%m.%Y %H:%M:%S")
    return s, e

def fmt_duration(hours: float) -> str:
    h = int(hours); m = int((hours - h) * 60)
    return f"{h}ч {m:02d}м"

def dms(lon: float) -> str:
    """Полная сидерическая долгота 0-360° → ДДД°ММ'СС\"."""
    lon = lon % 360
    ts  = round(lon * 3600)
    s   = ts % 60; tm = ts // 60; m = tm % 60; d = tm // 60
    return f"{d}\u00b0{m:02d}'{s:02d}\""

# ═══════════════════════════════════════════════════════════
#  DELTA T  (TT - UT)
# ═══════════════════════════════════════════════════════════
_DT_TABLE = [
    (1620, 124), (1700, 22),  (1800, 13),  (1900, 3),
    (1950, 29),  (1960, 33),  (1970, 40),  (1975, 45),
    (1980, 50),  (1985, 54),  (1990, 57),  (1995, 61),
    (2000, 63),  (2005, 65),  (2010, 66),  (2015, 68),
    (2020, 69),  (2025, 69),  (2030, 70),
]

def _delta_t(jd: float) -> float:
    year = 2000.0 + (jd - 2451545.0) / 365.25
    for i in range(len(_DT_TABLE) - 1):
        y0, d0 = _DT_TABLE[i]; y1, d1 = _DT_TABLE[i+1]
        if y0 <= year <= y1:
            return d0 + (d1 - d0) * (year - y0) / (y1 - y0)
    return float(_DT_TABLE[-1][1])

def _jd_to_tt(jd: float) -> float:
    return jd + _delta_t(jd) / 86400.0

# ═══════════════════════════════════════════════════════════
#  ЭФЕМЕРИДЫ — детектирование
# ═══════════════════════════════════════════════════════════

def _detect_eph() -> str:
    if not USE_SWISSEPH: return "MEEUS"
    try:
        _, rf = swe.calc_ut(2451545.0, swe.MOON, swe.FLG_SWIEPH)
        if rf & swe.FLG_SWIEPH:  return "SWISS"
        if rf & swe.FLG_MOSEPH:  return "MOSHIER"
        return "JPL"
    except Exception:
        return "MOSHIER"

_EPH_MODE = _detect_eph()
_EPH_NOTE = {
    "SWISS":   "Swiss Ephemeris (DE431, ~0.001\")",
    "MOSHIER": "Swiss Ephemeris — Moshier (~1-2\", без файлов .se1)",
    "JPL":     "Swiss Ephemeris — JPL",
    "MEEUS":   "Meeus algorithm (~1-2°, Moon only)",
}.get(_EPH_MODE, _EPH_MODE)

# ═══════════════════════════════════════════════════════════
#  ЛУНА
# ═══════════════════════════════════════════════════════════

def get_ayanamsha(jd: float) -> float:
    if USE_SWISSEPH:
        return swe.get_ayanamsa_ut(jd)   # _ut принимает UT напрямую, без ΔT
    # ИСПРАВЛЕНО: эпоха J2000 (2451545.0), а не B1900 (2415020.0)
    return 23.85 + (jd - 2451545.0) / 365.25 * 0.013958

def moon_sid(jd: float, topo: bool = False, lat: float = 0.0, lon: float = 0.0) -> float:
    """Сидерическая долгота Луны (0-360°). topo=True — топоцентрическая."""
    global _EPH_MODE, _EPH_NOTE
    aya = get_ayanamsha(jd)
    if USE_SWISSEPH:
        fl = swe.FLG_SWIEPH
        if topo and (lat != 0.0 or lon != 0.0):
            swe.set_topo(lon, lat, 0)
            fl |= swe.FLG_TOPOCTR
        pos, ret = swe.calc_ut(jd, swe.MOON, fl)
        if ret & swe.FLG_MOSEPH and _EPH_MODE != "MOSHIER":
            _EPH_MODE = "MOSHIER"
            _EPH_NOTE = "Swiss Ephemeris — Moshier (~1-2\", без файлов .se1)"
        elif ret & swe.FLG_SWIEPH and _EPH_MODE == "MOSHIER":
            _EPH_MODE = "SWISS"
            _EPH_NOTE = "Swiss Ephemeris (DE431, ~0.001\")"
        trop = pos[0]
    else:
        # Meeus с коррекцией Delta T
        jd_tt = _jd_to_tt(jd)
        T  = (jd_tt - 2451545.0) / 36525.0
        L0 = (218.3164477 + 481267.88123421 * T) % 360
        Mm = (134.9633964 + 477198.8676313  * T) % 360
        Ms = (357.5291092 +  35999.0502909  * T) % 360
        F  = ( 93.2720950 + 483202.0175233  * T) % 360
        D  = (297.8501921 + 445267.1114034  * T) % 360
        dL = (6.288774 * math.sin(math.radians(Mm))
            + 1.274027 * math.sin(math.radians(2*D - Mm))
            + 0.658314 * math.sin(math.radians(2*D))
            + 0.213618 * math.sin(math.radians(2*Mm))
            - 0.185116 * math.sin(math.radians(Ms))
            - 0.114332 * math.sin(math.radians(2*F)))
        trop = (L0 + dL) % 360
    return (trop - aya) % 360

def nk_idx(jd: float, lat: float = 0.0, lon: float = 0.0) -> int:
    return int(moon_sid(jd, lat=lat, lon=lon) / NK_SIZE) % 27

def pada_idx(jd: float, lat: float = 0.0, lon: float = 0.0) -> int:
    return int((moon_sid(jd, lat=lat, lon=lon) % NK_SIZE) / PADA_SIZE)

def boundary_flag(moon_lon: float, moon_speed_dpd: float = 13.2) -> str:
    """
    Предупреждение если Луна входит в паду уже близко к её концу
    (пада окажется очень короткой — менее 30 мин).
    moon_lon — сидерическая долгота на ВХОДЕ в паду.
    """
    pos_in_pada = moon_lon % PADA_SIZE
    dist_to_end = PADA_SIZE - pos_in_pada          # осталось до следующей границы
    margin_min  = dist_to_end / (moon_speed_dpd / (24 * 60))
    if margin_min < 10:
        return f"  ⚠ пада заканчивается через {margin_min:.0f} мин"
    if margin_min < 30:
        return f"  ! короткая пада ({margin_min:.0f} мин)"
    return ""

# ═══════════════════════════════════════════════════════════
#  БИНАРНЫЙ ПОИСК ПЕРЕХОДА
# ═══════════════════════════════════════════════════════════

def _bisect(jd_lo: float, jd_hi: float, state_fn, state_lo, prec_sec: float = 1.0) -> float:
    """
    Общий бинарный поиск момента, когда state_fn() меняет значение.
    Возвращает JD первого момента с новым значением.
    """
    prec = prec_sec / 86400.0
    while jd_hi - jd_lo > prec:
        mid = (jd_lo + jd_hi) / 2
        if state_fn(mid) == state_lo:
            jd_lo = mid
        else:
            jd_hi = mid
    return jd_hi

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ: накшатры + пады за период
# ═══════════════════════════════════════════════════════════

def calc_calendar(
        date_start: date, date_end: date,
        tz: float, lat: float = 0.0, lon: float = 0.0,
        step_h: float = 1.0, prec_sec: float = 1.0,
) -> list[dict]:
    """
    Возвращает список накшатр за период.
    Каждая накшатра содержит список пад со временем входа/выхода
    и позицией Луны.

    Структура записи:
        nk_num, name, ru, lord, gana
        jd_start, jd_end
        dt_start, dt_end      ← local datetime
        duration_h
        moon_start, moon_end  ← сидерические долготы (°)
        padas: [
            { pada: 1-4,
              jd_start, jd_end, dt_start, dt_end,
              moon_start, moon_end,
              duration_h }
        ]
    """
    # Границы в UTC
    jd_s = dt_to_jd(datetime(date_start.year, date_start.month, date_start.day))   - tz/24
    jd_e = dt_to_jd(datetime(date_end.year,   date_end.month,   date_end.day, 23, 59, 59)) - tz/24

    step = step_h / 24.0

    # ── 1. Находим все переходы накшатр ──────────────────
    use_topo = USE_SWISSEPH and (lat != 0.0 or lon != 0.0)
    _nk  = lambda jd: nk_idx(jd,   lat, lon) if use_topo else nk_idx(jd)
    _pd  = lambda jd: pada_idx(jd,  lat, lon) if use_topo else pada_idx(jd)
    _sid = lambda jd: moon_sid(jd, topo=use_topo, lat=lat, lon=lon)

    nk_transitions = []
    jd_cur = jd_s; prev = _nk(jd_cur)
    while jd_cur <= jd_e:
        jd_nx = jd_cur + step
        cur   = _nk(jd_nx)
        if cur != prev:
            nk_transitions.append(_bisect(jd_cur, jd_nx, _nk, prev, prec_sec))
            prev = cur
        jd_cur = jd_nx

    all_jd = [jd_s] + nk_transitions + [jd_e]

    result = []
    for i in range(len(all_jd) - 1):
        ns, ne = all_jd[i], all_jd[i+1]
        idx  = _nk(ns)
        nk   = NAKSHATRAS[idx]
        ms   = _sid(ns)
        me   = _sid(ne)
        dur  = (ne - ns) * 24

        # ── 2. Находим переходы пад внутри этой накшатры ─
        pada_transitions = []
        jd_cur = ns; pprev = _pd(jd_cur)
        while jd_cur <= ne:
            jd_nx = min(jd_cur + step, ne)
            pcur  = _pd(jd_nx)
            if pcur != pprev and jd_nx < ne:
                pada_transitions.append(_bisect(jd_cur, jd_nx, _pd, pprev, prec_sec))
                pprev = pcur
            if jd_nx >= ne:
                break
            jd_cur = jd_nx

        pada_jd = [ns] + pada_transitions + [ne]

        padas = []
        for j in range(len(pada_jd) - 1):
            ps, pe = pada_jd[j], pada_jd[j+1]
            p_ms   = _sid(ps)
            p_me   = _sid(pe)
            padas.append({
                "pada":       _pd(ps) + 1,
                "jd_start":   ps, "jd_end":   pe,
                "dt_start":   jd_to_local(ps, tz),
                "dt_end":     jd_to_local(pe, tz),
                "moon_start": p_ms,
                "moon_end":   p_me,
                "duration_h": (pe - ps) * 24,
                "boundary":   boundary_flag(p_ms),
            })

        result.append({
            "nk_num":    nk["num"],
            "name":      nk["name"],
            "ru":        nk["ru"],
            "lord":      nk["lord"],
            "gana":      nk["gana"],
            "jd_start":  ns, "jd_end":  ne,
            "dt_start":  jd_to_local(ns, tz),
            "dt_end":    jd_to_local(ne, tz),
            "duration_h": dur,
            "moon_start": ms,
            "moon_end":   me,
            "topo":       use_topo,
            "padas":      padas,
        })

    return result

# ═══════════════════════════════════════════════════════════
#  ВЫВОД
# ═══════════════════════════════════════════════════════════

def _header(date_start, date_end, tz, lat, lon, title, W):
    tz_str   = f"UTC{'+' if tz >= 0 else ''}{tz:g}"
    topo_str = "топоцентр" if USE_SWISSEPH else "геоцентр"
    print("\n" + "═" * W)
    print(f"  {title}")
    print("═" * W)
    print(f"  Период  : {date_start.strftime('%d.%m.%Y')} — {date_end.strftime('%d.%m.%Y')}")
    print(f"  Часовой : {tz_str}  |  lat {lat}°  lon {lon}°")
    print(f"  Метод   : {_EPH_NOTE}")
    print(f"  Позиция : {topo_str}  |  Аянамша: Лахири  |  Точность: ±1 сек")


def print_calendar_compact(entries: list[dict], date_start: date, date_end: date,
                            tz: float, lat: float, lon: float):
    """
    Краткий режим: только накшатры — дата начала/конца, длительность, владелец.
    Пады не выводятся.
    """
    W = 72
    _header(date_start, date_end, tz, lat, lon, "КАЛЕНДАРЬ НАКШАТР ЛУНЫ", W)
    print()
    print(f"  {'Начало':<22}{'Конец':<22}{'Накшатра':<22}{'Длит.':<10}Владелец")
    print("  " + "─" * (W - 2))

    prev_day = None
    for e in entries:
        day_s = e["dt_start"].strftime("%d.%m.%Y")
        if day_s != prev_day:
            if prev_day is not None:
                print()
            print(f"  ── {day_s}")
            prev_day = day_s

        ref  = e["dt_start"].date()
        ts   = e["dt_start"].strftime("%d.%m.%Y %H:%M:%S")
        same = e["dt_end"].date() == ref
        te   = e["dt_end"].strftime("%H:%M:%S") if same \
               else e["dt_end"].strftime("%d.%m.%Y %H:%M:%S")

        nk_str = f"#{e['nk_num']:02d} {e['ru']}"
        dur    = fmt_duration(e["duration_h"])
        print(f"  {ts:<22}{te:<22}{nk_str:<22}{dur:<10}{e['lord']}")

    total_days = (date_end - date_start).days + 1
    print()
    print(f"  {'─' * (W - 4)}")
    print(f"  Итого накшатр: {len(entries)}  |  Дней в периоде: {total_days}")
    print("═" * W + "\n")


def print_calendar(entries: list[dict], date_start: date, date_end: date,
                   tz: float, lat: float, lon: float):
    """
    Расширенный режим: накшатры + пады с временем и позицией Луны.
    """
    W = 68
    _header(date_start, date_end, tz, lat, lon, "КАЛЕНДАРЬ НАКШАТР ЛУНЫ — расширенный", W)
    print()

    prev_day = None
    for e in entries:
        day_s = e["dt_start"].strftime("%d.%m.%Y")
        if day_s != prev_day:
            if prev_day is not None:
                print()
            print(f"  ┄{'┄' * (W - 4)}┄")
            print(f"  {day_s}")
            prev_day = day_s

        ts, te = fmt_range(e["dt_start"], e["dt_end"])
        dur    = fmt_duration(e["duration_h"])
        print()
        print(f"  ◈  #{e['nk_num']:02d}  {e['name']}  /  {e['ru']}")
        print(f"     {e['lord']}  ·  {e['gana']}")
        print(f"     {ts}  →  {te}   ({dur})")
        print(f"     ☽ {dms(e['moon_start'])}  →  {dms(e['moon_end'])}")
        print()

        for p in e["padas"]:
            ps_same = p["dt_start"].date() == e["dt_start"].date()
            pe_same = p["dt_end"].date()   == p["dt_start"].date()
            p_s = p["dt_start"].strftime("%H:%M:%S") if ps_same \
                  else p["dt_start"].strftime("%d.%m %H:%M:%S")
            p_e = p["dt_end"].strftime("%H:%M:%S") if pe_same \
                  else p["dt_end"].strftime("%d.%m %H:%M:%S")
            pdur = fmt_duration(p["duration_h"])

            print(f"     пада {p['pada']}   {p_s}  →  {p_e}   ({pdur})")
            print(f"            ☽ {dms(p['moon_start'])}  →  {dms(p['moon_end'])}")

    print()
    total_days = (date_end - date_start).days + 1
    print(f"  {'─' * (W - 4)}")
    print(f"  Итого накшатр: {len(entries)}  |  Дней в периоде: {total_days}")
    print("═" * W + "\n")


# ═══════════════════════════════════════════════════════════
#  ИНТЕРАКТИВНЫЙ ВВОД
# ═══════════════════════════════════════════════════════════

def ask(prompt, cast, err):
    while True:
        try:
            return cast(input(prompt).strip())
        except Exception:
            print(f"  Ошибка: {err}")

def parse_date(s: str) -> date:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Неверный формат даты: {s}")

def get_input():
    print("\n  Календарь накшатр Луны")
    print("  " + "─" * 44)
    print("  Форматы даты: ДД.ММ.ГГГГ  /  ГГГГ-ММ-ДД")
    print()
    d_s  = ask("  Начало периода: ", parse_date, "пример: 01.01.2026")
    d_e  = ask("  Конец периода:  ", parse_date, "пример: 15.01.2026")
    tz   = ask("  Часовой пояс UTC+?: ", float,  "например: 3 или 5.5")
    lat  = ask("  Широта:  ", float, "например: 55.75")
    lon  = ask("  Долгота: ", float, "например: 37.62")
    mode = ask("  Режим [1=краткий, 2=расширенный]: ",
               lambda s: int(s) if s in ("1", "2") else (_ for _ in ()).throw(ValueError()),
               "введите 1 или 2")
    return d_s, d_e, tz, lat, lon, mode

# ═══════════════════════════════════════════════════════════
#  ПРИМЕРЫ
# ═══════════════════════════════════════════════════════════

EXAMPLES = [
    {
        "name":  "Москва, 14-21 марта 2026",
        "start": date(2026, 3, 14), "end": date(2026, 3, 17),
        "tz": 3.0, "lat": 55.75, "lon": 37.62,
    },
    {
        "name":  "Ставрополь, 10-14 июля 1990",
        "start": date(1990, 7, 10), "end": date(1990, 7, 14),
        "tz": 4.0, "lat": 45.043317, "lon": 41.969110,
    },
]

# ═══════════════════════════════════════════════════════════
#  ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "--examples":
            for ex in EXAMPLES:
                print(f"\n  Пример: {ex['name']}")
                entries = calc_calendar(ex["start"], ex["end"], ex["tz"], ex["lat"], ex["lon"])
                print_calendar_compact(entries, ex["start"], ex["end"], ex["tz"], ex["lat"], ex["lon"])
                print_calendar(entries, ex["start"], ex["end"], ex["tz"], ex["lat"], ex["lon"])

        elif cmd == "--period" and len(sys.argv) >= 7:
            d_s  = parse_date(sys.argv[2])
            d_e  = parse_date(sys.argv[3])
            tz   = float(sys.argv[4])
            lat  = float(sys.argv[5])
            lon  = float(sys.argv[6])
            mode = int(sys.argv[7]) if len(sys.argv) > 7 else 1
            entries = calc_calendar(d_s, d_e, tz, lat, lon)
            if mode == 2:
                print_calendar(entries, d_s, d_e, tz, lat, lon)
            else:
                print_calendar_compact(entries, d_s, d_e, tz, lat, lon)

        else:
            print("Использование:")
            print("  python nakshatra_calendar.py")
            print("  python nakshatra_calendar.py --examples")
            print("  python nakshatra_calendar.py --period ГГГГ-ММ-ДД ГГГГ-ММ-ДД TZ LAT LON [1|2]")
            print("    1 = краткий (по умолчанию)   2 = расширенный с падами")
    else:
        try:
            d_s, d_e, tz, lat, lon, mode = get_input()
            print("\n  Вычисляю...")
            entries = calc_calendar(d_s, d_e, tz, lat, lon)
            if mode == 2:
                print_calendar(entries, d_s, d_e, tz, lat, lon)
            else:
                print_calendar_compact(entries, d_s, d_e, tz, lat, lon)
        except KeyboardInterrupt:
            print("\n\nВыход.")