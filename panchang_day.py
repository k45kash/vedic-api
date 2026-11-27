"""Интервалы дневной панчанги. Время ответа — местное, с заданным UTC-смещением."""
from datetime import datetime, time, timedelta, timezone

import swisseph as swe

from Panchangam import (TITHIS, tithi_index, calc_horas_day, calc_karanas, calc_muhurtas_day, calc_tithis,
                        calc_yogas, moon_lon_sid)
from nakshatra_calculator import SIGNS, get_aya
from utils import NAKSHATRAS, _bisect, dt_to_jd, jd_to_local

WEEK = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")


def state_intervals(midnight, limit, tz, state, entries, step, pad):
    """Ищем границы за пределами окна. На выходе сохраняем обе полные даты."""
    left = midnight - pad
    previous = state(left)
    start = left
    rows = []
    while left < limit + pad:
        right = left + step
        current = state(right)
        if current != previous:
            edge = _bisect(left, right, state, previous)
            if edge > midnight and start < limit:
                entry = entries[previous]
                rows.append(dict(num=previous + 1, name=entry["ru"], lord=entry["lord"],
                                 dt_start=jd_to_local(start, tz), dt_end=jd_to_local(edge, tz)))
            if edge >= limit:
                break
            previous, start = current, edge
        left = right
    return rows


def utc_midnight(day, zone):
    return datetime.combine(day, time.min, tzinfo=zone).astimezone(timezone.utc)


def solar_cycles(jd, limit, lat, lon):
    def solar_event(after, event):
        status, values = swe.rise_trans(after, swe.SUN, event, (lon, lat, 0),
                                        1013.25, 15., swe.FLG_SWIEPH)
        return values[0] if status == 0 else None

    # Закат может прийтись на другую гражданскую дату.
    rise = solar_event(jd - 2, swe.CALC_RISE)
    while rise is not None and rise < limit:
        sunset = solar_event(rise, swe.CALC_SET)
        following = solar_event(rise + 0.001, swe.CALC_RISE)
        if not following or not sunset or not rise < sunset < following:
            break
        if following > jd:
            yield rise, sunset, following
        rise = following


def moon_nakshatras(jd, limit, tz):
    return state_intervals(jd, limit, tz, lambda t: int(moon_lon_sid(t) / (360 / 27)),
                           NAKSHATRAS, 1/24, 2)


RAHU_SEGMENT = (2, 7, 5, 6, 4, 3, 8)


