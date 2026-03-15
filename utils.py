"""Общие утилиты для всех модулей ведической астрологии."""

from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════
#  ЕДИНЫЙ СПРАВОЧНИК НАКШАТР
#  Поля: num, name, ru, lord, gana, symbol
#  Гана: Devata/Manushya/Rakshasa — традиционное разбиение 9-9-9
# ═══════════════════════════════════════════════════════════

NAKSHATRAS = [
    {"num":1,  "name":"Ashwini",        "ru":"Ашвини",          "lord":"Кету",     "gana":"Devata",   "symbol":"Голова лошади"},
    {"num":2,  "name":"Bharani",        "ru":"Бхарани",         "lord":"Венера",   "gana":"Manushya", "symbol":"Йони (лоно)"},
    {"num":3,  "name":"Krittika",       "ru":"Криттика",        "lord":"Солнце",   "gana":"Rakshasa", "symbol":"Бритва / пламя"},
    {"num":4,  "name":"Rohini",         "ru":"Рохини",          "lord":"Луна",     "gana":"Manushya", "symbol":"Колесница"},
    {"num":5,  "name":"Mrigashira",     "ru":"Мригашира",       "lord":"Марс",     "gana":"Devata",   "symbol":"Голова оленя"},
    {"num":6,  "name":"Ardra",          "ru":"Ардра",           "lord":"Раху",     "gana":"Manushya", "symbol":"Слеза / Алмаз"},
    {"num":7,  "name":"Punarvasu",      "ru":"Пунарвасу",       "lord":"Юпитер",   "gana":"Devata",   "symbol":"Колчан со стрелами"},
    {"num":8,  "name":"Pushya",         "ru":"Пушья",           "lord":"Сатурн",   "gana":"Devata",   "symbol":"Цветок лотоса"},
    {"num":9,  "name":"Ashlesha",       "ru":"Ашлеша",          "lord":"Меркурий", "gana":"Rakshasa", "symbol":"Змея"},
    {"num":10, "name":"Magha",          "ru":"Магха",           "lord":"Кету",     "gana":"Rakshasa", "symbol":"Королевский трон"},
    {"num":11, "name":"Purvaphalguni",  "ru":"Пурва Пхалгуни",  "lord":"Венера",   "gana":"Manushya", "symbol":"Гамак / ложе"},
    {"num":12, "name":"Uttaraphalguni", "ru":"Уттара Пхалгуни", "lord":"Солнце",   "gana":"Manushya", "symbol":"Кровать"},
    {"num":13, "name":"Hasta",          "ru":"Хаста",           "lord":"Луна",     "gana":"Devata",   "symbol":"Рука / кулак"},
    {"num":14, "name":"Chitra",         "ru":"Читра",           "lord":"Марс",     "gana":"Rakshasa", "symbol":"Жемчужина"},
    {"num":15, "name":"Swati",          "ru":"Свати",           "lord":"Раху",     "gana":"Devata",   "symbol":"Молодой росток"},
    {"num":16, "name":"Vishakha",       "ru":"Вишакха",         "lord":"Юпитер",   "gana":"Rakshasa", "symbol":"Украшенные ворота"},
    {"num":17, "name":"Anuradha",       "ru":"Анурадха",        "lord":"Сатурн",   "gana":"Devata",   "symbol":"Лотос"},
    {"num":18, "name":"Jyeshtha",       "ru":"Джьештха",        "lord":"Меркурий", "gana":"Rakshasa", "symbol":"Серьга / зонтик"},
    {"num":19, "name":"Mula",           "ru":"Мула",            "lord":"Кету",     "gana":"Rakshasa", "symbol":"Связка корней"},
    {"num":20, "name":"Purvashadha",    "ru":"Пурвашадха",      "lord":"Венера",   "gana":"Manushya", "symbol":"Веер / бивень слона"},
    {"num":21, "name":"Uttarashadha",   "ru":"Уттарашадха",     "lord":"Солнце",   "gana":"Manushya", "symbol":"Слоновий бивень"},
    {"num":22, "name":"Shravana",       "ru":"Шравана",         "lord":"Луна",     "gana":"Devata",   "symbol":"Три следа"},
    {"num":23, "name":"Dhanishtha",     "ru":"Дхаништха",       "lord":"Марс",     "gana":"Rakshasa", "symbol":"Барабан"},
    {"num":24, "name":"Shatabhisha",    "ru":"Шатабхиша",       "lord":"Раху",     "gana":"Rakshasa", "symbol":"Пустой круг"},
    {"num":25, "name":"Purvabhadra",    "ru":"Пурвабхадра",     "lord":"Юпитер",   "gana":"Manushya", "symbol":"Меч / двуликий"},
    {"num":26, "name":"Uttarabhadra",   "ru":"Уттарабхадра",    "lord":"Сатурн",   "gana":"Manushya", "symbol":"Змея в воде"},
    {"num":27, "name":"Revati",         "ru":"Ревати",          "lord":"Меркурий", "gana":"Devata",   "symbol":"Барабан / рыба"},
]


def dt_to_jd(dt: datetime) -> float:
    """datetime (UTC naive) → Julian Day.
    Даты до 1582-10-15 трактуются как юлианские (B=0),
    начиная с 1582-10-15 — как григорианские.
    """
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1; m += 12
    if dt.year > 1582 or (dt.year == 1582 and (dt.month > 10 or (dt.month == 10 and dt.day >= 15))):
        A = int(y / 100)
        B = 2 - A + int(A / 4)
    else:
        B = 0
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5


def jd_to_dt_utc(jd: float) -> datetime:
    """Julian Day → datetime UTC."""
    jd2 = jd + 0.5
    Z = int(jd2); F = jd2 - Z
    if Z < 2299161:
        A = Z
    else:
        alpha = int((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - int(alpha / 4)
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    df  = B - D - int(30.6001 * E) + F
    day = int(df); frac = df - day
    hf  = frac * 24; h = int(hf)
    mf  = (hf - h) * 60; mn = int(mf)
    sec = int((mf - mn) * 60 + 0.5)
    mon = E - 1 if E < 14 else E - 13
    yr  = C - 4716 if mon > 2 else C - 4715
    if sec >= 60: sec -= 60; mn  += 1
    if mn  >= 60: mn  -= 60; h   += 1
    if h   >= 24: h   -= 24; day += 1
    return datetime(yr, mon, day, h, mn, sec)


def jd_to_local(jd: float, tz: float) -> datetime:
    """JD → local datetime."""
    return jd_to_dt_utc(jd) + timedelta(hours=tz)


def _bisect(jd_lo: float, jd_hi: float, state_fn, state_lo, prec_sec: float = 1.0) -> float:
    """Бинарный поиск момента, когда state_fn() меняет значение.
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


def dms(degrees: float) -> str:
    """Долгота 0-359° → ДДД°ММ'СС\"."""
    degrees = degrees % 360
    total_sec = round(degrees * 3600)
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    d = total_min // 60
    return f"{d}\u00b0{m:02d}'{s:02d}\""


def dms_sign(deg_in_sign: float) -> str:
    """Градус внутри знака 0-29° → Д°ММ'СС\" (формат JHora/Kala/Parashara)."""
    total_sec = round(deg_in_sign * 3600)
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    d = total_min // 60
    return f"{d}\u00b0{m:02d}'{s:02d}\""
