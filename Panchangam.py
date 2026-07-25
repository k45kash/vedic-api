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
import os
from datetime import datetime, timedelta, date

import swisseph as swe

from utils import dt_to_jd, jd_to_local, _bisect

EPHE_PATH = os.environ.get(
    "SE_EPHE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
)
swe.set_ephe_path(EPHE_PATH)
swe.set_sid_mode(swe.SIDM_LAHIRI)

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

# ── НИТЬЯ-ЙОГИ ─────────────────────────────────────────────
# 27 йог по 13°20' от СУММЫ сидерических долгот Солнца и Луны.
# Порядок названий — Panchangam (Wikipedia):
#   https://en.wikipedia.org/wiki/Panchangam
#   «Yoga ... Apparent Moon plus Apparent Sun ... One Yoga = 13°20', 27 Yogas = 360°»
# Названия и качества синхронизированы с frontend-nuxt/content/panchanga.json
# (ключ "yoga"): ✦ → Очень благоприятная, ✓ → Благоприятная,
#                ~ → Смешанная,           ✗ → Неблагоприятная.
YOGAS = [
    # (num, name, quality)
    ( 1, "Вишкумбха", "Смешанная"),
    ( 2, "Прити",     "Благоприятная"),
    ( 3, "Аюшман",    "Благоприятная"),
    ( 4, "Саубхагья", "Благоприятная"),
    ( 5, "Шобхана",   "Благоприятная"),
    ( 6, "Атиганда",  "Неблагоприятная"),
    ( 7, "Сукарма",   "Благоприятная"),
    ( 8, "Дхрити",    "Смешанная"),
    ( 9, "Шула",      "Неблагоприятная"),
    (10, "Ганда",     "Неблагоприятная"),
    (11, "Вриддхи",   "Благоприятная"),
    (12, "Дхрува",    "Благоприятная"),
    (13, "Вьягхата",  "Неблагоприятная"),
    (14, "Харшана",   "Благоприятная"),
    (15, "Ваджра",    "Неблагоприятная"),
    (16, "Сиддхи",    "Благоприятная"),
    (17, "Вьятипата", "Неблагоприятная"),   # стоп-фактор: избегают целиком
    (18, "Варияна",   "Смешанная"),
    (19, "Паригха",   "Неблагоприятная"),
    (20, "Шива",      "Благоприятная"),
    (21, "Сиддха",    "Очень благоприятная"),
    (22, "Садхья",    "Благоприятная"),
    (23, "Шубха",     "Благоприятная"),
    (24, "Шукла",     "Благоприятная"),
    (25, "Брахма",    "Очень благоприятная"),
    (26, "Индра",     "Очень благоприятная"),
    (27, "Вайдхрити", "Неблагоприятная"),   # стоп-фактор: избегают целиком
]

# Номера йог-стоп-факторов (см. content/panchanga.json → yoga.note)
YOGA_STOP_NUMS = (17, 27)   # Вьятипата, Вайдхрити

# ── КАРАНЫ ─────────────────────────────────────────────────
# Карана = половина титхи (6° разницы Луна−Солнце). В лунном месяце 60 каран.
# Названия и качества — из frontend-nuxt/content/panchanga.json (ключ "karana").
KARANAS = [
    # (num, name, type, quality)
    ( 1, "Бава",           "Чара",   "Благоприятная"),
    ( 2, "Балава",         "Чара",   "Благоприятная"),
    ( 3, "Каулава",        "Чара",   "Благоприятная"),
    ( 4, "Тайтила",        "Чара",   "Благоприятная"),
    ( 5, "Гара",           "Чара",   "Смешанная"),
    ( 6, "Ваниджа",        "Чара",   "Смешанная"),
    ( 7, "Вишти (Бхадра)", "Чара",   "Неблагоприятная"),   # стоп-фактор Бхадра
    ( 8, "Шакуни",         "Стхира", "Смешанная"),
    ( 9, "Чатушпада",      "Стхира", "Смешанная"),
    (10, "Нага",           "Стхира", "Неблагоприятная"),
    (11, "Кимстугхна",     "Стхира", "Благоприятная"),
]

KARANA_TYPE_LABEL = {
    "Чара":   "Чара (подвижная)",
    "Стхира": "Стхира (неподвижная)",
}

# Индекс караны Вишти/Бхадра в KARANAS (0-based) — стоп-фактор для фронта
_KARANA_VISHTI = 6

