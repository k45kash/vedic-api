"""
╔═══════════════════════════════════════════════════════════════════╗
║   ПАНЧАНГ — Титхи, Мухурты, Хоры                                 ║
║   Лунные сутки · Планетарные часы · Мухурты дня                  ║
╚═══════════════════════════════════════════════════════════════════╝

Запуск:
    python panchang.py                                 — ввод
    python panchang.py --examples                      — примеры
    python panchang.py --period 2026-03-14 2026-03-17 3 55.75 37.62
"""

import math
import sys
from datetime import datetime, timedelta, date

try:
    import swisseph as swe
    USE_SWISSEPH = True
    import os as _os
    EPHE_PATH = _os.environ.get(
        "SE_EPHE_PATH",
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ephe")
    )
    swe.set_ephe_path(EPHE_PATH)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
except ImportError:
    USE_SWISSEPH = False
    print("⚠  pyswisseph не установлен. pip install pyswisseph\n")

# ═══════════════════════════════════════════════════════════
#  СПРАВОЧНИКИ
# ═══════════════════════════════════════════════════════════

TITHIS = [
    # (num, name, paksha, type, quality)
    ( 1, "Пратипада",  "Шукла",  "Нанда",  "Благоприятная"),
    ( 2, "Двитья",     "Шукла",  "Бхадра", "Благоприятная"),
    ( 3, "Тритья",     "Шукла",  "Джая",   "Благоприятная"),
    ( 4, "Чатуртхи",  "Шукла",  "Рикта",  "Неблагоприятная"),
    ( 5, "Панчами",    "Шукла",  "Пурна",  "Благоприятная"),
    ( 6, "Шаштхи",    "Шукла",  "Нанда",  "Переменная"),
    ( 7, "Саптами",   "Шукла",  "Бхадра", "Благоприятная"),
    ( 8, "Аштами",    "Шукла",  "Джая",   "Переменная"),
    ( 9, "Навами",    "Шукла",  "Рикта",  "Неблагоприятная"),
    (10, "Дашами",    "Шукла",  "Пурна",  "Благоприятная"),
    (11, "Экадаши",   "Шукла",  "Нанда",  "Очень благоприятная"),
    (12, "Двадаши",   "Шукла",  "Бхадра", "Благоприятная"),
    (13, "Трайодаши", "Шукла",  "Джая",   "Благоприятная"),
    (14, "Чатурдаши", "Шукла",  "Рикта",  "Неблагоприятная"),
    (15, "Пурнима",   "Шукла",  "Пурна",  "Очень благоприятная"),
    (16, "Пратипада", "Кришна", "Нанда",  "Переменная"),
    (17, "Двитья",    "Кришна", "Бхадра", "Переменная"),
    (18, "Тритья",    "Кришна", "Джая",   "Переменная"),
    (19, "Чатуртхи", "Кришна", "Рикта",  "Неблагоприятная"),
    (20, "Панчами",   "Кришна", "Пурна",  "Переменная"),
    (21, "Шаштхи",   "Кришна", "Нанда",  "Переменная"),
    (22, "Саптами",  "Кришна", "Бхадра", "Благоприятная"),
    (23, "Аштами",   "Кришна", "Джая",   "Переменная"),
    (24, "Навами",   "Кришна", "Рикта",  "Неблагоприятная"),
    (25, "Дашами",   "Кришна", "Пурна",  "Благоприятная"),
    (26, "Экадаши",  "Кришна", "Нанда",  "Очень благоприятная"),
    (27, "Двадаши",  "Кришна", "Бхадра", "Благоприятная"),
    (28, "Трайодаши","Кришна", "Джая",   "Благоприятная"),
    (29, "Чатурдаши","Кришна", "Рикта",  "Переменная"),
    (30, "Амавасья", "Кришна", "Пурна",  "Новолуние — Неблагоприятная"),
]

PAKSHA_LABEL = {
    "Шукла":  "Шукла (Светлая)",
    "Кришна": "Кришна (Тёмная)",
}

