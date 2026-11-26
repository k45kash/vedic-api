"""Интервалы дневной панчанги. Время ответа — местное, с заданным UTC-смещением."""
from datetime import datetime, time, timedelta

import swisseph as swe

from Panchangam import (calc_horas_day, calc_karanas, calc_muhurtas_day, calc_tithis,
                        calc_yogas, moon_lon_sid)
from nakshatra_calculator import SIGNS, get_aya
from utils import NAKSHATRAS, _bisect, dt_to_jd, jd_to_local

WEEK = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")


def state_intervals(midnight, tz, state, entries, step, pad):
    """Ищем границы за пределами окна. На выходе сохраняем обе полные даты."""
    left = midnight - pad
    previous = state(left)
    start = left
    rows = []
    while left < midnight + 1 + pad:
        right = left + step
        current = state(right)
        if current != previous:
            edge = _bisect(left, right, state, previous)
            if edge > midnight and start < midnight + 1:
                entry = entries[previous]
                rows.append(dict(num=previous + 1, name=entry["ru"], lord=entry["lord"],
                                 dt_start=jd_to_local(start, tz), dt_end=jd_to_local(edge, tz)))
            if edge >= midnight + 1:
                break
            previous, start = current, edge
        left = right
    return rows


def day_timeline(date, lat, lon, tz):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    begin = datetime.combine(date, time.min)
    end = begin + timedelta(days=1)
    jd = dt_to_jd(begin) - tz / 24
    rows = {}
    for key, calc in (("tithi", calc_tithis), ("karana", calc_karanas), ("yoga", calc_yogas)):
        rows[key] = calc(jd - 2, jd + 3, tz)

    rows["nakshatra"] = state_intervals(jd, tz, lambda t: int(moon_lon_sid(t) / (360 / 27)),
                                       NAKSHATRAS, 1/24, 2)
    rows["moon"] = state_intervals(jd, tz, lambda t: int(moon_lon_sid(t) / 30), SIGNS, 1/12, 4)
    warnings = []
    rows["lagna"] = []
    if abs(lat) < 66:
        def asc_sign(t):
            asc = swe.houses(t, lat, lon, b'W')[1][0]
            return int(((asc - get_aya(t)) % 360) / 30)
        rows["lagna"] = state_intervals(jd, tz, asc_sign, SIGNS, 1/1440, 0.3)
    else:
        warnings.append("Ряд лагны доступен для широт ниже 66° по модулю.")

    for key in ("vara", "light", "yama", "muhurta", "hora", "rahu", "abhijit"):
        rows[key] = []

    def solar_event(after, event):
        status, values = swe.rise_trans(after, swe.SUN, event, (lon, lat, 0),
                                        1013.25, 15., swe.FLG_SWIEPH)
        return values[0] if status == 0 else None

    # Собираем циклы от реального восхода. Закат может прийтись и на другую гражданскую дату.
    rise = solar_event(jd - 2, swe.CALC_RISE)
    while rise is not None and rise < jd + 1:
        sunset = solar_event(rise, swe.CALC_SET)
        following = solar_event(rise + 0.001, swe.CALC_RISE)
        if not following or not sunset or not rise < sunset < following:
            break
        if following > jd:
            dawn, dusk, next_dawn = (jd_to_local(t, tz) for t in (rise, sunset, following))
            weekday = dawn.weekday()
            rows["vara"].append(dict(name=WEEK[weekday], num=weekday+1, dt_start=dawn,
                                     dt_end=next_dawn, sunset=dusk))
            muhurtas = calc_muhurtas_day(rise, sunset, following, tz)
            rows["muhurta"].extend(muhurtas)
            rows["abhijit"].append(dict(muhurtas[7], name="Абхиджит"))
            rows["hora"].extend(calc_horas_day(rise, sunset, following, tz))
            for name, a, b in (("День", dawn, dusk), ("Ночь", dusk, next_dawn)):
                rows["light"].append(dict(name=name, dt_start=a, dt_end=b))
                for n in range(8):
                    part = dict(num=n+1, name=f"{name} · {n+1}", dt_start=a+(b-a)*n/8,
                                dt_end=a+(b-a)*(n+1)/8)
                    rows["yama"].append(part)
                    if name == "День" and n+1 == (2, 7, 5, 6, 4, 3, 8)[weekday]:
                        rows["rahu"].append(dict(part, name="Раху-кала"))
        rise = following

    visible = {key: [r for r in items if r["dt_start"] < end and r["dt_end"] > begin]
               for key, items in rows.items()}
    if not visible["vara"]:
        warnings.append("Для этих суток цикл от восхода до следующего восхода недоступен.")
    return dict(date=date, rows=visible, warnings=warnings)