# Раскладка 60 полутитх лунного месяца на 11 каран.
# Источники (сверено, совпадают дословно):
#   1) https://en.wikipedia.org/wiki/Karaṇa_(pañcāṅga)
#      «The fifty-six half tithi-s starting from Śukla pakṣa pratipad second half
#       to Kṛṣṇa pakṣa caturdasi first half are given the variable names Bava,
#       Bālava, Kaulava, Taitila, Gara, Vaṇij and Vṛṣṭi in a cyclical order,
#       repeated eight times.»
#      Фиксированные: Кришна чатурдаши 2-я половина — Шакуни;
#      Амавасья 1-я половина — Чатушпада; Амавасья 2-я половина — Нага;
#      Шукла пратипада 1-я половина — Кимстугхна.
#   2) https://astrobix.com/learn/99-calculation-of-a-panchanga.html
#      (та же последовательность, karana = 2*tithi−1 / 2*tithi)
#
# В 0-based индексе полутитхи k = int(((Луна−Солнце) mod 360) / 6):
#   k = 0        → Кимстугхна   (Шукла пратипада, 1-я половина)
#   k = 1..56    → Бава…Вишти циклом 8 раз ((k−1) mod 7)
#   k = 57       → Шакуни       (Кришна чатурдаши, 2-я половина)
#   k = 58       → Чатушпада    (Амавасья, 1-я половина)
#   k = 59       → Нага         (Амавасья, 2-я половина)

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

def sun_lon(jd: float) -> float:
    """Тропическая долгота Солнца."""
    pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
    return pos[0]


def moon_lon(jd: float) -> float:
    """Тропическая долгота Луны."""
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
    return pos[0]


def sun_lon_sid(jd: float) -> float:
    """Сидерическая (нираяна, Лахири) долгота Солнца."""
    pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return pos[0]


def moon_lon_sid(jd: float) -> float:
    """Сидерическая (нираяна, Лахири) долгота Луны."""
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return pos[0]


def tithi_index(jd: float) -> int:
    """Индекс титхи 0-29: (Луна-Солнце) / 12°."""
    diff = (moon_lon(jd) - sun_lon(jd)) % 360
    return int(diff / 12)


def yoga_index(jd: float) -> int:
    """
    Индекс нитья-йоги 0-26: (Солнце + Луна) / 13°20'.

    Долготы — СИДЕРИЧЕСКИЕ: в отличие от титхи/караны (разность, где айанамша
    сокращается) сумма зависит от айанамши, поэтому тропические долготы дали бы
    сдвиг на 2×айанамша (~48°, то есть ~3.6 йоги).
    """
    total = (sun_lon_sid(jd) + moon_lon_sid(jd)) % 360
    return int(total / (40.0 / 3.0))       # 13°20' = 40/3°


def karana_index(jd: float) -> int:
    """Индекс полутитхи (караны) 0-59 в лунном месяце: (Луна-Солнце) / 6°."""
    diff = (moon_lon(jd) - sun_lon(jd)) % 360
    return int(diff / 6)


def karana_num_for_half(k: int) -> int:
    """
    Номер караны (1-11 в KARANAS) для 0-based индекса полутитхи k (0-59).
    Раскладка — см. комментарий у таблицы KARANAS.
    """
    if k == 0:
        return 11          # Кимстугхна
    if k <= 56:
        return (k - 1) % 7 + 1     # Бава … Вишти, 8 циклов
    return {57: 8, 58: 9, 59: 10}[k]   # Шакуни, Чатушпада, Нага


def _sun_params(jd: float):
    """
    Склонение Солнца (рад) и уравнение времени (мин) для JD (0h UT).
    Meeus "Astronomical Algorithms" ch.25 — погрешность < 2 мин.
    Используется только как fallback для полярных широт в get_sunrise_sunset().
    """
    T   = (jd - 2451545.0) / 36525.0
    L0  = (280.46646 + 36000.76983*T) % 360
    M   = math.radians((357.52911 + 35999.05029*T) % 360)
    C   = ((1.914602 - 0.004817*T)*math.sin(M)
          + 0.019993*math.sin(2*M)
          + 0.000289*math.sin(3*M))
    sl  = (L0 + C) % 360
    omega   = 125.04 - 1934.136*T
    app_lon = math.radians(sl - 0.00569 - 0.00478*math.sin(math.radians(omega)))
    eps     = math.radians(23.439291111 - 0.013004167*T
                           + 0.000164*math.sin(math.radians(omega)))
    dec     = math.asin(math.sin(eps)*math.sin(app_lon))
    ra      = math.degrees(math.atan2(math.cos(eps)*math.sin(app_lon), math.cos(app_lon))) % 360
    eot_min = ((L0 - 0.0057183 - ra + 180*(round((L0-ra)/180))) * 4)
    return dec, eot_min