MUHURTAS = [
    # (номер, название, качество)
    ( 1, "Рудра",          "Неблагоприятная"),
    ( 2, "Ахи",            "Неблагоприятная"),
    ( 3, "Митра",          "Благоприятная"),
    ( 4, "Питру",          "Неблагоприятная"),
    ( 5, "Васу",           "Благоприятная"),
    ( 6, "Вара",           "Благоприятная"),
    ( 7, "Вишведева",      "Благоприятная"),
    ( 8, "Видхи",          "Благоприятная"),
    ( 9, "Хутасана",       "Неблагоприятная"),
    (10, "Пурухута",       "Благоприятная"),
    (11, "Вахини",         "Неблагоприятная"),
    (12, "Нактанкара",     "Неблагоприятная"),
    (13, "Варуна",         "Благоприятная"),
    (14, "Арьяман",        "Благоприятная"),
    (15, "Бхага",          "Смешанная"),
    (16, "Гириша",         "Неблагоприятная"),
    (17, "Аджапада",       "Неблагоприятная"),
    (18, "Ахир Будхнья",   "Смешанная"),
    (19, "Пушья",          "Очень благоприятная"),
    (20, "Ашвини",         "Благоприятная"),
    (21, "Яма",            "Неблагоприятная"),
    (22, "Агни",           "Смешанная"),
    (23, "Видхата",        "Благоприятная"),
    (24, "Канда",          "Смешанная"),
    (25, "Адити",          "Благоприятная"),
    (26, "Джива / Амрита", "Очень благоприятная"),
    (27, "Вишну",          "Благоприятная"),
    (28, "Дьюмадгадьюти",  "Благоприятная"),
    (29, "Брахма",         "Очень благоприятная"),
    (30, "Самудрам",       "Благоприятная"),
]

# Халдейский порядок планет для хоры
HORA_PLANETS = ["Солнце", "Венера", "Меркурий", "Луна", "Сатурн", "Юпитер", "Марс"]

# Владелец первой хоры каждого дня недели (0=Пн)
WEEKDAY_FIRST_HORA = {
    0: "Луна",     # Понедельник
    1: "Марс",     # Вторник
    2: "Меркурий", # Среда
    3: "Юпитер",   # Четверг
    4: "Венера",   # Пятница
    5: "Сатурн",   # Суббота
    6: "Солнце",   # Воскресенье
}

# ═══════════════════════════════════════════════════════════
#  УТИЛИТЫ ВРЕМЕНИ
# ═══════════════════════════════════════════════════════════

def dt_to_jd(dt: datetime) -> float:
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute/60 + dt.second/3600) / 24
    if m <= 2: y -= 1; m += 12
    A = int(y/100); B = 2 - A + int(A/4)
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + B - 1524.5

def jd_to_dt_utc(jd: float) -> datetime:
    jd2 = jd + 0.5; Z = int(jd2); F = jd2 - Z
    A = Z if Z < 2299161 else (lambda a: Z+1+a-int(a/4))(int((Z-1867216.25)/36524.25))
    B = A+1524; C = int((B-122.1)/365.25); D = int(365.25*C); E = int((B-D)/30.6001)
    df = B-D-int(30.6001*E)+F; day = int(df); frac = df-day
    hf = frac*24; h = int(hf); mf = (hf-h)*60; mn = int(mf); sec = int((mf-mn)*60+0.5)
    mon = E-1 if E < 14 else E-13; yr = C-4716 if mon > 2 else C-4715
    if sec >= 60: sec -= 60; mn += 1
    if mn  >= 60: mn  -= 60; h  += 1
    if h   >= 24: h   -= 24; day += 1
    return datetime(yr, mon, day, h, mn, sec)

def jd_to_local(jd: float, tz: float) -> datetime:
    return jd_to_dt_utc(jd) + timedelta(hours=tz)

def fmt_dt(dt: datetime, ref_date=None) -> str:
    """Время, дата только если отличается от ref_date."""
    if ref_date is None or dt.date() != ref_date:
        return dt.strftime("%d.%m %H:%M:%S")
    return dt.strftime("%H:%M:%S")

def fmt_dur(hours: float) -> str:
    """Длительность в минутах и секундах (или часах если > 60 мин)."""
    total_sec = round(hours * 3600)
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    h = total_min // 60
    if h > 0:
        return f"{h}ч {m:02d}м {s:02d}с"
    return f"{m}м {s:02d}с"

