"""Общие утилиты для всех модулей ведической астрологии."""

from datetime import datetime, timedelta


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