def get_sunrise_sunset(jd_day: float, lat: float, lon: float, tz: float,
                       elev_m: float = 0.0) -> tuple:
    """
    Возвращает (jd_sunrise, jd_sunset).

    Точность: DE431 + rise_trans → < 1 сек.
    Для полярных широт (полярный день/ночь) возвращает полдень дважды.

    rise_trans ищет событие ПОСЛЕ переданного JD.
    Начинаем с 00:00 UTC чтобы гарантированно найти восход текущего дня.
    """
    geopos   = (lon, lat, elev_m / 1000.0)   # высота в км
    jd_start = math.floor(jd_day + 0.5) - 0.5  # 00:00 UTC текущего дня

    def _rise_trans(jd_s, rsmi):
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

    # Полярный день/ночь — геометрический расчёт по Meeus
    jd0   = math.floor(jd_day + 0.5) - 0.5
    dec, eot = _sun_params(jd0)
    lat_r = math.radians(lat)
    cos_H = (math.sin(math.radians(-0.8333)) - math.sin(lat_r)*math.sin(dec)) / \
            (math.cos(lat_r)*math.cos(dec))
    noon_jd = jd0 + (12.0 - lon/15.0 - eot/60.0) / 24.0
    if abs(cos_H) > 1:
        return noon_jd, noon_jd
    H_h = math.degrees(math.acos(cos_H)) / 15.0
    return noon_jd - H_h/24.0, noon_jd + H_h/24.0

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ ТИТХИ
# ═══════════════════════════════════════════════════════════

def calc_tithis(jd_s: float, jd_e: float, tz: float, step_h: float = 0.5) -> list:
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
#  РАСЧЁТ НИТЬЯ-ЙОГ
# ═══════════════════════════════════════════════════════════

def calc_yogas(jd_s: float, jd_e: float, tz: float, step_h: float = 0.5) -> list:
    """Список нитья-йог за период с временем начала/конца.

    Средняя длительность йоги ~22.6 ч (минимум ~19.5 ч), поэтому шага 0.5 ч
    заведомо хватает: (Солнце+Луна) растёт монотонно, пропусков границ нет.
    """
    step = step_h / 24
    transitions = []
    jd_cur = jd_s; prev = yoga_index(jd_cur)
    while jd_cur <= jd_e:
        jd_nx = jd_cur + step
        cur = yoga_index(jd_nx)
        if cur != prev:
            transitions.append(_bisect(jd_cur, jd_nx, yoga_index, prev))
            prev = cur
        jd_cur = jd_nx

    all_jd = [jd_s] + transitions + [jd_e]
    result = []
    for i in range(len(all_jd)-1):
        js, je = all_jd[i], all_jd[i+1]
        y = YOGAS[yoga_index(js)]
        result.append({
            "num": y[0], "name": y[1], "quality": y[2],
            "is_stop": y[0] in YOGA_STOP_NUMS,
            "jd_start": js, "jd_end": je,
            "dt_start": jd_to_local(js, tz),
            "dt_end":   jd_to_local(je, tz),
            "duration_h": (je-js)*24,
            "sun_moon_sum": round((sun_lon_sid(js)+moon_lon_sid(js)) % 360, 3),
        })
    return result

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ КАРАН
# ═══════════════════════════════════════════════════════════

def calc_karanas(jd_s: float, jd_e: float, tz: float, step_h: float = 0.5) -> list:
    """Список каран за период с временем начала/конца.

    Карана = половина титхи (~11.8 ч в среднем, минимум ~10 ч).
    Поле is_bhadra помечает Вишти/Бхадру — стоп-фактор панчанги.
    """
    step = step_h / 24
    transitions = []
    jd_cur = jd_s; prev = karana_index(jd_cur)
    while jd_cur <= jd_e:
        jd_nx = jd_cur + step
        cur = karana_index(jd_nx)
        if cur != prev:
            transitions.append(_bisect(jd_cur, jd_nx, karana_index, prev))
            prev = cur
        jd_cur = jd_nx

    all_jd = [jd_s] + transitions + [jd_e]
    result = []
    for i in range(len(all_jd)-1):
        js, je = all_jd[i], all_jd[i+1]
        k   = karana_index(js)
        kar = KARANAS[karana_num_for_half(k) - 1]
        result.append({
            "num": kar[0], "name": kar[1], "type": kar[2], "quality": kar[3],
            "type_label":   KARANA_TYPE_LABEL[kar[2]],
            "num_in_month": k + 1,             # 1-60: номер полутитхи в лунном месяце
            "tithi_num":    k // 2 + 1,        # титхи, которой принадлежит карана
            "tithi_half":   k % 2 + 1,         # 1 — первая половина, 2 — вторая
            "is_bhadra":    kar[0] == KARANAS[_KARANA_VISHTI][0],
            "jd_start": js, "jd_end": je,
            "dt_start": jd_to_local(js, tz),
            "dt_end":   jd_to_local(je, tz),
            "duration_h": (je-js)*24,
            "moon_sun_diff": round((moon_lon(js)-sun_lon(js)) % 360, 3),
        })
    return result

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ МУХУРТ
# ═══════════════════════════════════════════════════════════