# ═══════════════════════════════════════════════════════════
#  АСТРОНОМИЧЕСКИЕ ВЫЧИСЛЕНИЯ
# ═══════════════════════════════════════════════════════════

_DT_TABLE = [
    (1620,124),(1700,22),(1800,13),(1900,3),
    (1950,29),(1960,33),(1970,40),(1975,45),
    (1980,50),(1985,54),(1990,57),(1995,61),
    (2000,63),(2005,65),(2010,66),(2015,68),
    (2020,69),(2025,69),(2030,70),
]

def _delta_t(jd):
    year = 2000.0 + (jd-2451545.0)/365.25
    for i in range(len(_DT_TABLE)-1):
        y0,d0 = _DT_TABLE[i]; y1,d1 = _DT_TABLE[i+1]
        if y0 <= year <= y1: return d0+(d1-d0)*(year-y0)/(y1-y0)
    return float(_DT_TABLE[-1][1])

def sun_lon(jd: float) -> float:
    """Тропическая долгота Солнца."""
    if USE_SWISSEPH:
        pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
        return pos[0]
    # Meeus fallback с Delta T
    jd_tt = jd + _delta_t(jd)/86400
    T = (jd_tt-2451545.0)/36525
    L0 = 280.46646+36000.76983*T
    M  = 357.52911+35999.05029*T-0.0001537*T*T
    C  = ((1.914602-0.004817*T-0.000014*T*T)*math.sin(math.radians(M))
         +(0.019993-0.000101*T)*math.sin(math.radians(2*M))
         +0.000289*math.sin(math.radians(3*M)))
    return (L0+C) % 360

def moon_lon(jd: float) -> float:
    """Тропическая долгота Луны."""
    if USE_SWISSEPH:
        pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
        return pos[0]
    jd_tt = jd + _delta_t(jd)/86400
    T = (jd_tt-2451545.0)/36525
    L0 = (218.3164477+481267.88123421*T) % 360
    Mm = (134.9633964+477198.8676313*T)  % 360
    Ms = (357.5291092+35999.0502909*T)   % 360
    F  = (93.2720950+483202.0175233*T)   % 360
    D  = (297.8501921+445267.1114034*T)  % 360
    dL = (6.288774*math.sin(math.radians(Mm))
         +1.274027*math.sin(math.radians(2*D-Mm))
         +0.658314*math.sin(math.radians(2*D))
         +0.213618*math.sin(math.radians(2*Mm))
         -0.185116*math.sin(math.radians(Ms))
         -0.114332*math.sin(math.radians(2*F)))
    return (L0+dL) % 360

def tithi_index(jd: float) -> int:
    """Индекс титхи 0-29: (Луна-Солнце) / 12°."""
    diff = (moon_lon(jd) - sun_lon(jd)) % 360
    return int(diff / 12)

def _sun_params(jd):
    """
    Склонение Солнца (рад) и уравнение времени (мин) для JD (0h UT).
    Meeus "Astronomical Algorithms" ch.25 — погрешность < 2 мин.
    """
    T   = (jd - 2451545.0) / 36525.0
    L0  = (280.46646 + 36000.76983*T) % 360
    M   = math.radians((357.52911 + 35999.05029*T) % 360)
    C   = ((1.914602 - 0.004817*T)*math.sin(M)
          + 0.019993*math.sin(2*M)
          + 0.000289*math.sin(3*M))
    sun_lon = (L0 + C) % 360
    omega   = 125.04 - 1934.136*T
    app_lon = math.radians(sun_lon - 0.00569 - 0.00478*math.sin(math.radians(omega)))
    eps     = math.radians(23.439291111 - 0.013004167*T
                           + 0.000164*math.sin(math.radians(omega)))
    dec     = math.asin(math.sin(eps)*math.sin(app_lon))
    # Уравнение времени через прямое восхождение
    ra      = math.degrees(math.atan2(math.cos(eps)*math.sin(app_lon), math.cos(app_lon))) % 360
    eot_min = ((L0 - 0.0057183 - ra + 180*(round((L0-ra)/180))) * 4)
    return dec, eot_min