def tara_window_timeline(first, last, lat, lon, tz):
    """Факторы подбора времени за весь диапазон в заданном UTC-смещении."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    begin = datetime.combine(first, time.min)
    end = datetime.combine(last + timedelta(days=1), time.min)
    jd = dt_to_jd(begin) - tz / 24
    limit = jd + (end - begin).days
    rows = dict(nakshatra=moon_nakshatras(jd, limit, tz),
                tithi=calc_tithis(jd - 2, limit + 2, tz),
                yoga=calc_yogas(jd - 2, limit + 2, tz),
                karana=[row for row in calc_karanas(jd - 2, limit + 2, tz) if row["is_bhadra"]],
                vara=[], abhijit=[], rahu=[])
    # Каждый день ищет цикл независимо, как дневная панчанга.
    # Пропущенный восход на полярной широте не останавливает весь диапазон.
    cycles = (cycle for offset in range((end - begin).days)
              for cycle in solar_cycles(jd + offset, jd + offset + 1, lat, lon))
    seen = set()
    for rise, sunset, following in cycles:
        dawn, dusk, next_dawn = (jd_to_local(t, tz) for t in (rise, sunset, following))
        if dawn in seen:
            continue
        seen.add(dawn)
        weekday = dawn.weekday()
        rows["vara"].append(dict(num=weekday+1, dt_start=dawn, dt_end=next_dawn))
        rows["abhijit"].append(calc_muhurtas_day(rise, sunset, following, tz)[7])
        segment = RAHU_SEGMENT[weekday]
        rows["rahu"].append(dict(dt_start=dawn+(dusk-dawn)*(segment-1)/8,
                                 dt_end=dawn+(dusk-dawn)*segment/8))
    return {key: [row for row in items if row["dt_start"] < end and row["dt_end"] > begin]
            for key, items in rows.items()}


def day_timeline(date, lat, lon, tz, zone=None):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    begin = datetime.combine(date, time.min)
    end = begin + timedelta(days=1)
    if zone is None:
        jd = dt_to_jd(begin) - tz / 24
        limit = jd + 1
    else:
        local_start = utc_midnight(date, zone)
        local_end = utc_midnight(end.date(), zone)
        begin, end = [stamp.replace(tzinfo=None) for stamp in (local_start, local_end)]
        jd, limit = dt_to_jd(begin), dt_to_jd(end)
        tz = 0
        if begin == end:
            return dict(date=date, rows={}, warnings=["Этой местной даты нет в часовом поясе."],
                        start=local_start, end=local_end, timezone=zone.key)
    rows = {}
    for key, calc in (("tithi", calc_tithis), ("karana", calc_karanas), ("yoga", calc_yogas)):
        rows[key] = calc(jd - 2, limit + 2, tz)

    rows["nakshatra"] = moon_nakshatras(jd, limit, tz)
    rows["moon"] = state_intervals(jd, limit, tz, lambda t: int(moon_lon_sid(t) / 30), SIGNS, 1/12, 4)
    warnings = []
    rows["lagna"] = []
    if abs(lat) < 66:
        def asc_sign(t):
            asc = swe.houses(t, lat, lon, b'W')[1][0]
            return int(((asc - get_aya(t)) % 360) / 30)
        rows["lagna"] = state_intervals(jd, limit, tz, asc_sign, SIGNS, 1/1440, 0.3)
    else:
        warnings.append("Ряд лагны доступен для широт ниже 66° по модулю.")

    for key in ("vara", "light", "yama", "muhurta", "hora", "rahu", "abhijit"):
        rows[key] = []

    for rise, sunset, following in solar_cycles(jd, limit, lat, lon):
        dawn, dusk, next_dawn = (jd_to_local(t, tz) for t in (rise, sunset, following))
        weekday = (dawn.replace(tzinfo=timezone.utc).astimezone(zone) if zone else dawn).weekday()
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
                if name == "День" and n+1 == RAHU_SEGMENT[weekday]:
                    rows["rahu"].append(dict(part, name="Раху-кала"))

    visible = {key: [r for r in items if r["dt_start"] < end and r["dt_end"] > begin]
               for key, items in rows.items()}
    if not visible["vara"]:
        warnings.append("Для этих суток цикл от восхода до следующего восхода недоступен.")
    response = dict(date=date, rows=visible, warnings=warnings)
    if zone is not None:
        response.update(start=local_start, end=local_end, timezone=zone.key)
        for intervals in visible.values():
            for row in intervals:
                for key in ("dt_start", "dt_end", "sunset"):
                    if key in row:
                        row[key] = row[key].replace(tzinfo=timezone.utc).astimezone(zone)
    return response


def month_summary(first, lat, lon, tz, zone=None):
    """Титхи и накшатра на восходе, а также Бхадра в гражданских сутках."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    following = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    count = (following - first).days
    if zone:
        bounds = [dt_to_jd(utc_midnight(first + timedelta(days=i), zone).replace(tzinfo=None))
                  for i in range(count + 1)]
        tz = 0
    else:
        start = dt_to_jd(datetime.combine(first, time.min)) - tz / 24
        bounds = [start + i for i in range(count + 1)]
    bhadra = [row for row in calc_karanas(bounds[0], bounds[-1], tz) if row["is_bhadra"]]
    days = []
    for offset in range(count):
        midnight, limit = bounds[offset:offset+2]
        day = first + timedelta(days=offset)
        status, times = swe.rise_trans(midnight, swe.SUN, swe.CALC_RISE, (lon, lat, 0),
                                       1013.25, 15., swe.FLG_SWIEPH)
        result = dict(date=day, tithi=None, nakshatra=None,
                      bhadra=midnight < limit and any(row["jd_start"] < limit and row["jd_end"] > midnight
                                 for row in bhadra))
        if status == 0 and midnight <= times[0] < limit:
            sunrise = times[0]
            result["tithi"] = TITHIS[tithi_index(sunrise)][1]
            result["nakshatra"] = NAKSHATRAS[int(moon_lon_sid(sunrise) / (360 / 27))]["ru"]
        days.append(result)
    return days