def calc_muhurtas_day(jd_sunrise: float, jd_sunset: float,
                      jd_next_sunrise: float, tz: float) -> list:
    """
    30 мухурт: 15 дневных (восход→закат) + 15 ночных (закат→следующий восход).
    Каждая мухурта = 1/15 длины своего периода.
    Длительность меняется день ото дня: зимой ~40 мин, летом ~56 мин.
    """
    day_dur   = jd_sunset       - jd_sunrise
    night_dur = jd_next_sunrise - jd_sunset
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

def calc_horas_day(jd_sunrise: float, jd_sunset: float,
                   jd_next_sunrise: float, tz: float) -> list:
    """24 хоры: 12 дневных (восход→закат) + 12 ночных (закат→следующий восход)."""
    dt_sunrise_local = jd_to_local(jd_sunrise, tz)
    weekday = dt_sunrise_local.weekday()   # 0=Пн, соответствует WEEKDAY_FIRST_HORA

    first_planet = WEEKDAY_FIRST_HORA[weekday]
    start_idx    = HORA_PLANETS.index(first_planet)

    day_dur    = jd_sunset       - jd_sunrise
    night_dur  = jd_next_sunrise - jd_sunset
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
    jd_s = dt_to_jd(datetime(date_start.year, date_start.month, date_start.day))           - tz/24
    jd_e = dt_to_jd(datetime(date_end.year,   date_end.month,   date_end.day, 23, 59, 59)) - tz/24

    tithis  = calc_tithis(jd_s, jd_e, tz)
    yogas   = calc_yogas(jd_s, jd_e, tz)
    karanas = calc_karanas(jd_s, jd_e, tz)

    days = []
    current = date_start
    while current <= date_end:
        jd_noon = dt_to_jd(datetime(current.year, current.month, current.day, 12, 0)) - tz/24
        jd_rise, jd_set = get_sunrise_sunset(jd_noon, lat, lon, tz, elev_m)

        # Следующий восход — реальный расчёт (не +24ч)
        jd_rise_next, _ = get_sunrise_sunset(jd_noon + 1.0, lat, lon, tz, elev_m)

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

    return {"tithis": tithis, "yogas": yogas, "karanas": karanas, "days": days}

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
    """Вернуть элементы списка, чьё dt_start попадает в [dt_start, dt_end)."""
    return [x for x in items if dt_start <= x["dt_start"] < dt_end]


def _all_muhurtas(data):
    result = []
    for day in data["days"]:
        result.extend(day["muhurtas"])
    return result


def _all_horas(data):
    result = []
    for day in data["days"]:
        result.extend(day["horas"])
    return result


def print_panchang(data, date_start, date_end, tz, lat, lon):
    tz_str = f"UTC{'+' if tz >= 0 else ''}{tz:g}"
    W = 72

    print("\n" + "═"*W)
    print("  ПАНЧАНГ  —  Титхи · Мухурты · Хоры")
    print("═"*W)
    print(f"  Период   : {date_start.strftime('%d.%m.%Y')} — {date_end.strftime('%d.%m.%Y')}")
    print(f"  Часовой  : {tz_str}  |  lat {lat}°  lon {lon}°")
    print(f"  Метод    : Swiss Ephemeris (DE431, ~0.001\")  |  Точность: ±1 сек")
    print()

    all_muh  = _all_muhurtas(data)
    all_hora = _all_horas(data)

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

        print("━"*W)
        print(f"  #{tithi['num']:02d}  {tithi['name']}   {paksha}")
        print(f"  {ts}  →  {te}   "
              f"({fmt_dur(tithi['duration_h'])})   "
              f"{mark} {tithi['quality']}")
        print()

        # Восход/закат для дней внутри титхи
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

        # Мухурты внутри этой титхи
        muhs = _items_in_range(all_muh, t_s, t_e)
        if muhs:
            print("  Мухурты")
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

        # Хоры внутри этой титхи
        horas = _items_in_range(all_hora, t_s, t_e)
        if horas:
            print("  Хоры (планетарные часы)")
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
        try:
            return cast(input(prompt).strip())
        except Exception:
            print(f"  Ошибка: {err}")


def parse_date(s):
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
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