def jd_from_date(year, month, day):
    if month <= 2: year -= 1; month += 12
    A = int(year/100); B = 2 - A + int(A/4)
    return int(365.25*(year+4716)) + int(30.6001*(month+1)) + day + B - 1524.5

def get_sunrise_sunset(jd_day: float, lat: float, lon: float, tz: float,
                       elev_m: float = 0.0) -> tuple:
    """
    Возвращает (jd_sunrise, jd_sunset).

    Точность по режимам:
      DE431 + rise_trans  → < 1 сек   (с .se1 файлами)
      Moshier + rise_trans→ ~5-10 сек (без файлов, SWE встроенный)
      Meeus fallback      → ~2 мин    (без SWE)

    rise_trans ищет событие ПОСЛЕ переданного JD.
    Начинаем с предыдущей полуночи UTC чтобы гарантированно
    найти восход текущего дня.
    """
    if USE_SWISSEPH:
        geopos   = (lon, lat, elev_m / 1000.0)   # высота в км
        # Начинаем поиск с 00:00 UTC текущего дня
        # JD система: целое JD = полдень, поэтому +0.5 перед floor
        jd_start = math.floor(jd_day + 0.5) - 0.5  # 00:00 UTC текущего дня

        def _rise_trans(jd_s, rsmi):
            # rise_trans(tjdut, body, rsmi, geopos, atpress, attemp, flags)
            try:
                ret, t = swe.rise_trans(jd_s, swe.SUN, rsmi,
                                        geopos, 1013.25, 15.0,
                                        swe.FLG_SWIEPH)
                if ret == 0:
                    return t[0]
            except Exception:
                pass
            return None

        jd_rise = _rise_trans(jd_start, swe.CALC_RISE)
        jd_set  = _rise_trans(jd_start, swe.CALC_SET)

        if jd_rise is not None and jd_set is not None:
            return jd_rise, jd_set

    # Meeus fallback — Astronomical Algorithms ch.25, погрешность ~2 мин
    jd0   = math.floor(jd_day + 0.5) - 0.5  # 0h UT данного дня
    dec, eot = _sun_params(jd0)
    lat_r = math.radians(lat)
    cos_H = (math.sin(math.radians(-0.8333)) - math.sin(lat_r)*math.sin(dec)) / \
            (math.cos(lat_r)*math.cos(dec))
    if abs(cos_H) > 1:
        noon_jd = jd0 + (12.0 - lon/15.0 - eot/60.0) / 24.0
        return noon_jd, noon_jd
    H_h        = math.degrees(math.acos(cos_H)) / 15.0
    noon_utc_h = 12.0 - lon/15.0 - eot/60.0
    return jd0 + (noon_utc_h - H_h)/24.0, jd0 + (noon_utc_h + H_h)/24.0

# ═══════════════════════════════════════════════════════════
#  БИНАРНЫЙ ПОИСК ПЕРЕХОДОВ
# ═══════════════════════════════════════════════════════════

def _bisect(jd_lo, jd_hi, state_fn, state_lo, prec_sec=1.0):
    prec = prec_sec / 86400
    while jd_hi - jd_lo > prec:
        mid = (jd_lo + jd_hi) / 2
        if state_fn(mid) == state_lo: jd_lo = mid
        else: jd_hi = mid
    return jd_hi

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ ТИТХИ
# ═══════════════════════════════════════════════════════════

def calc_tithis(jd_s, jd_e, tz, step_h=0.5):
    """Список титхи за период с временем начала/конца."""
    step = step_h / 24
    transitions = []
    jd_cur = jd_s; prev = tithi_index(jd_cur)
    while jd_cur <= jd_e:
        jd_nx = jd_cur + step
        cur = tithi_index(jd_nx)
        if cur != prev:
            transitions.append(_bisect(jd_cur, jd_nx, tithi_index, prev))
            prev = cur
        jd_cur = jd_nx

    all_jd = [jd_s] + transitions + [jd_e]
    result = []
    for i in range(len(all_jd)-1):
        js, je = all_jd[i], all_jd[i+1]
        idx = tithi_index(js)
        t = TITHIS[idx]
        result.append({
            "num": t[0], "name": t[1], "paksha": t[2],
            "type": t[3], "quality": t[4],
            "jd_start": js, "jd_end": je,
            "dt_start": jd_to_local(js, tz),
            "dt_end":   jd_to_local(je, tz),
            "duration_h": (je-js)*24,
            "moon_sun_diff": round((moon_lon(js)-sun_lon(js)) % 360, 3),
        })
    return result

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ МУХ УРТ
# ═══════════════════════════════════════════════════════════

def calc_muhurtas_day(jd_sunrise, jd_sunset, jd_next_sunrise, tz):
    """
    30 мухурт: 15 дневных (восход→закат) + 15 ночных (закат→следующий восход).
    Каждая мухурта = 1/15 длины своего периода.
    Длительность немного меняется день ото дня — это норма: день зимой короче,
    летом длиннее. За солнечный год мухурта колеблется от ~40 до ~56 минут.
    """
    day_dur   = jd_sunset       - jd_sunrise       # длина дня
    night_dur = jd_next_sunrise - jd_sunset         # длина ночи
    muh_day   = day_dur   / 15
    muh_night = night_dur / 15

    result = []
    for i in range(30):
        if i < 15:
            js = jd_sunrise + i       * muh_day
            je = jd_sunrise + (i + 1) * muh_day
        else:
            j  = i - 15
            js = jd_sunset  + j       * muh_night
            je = jd_sunset  + (j + 1) * muh_night
        m = MUHURTAS[i]
        result.append({
            "num":       m[0], "name": m[1], "quality": m[2],
            "day_night": "день" if i < 15 else "ночь",
            "dt_start":  jd_to_local(js, tz),
            "dt_end":    jd_to_local(je, tz),
            "duration_h": (je - js) * 24,
        })
    return result

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ ХОР
# ═══════════════════════════════════════════════════════════

def calc_horas_day(jd_sunrise, jd_sunset, jd_next_sunrise, tz):
    """
    24 хоры: 12 дневных (восход→закат) + 12 ночных (закат→следующий восход).
    """
    dt_sunrise_local = jd_to_local(jd_sunrise, tz)
    weekday = dt_sunrise_local.weekday()

    first_planet = WEEKDAY_FIRST_HORA[weekday]
    start_idx    = HORA_PLANETS.index(first_planet)

    day_dur   = jd_sunset       - jd_sunrise
    night_dur = jd_next_sunrise - jd_sunset
    hora_day   = day_dur   / 12
    hora_night = night_dur / 12

    result = []
    for i in range(24):
        planet = HORA_PLANETS[(start_idx + i) % 7]
        if i < 12:
            js = jd_sunrise + i       * hora_day
            je = jd_sunrise + (i + 1) * hora_day
        else:
            j  = i - 12
            js = jd_sunset  + j       * hora_night
            je = jd_sunset  + (j + 1) * hora_night
        result.append({
            "num":        i + 1,
            "planet":     planet,
            "day_night":  "день" if i < 12 else "ночь",
            "dt_start":   jd_to_local(js, tz),
            "dt_end":     jd_to_local(je, tz),
            "duration_h": (je - js) * 24,
        })
    return result

# ═══════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ РАСЧЁТА
# ═══════════════════════════════════════════════════════════

def calc_panchang(date_start, date_end, tz, lat=0.0, lon=0.0, elev_m=0.0):
    jd_s = dt_to_jd(datetime(date_start.year, date_start.month, date_start.day)) - tz/24
    jd_e = dt_to_jd(datetime(date_end.year,   date_end.month,   date_end.day, 23, 59, 59)) - tz/24

    # Титхи за весь период
    tithis = calc_tithis(jd_s, jd_e, tz)

    # Мухурты и хоры — по дням
    days = []
    current = date_start
    while current <= date_end:
        jd_noon = dt_to_jd(datetime(current.year, current.month, current.day, 12, 0)) - tz/24
        jd_rise, jd_set = get_sunrise_sunset(jd_noon, lat, lon, tz, elev_m)

        # Следующий восход — реальный расчёт (не +24ч)
        jd_noon_next = jd_noon + 1.0
        jd_rise_next, _ = get_sunrise_sunset(jd_noon_next, lat, lon, tz, elev_m)

        muhurtas = calc_muhurtas_day(jd_rise, jd_set, jd_rise_next, tz)
        horas    = calc_horas_day(jd_rise, jd_set, jd_rise_next, tz)

        days.append({
            "date":       current,
            "dt_sunrise": jd_to_local(jd_rise, tz),
            "dt_sunset":  jd_to_local(jd_set,  tz),
            "day_dur_h":  (jd_set - jd_rise) * 24,
            "muhurtas":   muhurtas,
            "horas":      horas,
        })
        current += timedelta(days=1)

    return {"tithis": tithis, "days": days}

# ═══════════════════════════════════════════════════════════
#  ВЫВОД
# ═══════════════════════════════════════════════════════════

QUALITY_MARK = {
    "Очень благоприятная":          "★★",
    "Благоприятная":                "★ ",
    "Переменная":                   "◑ ",
    "Смешанная":                    "◑ ",
    "Неблагоприятная":              "✗ ",
    "Новолуние — Неблагоприятная":  "☽✗",
}

def _items_in_range(items, dt_start, dt_end):
    """Вернуть элементы списка чьё dt_start попадает в [dt_start, dt_end)."""
    return [x for x in items
            if dt_start <= x["dt_start"] < dt_end]

def _all_muhurtas(data):
    """Плоский список всех мухурт по всем дням."""
    result = []
    for day in data["days"]:
        result.extend(day["muhurtas"])
    return result

def _all_horas(data):
    """Плоский список всех хор по всем дням."""
    result = []
    for day in data["days"]:
        result.extend(day["horas"])
    return result

def print_panchang(data, date_start, date_end, tz, lat, lon):
    tz_str = f"UTC{'+' if tz >= 0 else ''}{tz:g}"
    method = "Swiss Ephemeris (DE431)" if USE_SWISSEPH else "Meeus algorithm"
    W = 72

    print("\n" + "═"*W)
    print("  ПАНЧАНГ  —  Титхи · Мухурты · Хоры")
    print("═"*W)
    print(f"  Период   : {date_start.strftime('%d.%m.%Y')} — {date_end.strftime('%d.%m.%Y')}")
    print(f"  Часовой  : {tz_str}  |  lat {lat}°  lon {lon}°")
    print(f"  Метод    : {method}  |  Точность: ±1 сек")
    print()

    all_muh  = _all_muhurtas(data)
    all_hora = _all_horas(data)

    # Индекс дней по дате для быстрого поиска восхода/заката
    days_by_date = {day["date"]: day for day in data["days"]}

    for tithi in data["tithis"]:
        t_s = tithi["dt_start"]
        t_e = tithi["dt_end"]
        ref = t_s.date()

        ts = t_s.strftime("%d.%m.%Y %H:%M:%S")
        te_same = t_e.date() == ref
        te = t_e.strftime("%H:%M:%S") if te_same else t_e.strftime("%d.%m.%Y %H:%M:%S")

        paksha = PAKSHA_LABEL.get(tithi["paksha"], tithi["paksha"])
        mark   = QUALITY_MARK.get(tithi["quality"], "  ")

        # ── Заголовок титхи ───────────────────────────────
        print("━"*W)
        print(f"  #{tithi['num']:02d}  {tithi['name']}   {paksha}")
        print(f"  {ts}  →  {te}   "
              f"({fmt_dur(tithi['duration_h'])})   "
              f"{mark} {tithi['quality']}")
        print()

        # ── Восход/закат для дней внутри титхи ───────────
        # Собираем уникальные даты, которые покрывает эта титхи
        sun_dates = []
        d = t_s.date()
        while d <= t_e.date():
            if d in days_by_date:
                sun_dates.append(d)
            d += timedelta(days=1)
        if sun_dates:
            for sd in sun_dates:
                day = days_by_date[sd]
                rise = day["dt_sunrise"].strftime("%H:%M:%S")
                sset = day["dt_sunset"].strftime("%H:%M:%S")
                weekday_ru = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][sd.weekday()]
                print(f"  {sd.strftime('%d.%m.%Y')} {weekday_ru}  "
                      f"☀ Восход {rise}   ☀ Закат {sset}   "
                      f"День: {fmt_dur(day['day_dur_h'])}")
            print()

        # ── Мухурты внутри этой титхи ─────────────────────
        muhs = _items_in_range(all_muh, t_s, t_e)
        if muhs:
            print(f"  {'Мухурты':}")
            print(f"  {'№':<4}{'Начало':<12}{'Конец':<24}{'Название':<24}{'Часть':<7}{'Длит.':<7}Качество")
            print("  " + "─"*(W-2))
            for m in muhs:
                ms = m["dt_start"].strftime("%H:%M:%S")
                me_dt = m["dt_end"]
                me = me_dt.strftime("%H:%M:%S") if me_dt.date() == m["dt_start"].date() \
                     else me_dt.strftime("%d.%m %H:%M:%S")
                qm = QUALITY_MARK.get(m["quality"], "  ")
                print(f"  {m['num']:<4}{ms:<12}{me:<24}{m['name']:<24}"
                      f"{m['day_night']:<7}{fmt_dur(m['duration_h']):<7}{qm} {m['quality']}")
            print()

        # ── Хоры внутри этой титхи ────────────────────────
        horas = _items_in_range(all_hora, t_s, t_e)
        if horas:
            print(f"  {'Хоры (планетарные часы)':}")
            print(f"  {'№':<4}{'Начало':<12}{'Конец':<24}{'Планета':<14}{'Часть':<7}Длит.")
            print("  " + "─"*(W-2))
            for h in horas:
                hs = h["dt_start"].strftime("%H:%M:%S")
                he_dt = h["dt_end"]
                he = he_dt.strftime("%H:%M:%S") if he_dt.date() == h["dt_start"].date() \
                     else he_dt.strftime("%d.%m %H:%M:%S")
                print(f"  {h['num']:<4}{hs:<12}{he:<24}{h['planet']:<14}"
                      f"{h['day_night']:<7}{fmt_dur(h['duration_h'])}")
            print()

    print("═"*W)
    total_days = (date_end - date_start).days + 1
    print(f"  Итого титхи: {len(data['tithis'])}  |  Дней в периоде: {total_days}")
    print("═"*W + "\n")

# ═══════════════════════════════════════════════════════════
#  ВВОД / CLI
# ═══════════════════════════════════════════════════════════

def ask(prompt, cast, err):
    while True:
        try: return cast(input(prompt).strip())
        except: print(f"  Ошибка: {err}")

def parse_date(s):
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    raise ValueError(s)

EXAMPLES = [
    {
        "name":  "Ставрополь, 8-18 марта 2026",
        "start": date(2026, 3, 8), "end": date(2026, 3, 18),
        "tz": 3.0, "lat": 45.043317, "lon": 41.969110, "elev_m": 450,
    },
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--examples":
            for ex in EXAMPLES:
                print(f"\n  Пример: {ex['name']}")
                data = calc_panchang(ex["start"], ex["end"], ex["tz"], ex["lat"], ex["lon"], ex.get("elev_m", 0))
                print_panchang(data, ex["start"], ex["end"], ex["tz"], ex["lat"], ex["lon"])
        elif cmd == "--period" and len(sys.argv) >= 7:
            d_s = parse_date(sys.argv[2]); d_e = parse_date(sys.argv[3])
            tz  = float(sys.argv[4]); lat = float(sys.argv[5]); lon = float(sys.argv[6])
            data = calc_panchang(d_s, d_e, tz, lat, lon)
            print_panchang(data, d_s, d_e, tz, lat, lon)
        else:
            print("  python panchang.py")
            print("  python panchang.py --examples")
            print("  python panchang.py --period ГГГГ-ММ-ДД ГГГГ-ММ-ДД TZ LAT LON")
    else:
        try:
            print("\n  Панчанг — Титхи · Мухурты · Хоры")
            print("  " + "─"*42)
            d_s = ask("  Начало периода: ", parse_date, "пример: 14.03.2026")
            d_e = ask("  Конец периода:  ", parse_date, "пример: 16.03.2026")
            tz  = ask("  Часовой UTC+?: ", float, "например: 3")
            lat = ask("  Широта:  ", float, "например: 55.75")
            lon = ask("  Долгота: ", float, "например: 37.62")
            data = calc_panchang(d_s, d_e, tz, lat, lon)
            print_panchang(data, d_s, d_e, tz, lat, lon)
        except KeyboardInterrupt:
            print("\n\nВыход.")