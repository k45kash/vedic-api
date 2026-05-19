"""
╔═══════════════════════════════════════════════════════════════════╗
║   САДИ САТИ — 7,5-летний транзит Сатурна вокруг натальной Луны   ║
║   + Аштама Шани (8-й знак от Луны)                                ║
║   + Кантака Шани / Ардха-аштама (4-й знак от Луны)                ║
╚═══════════════════════════════════════════════════════════════════╝

Сади Сати: транзит Сатурна по трём знакам подряд — 12-му, 1-му (знак
           натальной Луны) и 2-му. Каждая фаза ~2,5 года, общий цикл ~7,5 лет.
Аштама Шани:  Сатурн в 8-м знаке от Луны (~2,5 года).
Кантака Шани: Сатурн в 4-м знаке от Луны (~2,5 года).

Учитывается ретроградность Сатурна: каждый эпизод — непрерывное
пребывание в одном знаке, эпизоды одного цикла группируются вместе.

Запуск:
    python sade_sati.py --period 1990 5 17 14 30 3
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Optional

import swisseph as swe

from utils import dt_to_jd, jd_to_local, _bisect, dms, dms_sign, NAKSHATRAS

EPHE_PATH = os.environ.get(
    "SE_EPHE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
)
swe.set_ephe_path(EPHE_PATH)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ═══════════════════════════════════════════════════════════
#  СПРАВОЧНИКИ
# ═══════════════════════════════════════════════════════════

SIGNS = [
    {"num":1,  "name":"Aries",       "ru":"Овен",      "lord":"Марс",     "element":"Огонь"},
    {"num":2,  "name":"Taurus",      "ru":"Телец",     "lord":"Венера",   "element":"Земля"},
    {"num":3,  "name":"Gemini",      "ru":"Близнецы",  "lord":"Меркурий", "element":"Воздух"},
    {"num":4,  "name":"Cancer",      "ru":"Рак",       "lord":"Луна",     "element":"Вода"},
    {"num":5,  "name":"Leo",         "ru":"Лев",       "lord":"Солнце",   "element":"Огонь"},
    {"num":6,  "name":"Virgo",       "ru":"Дева",      "lord":"Меркурий", "element":"Земля"},
    {"num":7,  "name":"Libra",       "ru":"Весы",      "lord":"Венера",   "element":"Воздух"},
    {"num":8,  "name":"Scorpio",     "ru":"Скорпион",  "lord":"Марс",     "element":"Вода"},
    {"num":9,  "name":"Sagittarius", "ru":"Стрелец",   "lord":"Юпитер",   "element":"Огонь"},
    {"num":10, "name":"Capricorn",   "ru":"Козерог",   "lord":"Сатурн",   "element":"Земля"},
    {"num":11, "name":"Aquarius",    "ru":"Водолей",   "lord":"Сатурн",   "element":"Воздух"},
    {"num":12, "name":"Pisces",      "ru":"Рыбы",      "lord":"Юпитер",   "element":"Вода"},
]

NK_SIZE = 360.0 / 27

# Скорость Сатурна ~0.034°/день; знак (30°) проходит за ~880 дней.
# Шаг 2 дня даёт ~0.07° между точками — гарантированно ловит любую смену знака,
# включая 3-кратные пересечения границы при ретроградности.
SEARCH_STEP_DAYS = 2.0

# Минимальный разрыв между циклами Сади Сати — между ними ~22 года, так что
# 5 лет — безопасный порог разделения.
CYCLE_GAP_DAYS = 365.25 * 5

# Топоцентрический параллакс Луны достигает ~1°. Если Луна ближе 1° к границе
# знака — пересчитываем топоцентрически: для пограничных рождений знак может
# поменяться, что развернёт весь Сади Сати.
BOUNDARY_CHECK_DEG = 1.0

# ═══════════════════════════════════════════════════════════
#  АСТРОНОМИЯ
# ═══════════════════════════════════════════════════════════

def get_aya(jd: float) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa_ut(jd)


def saturn_sid(jd: float) -> float:
    """Сидерическая долгота Сатурна (Лахири)."""
    aya = get_aya(jd)
    pos, _ = swe.calc_ut(jd, swe.SATURN, swe.FLG_SWIEPH)
    return (pos[0] - aya) % 360


def saturn_sign(jd: float) -> int:
    """Знак Сатурна (1-12)."""
    return int(saturn_sid(jd) / 30) + 1


def _moon_sid_at(jd: float, aya: float, topo: bool,
                 lat: float, lon: float) -> float:
    """Сидерическая долгота Луны: гео- или топоцентрическая."""
    fl = swe.FLG_SWIEPH
    if topo:
        swe.set_topo(lon, lat, 0)
        fl |= swe.FLG_TOPOCTR
    pos, _ = swe.calc_ut(jd, swe.MOON, fl)
    return (pos[0] - aya) % 360


def moon_natal(jd: float, lat: float = 0.0, lon: float = 0.0) -> dict:
    """Натальная Луна: знак, сидерическая долгота, накшатра, пада.

    На границе знака (<1°) пересчитывает топоцентрически и, если знак меняется,
    использует топоцентрический результат — для Сади Сати это критично, так как
    весь расчёт строится от знака Луны.
    """
    aya     = get_aya(jd)
    sid_geo = _moon_sid_at(jd, aya, topo=False, lat=lat, lon=lon)

    sign_geo    = int(sid_geo / 30) + 1
    pos_in_sign = sid_geo % 30
    dist_bound  = min(pos_in_sign, 30 - pos_in_sign)

    use_topo = False
    boundary = {
        "near_boundary":         dist_bound < BOUNDARY_CHECK_DEG,
        "dist_to_boundary_deg":  round(dist_bound, 4),
        "topo_applied":          False,
        "sign_changed_by_topo":  False,
    }

    if boundary["near_boundary"] and (lat != 0.0 or lon != 0.0):
        sid_topo  = _moon_sid_at(jd, aya, topo=True, lat=lat, lon=lon)
        sign_topo = int(sid_topo / 30) + 1
        boundary.update({
            "topo_applied":         True,
            "geo_sid":              round(sid_geo, 6),
            "topo_sid":             round(sid_topo, 6),
            "delta_arcsec":         round((sid_topo - sid_geo) * 3600, 2),
            "geo_sign_num":         sign_geo,
            "topo_sign_num":        sign_topo,
            "sign_changed_by_topo": sign_topo != sign_geo,
        })
        use_topo = True
        sid_final  = sid_topo
        sign_final = sign_topo
    else:
        sid_final  = sid_geo
        sign_final = sign_geo

    deg_in_sign = sid_final % 30
    nk_idx      = int(sid_final / NK_SIZE) % 27
    pada        = int((sid_final % NK_SIZE) / (NK_SIZE / 4)) + 1
    nk = NAKSHATRAS[nk_idx]
    s  = SIGNS[sign_final - 1]
    return {
        "sign_num":        sign_final,
        "sign":            s["name"],
        "sign_ru":         s["ru"],
        "sign_lord":       s["lord"],
        "sid":             round(sid_final, 6),
        "sid_dms":         dms(sid_final),
        "deg_in_sign":     round(deg_in_sign, 6),
        "deg_in_sign_dms": dms_sign(deg_in_sign),
        "nakshatra":       nk["name"],
        "nakshatra_ru":    nk["ru"],
        "pada":            pada,
        "nk_lord":         nk["lord"],
        "frame":           "topocentric" if use_topo else "geocentric",
        "boundary":        boundary,
    }

# ═══════════════════════════════════════════════════════════
#  ТРАНЗИТЫ САТУРНА
# ═══════════════════════════════════════════════════════════

def find_saturn_transitions(jd_start: float, jd_end: float,
                            step_days: float = SEARCH_STEP_DAYS) -> list:
    """Все смены знака Сатурном в [jd_start, jd_end].
    Возвращает список (jd_перехода, новый_знак).
    """
    transitions = []
    jd  = jd_start
    prev = saturn_sign(jd)
    while jd < jd_end:
        jd_nx = min(jd + step_days, jd_end)
        cur   = saturn_sign(jd_nx)
        if cur != prev:
            t = _bisect(jd, jd_nx, saturn_sign, prev, prec_sec=60.0)
            transitions.append((t, cur))
            prev = cur
        jd = jd_nx
    return transitions


def episodes_in_signs(jd_start: float, jd_end: float, transitions: list,
                      target_signs: dict, tz: float) -> list:
    """Эпизоды пребывания Сатурна в одном из target_signs.
    target_signs: {sign_num: phase_label}.
    Каждый эпизод — непрерывное пребывание в одном знаке (с учётом ретро
    эпизодов одного знака может быть несколько).
    """
    episodes = []
    cur_jd   = jd_start
    cur_sign = saturn_sign(jd_start)

    boundaries = transitions + [(jd_end, None)]
    for jd_t, new_sign in boundaries:
        if cur_sign in target_signs:
            episodes.append({
                "phase":           target_signs[cur_sign],
                "sign_num":        cur_sign,
                "sign":            SIGNS[cur_sign - 1]["name"],
                "sign_ru":         SIGNS[cur_sign - 1]["ru"],
                "jd_start":        cur_jd,
                "jd_end":          jd_t,
                "dt_start":        jd_to_local(cur_jd, tz),
                "dt_end":          jd_to_local(jd_t, tz),
                "duration_days":   round(jd_t - cur_jd, 2),
                "truncated_start": cur_jd == jd_start,
                "truncated_end":   new_sign is None,
            })
        cur_jd = jd_t
        if new_sign is not None:
            cur_sign = new_sign
    return episodes


def group_sade_sati_cycles(episodes: list,
                           max_gap_days: float = CYCLE_GAP_DAYS) -> list:
    """Группирует эпизоды Сади Сати в циклы по ~7,5 лет.
    Эпизоды одного цикла разделены ретро-возвратами (дни-недели),
    между разными циклами — ~22 года.
    """
    cycles = []
    cur    = []
    for ep in episodes:
        if not cur:
            cur.append(ep)
        else:
            gap = ep["jd_start"] - cur[-1]["jd_end"]
            if gap < max_gap_days:
                cur.append(ep)
            else:
                cycles.append(_cycle_summary(cur))
                cur = [ep]
    if cur:
        cycles.append(_cycle_summary(cur))
    return cycles


def _cycle_summary(eps: list) -> dict:
    js = eps[0]["jd_start"]
    je = eps[-1]["jd_end"]
    span_days = je - js

    seen_signs: set = set()
    for ep in eps:
        ep["is_retrograde_return"] = ep["sign_num"] in seen_signs
        seen_signs.add(ep["sign_num"])

    return {
        "dt_start":         eps[0]["dt_start"],
        "dt_end":           eps[-1]["dt_end"],
        "duration_days":    round(span_days, 2),
        "duration_years":   round(span_days / 365.25, 3),
        "truncated_start":  eps[0]["truncated_start"],
        "truncated_end":    eps[-1]["truncated_end"],
        "episodes":         eps,
    }

# ═══════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════

def _add_years_safe(d: date, years: int) -> date:
    """date + years с защитой от 29 февраля."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=d.day - 1)


def calc_sade_sati(
        year: int, month: int, day: int,
        hour: int = 12, minute: int = 0,
        tz: float = 0.0, lat: float = 0.0, lon: float = 0.0,
        search_from: Optional[date] = None,
        search_to:   Optional[date] = None) -> dict:
    """Полный отчёт по Сади Сати + Аштама/Кантака Шани.

    По умолчанию ищет периоды от даты рождения до +120 лет.
    """
    birth_dt = datetime(year, month, day, hour, minute)
    jd_birth = dt_to_jd(birth_dt) - tz / 24.0

    natal = moon_natal(jd_birth, lat=lat, lon=lon)
    m = natal["sign_num"]

    # Знаки относительно натальной Луны
    sign_12 = ((m - 2) % 12) + 1   # 12-й (Aarohini)
    sign_1  = m                    # 1-й (Madhya / Janma)
    sign_2  = (m % 12) + 1         # 2-й (Avarohini)
    sign_4  = ((m - 1 + 3) % 12) + 1   # 4-й (Kantaka)
    sign_8  = ((m - 1 + 7) % 12) + 1   # 8-й (Ashtama)

    phase_signs = {
        sign_12: "Aarohini",
        sign_1:  "Madhya",
        sign_2:  "Avarohini",
    }

    birth_date = date(year, month, day)
    if search_from is None:
        search_from = birth_date
    if search_to is None:
        search_to = _add_years_safe(birth_date, 120)

    if search_to <= search_from:
        raise ValueError("search_to должна быть позже search_from")

    jd_s = dt_to_jd(datetime(search_from.year, search_from.month, search_from.day)) - tz / 24.0
    jd_e = dt_to_jd(datetime(search_to.year,   search_to.month,   search_to.day, 23, 59, 59)) - tz / 24.0

    transitions = find_saturn_transitions(jd_s, jd_e)

    sade_sati_eps = episodes_in_signs(jd_s, jd_e, transitions, phase_signs, tz)
    ashtama_eps   = episodes_in_signs(jd_s, jd_e, transitions, {sign_8: "Ashtama Shani"}, tz)
    kantaka_eps   = episodes_in_signs(jd_s, jd_e, transitions, {sign_4: "Kantaka Shani"}, tz)

    cycles = group_sade_sati_cycles(sade_sati_eps)

    jd_now = dt_to_jd(datetime.utcnow())
    current = _current_status(cycles, ashtama_eps, kantaka_eps, jd_now, tz)

    def _sign_info(n: int) -> dict:
        s = SIGNS[n - 1]
        return {"sign_num": n, "sign": s["name"], "sign_ru": s["ru"], "lord": s["lord"]}

    return {
        "input": {
            "date": f"{day:02d}/{month:02d}/{year}",
            "time": f"{hour:02d}:{minute:02d}",
            "tz": tz, "lat": lat, "lon": lon,
        },
        "search_range": {
            "from": search_from.isoformat(),
            "to":   search_to.isoformat(),
        },
        "natal_moon": natal,
        "phase_signs": {
            "aarohini":  {**_sign_info(sign_12), "house_from_moon": 12},
            "madhya":    {**_sign_info(sign_1),  "house_from_moon": 1},
            "avarohini": {**_sign_info(sign_2),  "house_from_moon": 2},
        },
        "ashtama_sign":          {**_sign_info(sign_8), "house_from_moon": 8},
        "kantaka_sign":          {**_sign_info(sign_4), "house_from_moon": 4},
        "sade_sati_cycles":      cycles,
        "ashtama_shani_periods": ashtama_eps,
        "kantaka_shani_periods": kantaka_eps,
        "current":               current,
        "method": "Swiss Ephemeris (DE431) + Lahiri ayanamsha",
    }


def _current_episode(eps: list, jd_now: float, tz: float) -> Optional[dict]:
    for ep in eps:
        if ep["jd_start"] <= jd_now < ep["jd_end"]:
            total = ep["jd_end"] - ep["jd_start"]
            done  = jd_now - ep["jd_start"]
            return {
                "phase":                ep.get("phase"),
                "sign":                 ep["sign"],
                "sign_ru":              ep["sign_ru"],
                "sign_num":             ep["sign_num"],
                "dt_start":             ep["dt_start"],
                "dt_end":               ep["dt_end"],
                "days_remaining":       round(ep["jd_end"] - jd_now, 1),
                "days_elapsed":         round(done, 1),
                "progress":             round(done / total, 3) if total > 0 else 0,
                "is_retrograde_return": ep.get("is_retrograde_return", False),
            }
    return None


def _current_status(cycles: list, ashtama: list, kantaka: list,
                    jd_now: float, tz: float) -> dict:
    sade = None
    cycle_info = None
    for c in cycles:
        ep = _current_episode(c["episodes"], jd_now, tz)
        if ep:
            sade = ep
            cycle_total = c["jd_end"] if "jd_end" in c else c["episodes"][-1]["jd_end"]
            cycle_start = c["episodes"][0]["jd_start"]
            cycle_info = {
                "dt_start":       c["dt_start"],
                "dt_end":         c["dt_end"],
                "duration_years": c["duration_years"],
                "days_remaining": round(c["episodes"][-1]["jd_end"] - jd_now, 1),
            }
            break

    return {
        "as_of":         jd_to_local(jd_now, tz),
        "sade_sati":     sade,
        "sade_sati_cycle": cycle_info,
        "ashtama_shani": _current_episode(ashtama, jd_now, tz),
        "kantaka_shani": _current_episode(kantaka, jd_now, tz),
    }

# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

def print_result(res: dict) -> None:
    W = 72
    print("\n" + "═" * W)
    print("  САДИ САТИ — отчёт по транзитам Сатурна")
    print("═" * W)
    n = res["natal_moon"]
    print(f"  Рождение : {res['input']['date']} {res['input']['time']}  UTC{res['input']['tz']:+g}")
    print(f"  Луна     : {n['sign_ru']} ({n['sign']}) {n['deg_in_sign_dms']}  |  "
          f"накшатра {n['nakshatra_ru']} (пада {n['pada']})")
    p = res["phase_signs"]
    print(f"  Фазы СС  : {p['aarohini']['sign_ru']} → {p['madhya']['sign_ru']} → {p['avarohini']['sign_ru']}")
    print(f"  Аштама   : {res['ashtama_sign']['sign_ru']}    Кантака: {res['kantaka_sign']['sign_ru']}")
    print(f"  Окно     : {res['search_range']['from']} … {res['search_range']['to']}")
    print()

    for i, c in enumerate(res["sade_sati_cycles"], 1):
        print("─" * W)
        flag = ""
        if c["truncated_start"]: flag += "  (начало вне окна)"
        if c["truncated_end"]:   flag += "  (конец вне окна)"
        print(f"  ЦИКЛ #{i}: {c['dt_start']:%Y-%m-%d} → {c['dt_end']:%Y-%m-%d}   "
              f"({c['duration_years']} лет){flag}")
        for ep in c["episodes"]:
            print(f"    [{ep['phase']:<10}] {ep['sign_ru']:<10} "
                  f"{ep['dt_start']:%Y-%m-%d %H:%M} → {ep['dt_end']:%Y-%m-%d %H:%M}  "
                  f"({ep['duration_days']:.0f} дн)")
        print()

    if res["ashtama_shani_periods"]:
        print("─" * W)
        print(f"  АШТАМА ШАНИ ({res['ashtama_sign']['sign_ru']})")
        for ep in res["ashtama_shani_periods"]:
            print(f"    {ep['dt_start']:%Y-%m-%d} → {ep['dt_end']:%Y-%m-%d}   ({ep['duration_days']:.0f} дн)")
        print()

    if res["kantaka_shani_periods"]:
        print("─" * W)
        print(f"  КАНТАКА ШАНИ ({res['kantaka_sign']['sign_ru']})")
        for ep in res["kantaka_shani_periods"]:
            print(f"    {ep['dt_start']:%Y-%m-%d} → {ep['dt_end']:%Y-%m-%d}   ({ep['duration_days']:.0f} дн)")
        print()
    print("═" * W + "\n")


if __name__ == "__main__":
    if len(sys.argv) >= 8 and sys.argv[1] == "--period":
        y, mo, d, h, mi = map(int, sys.argv[2:7])
        tz = float(sys.argv[7])
        lat = float(sys.argv[8]) if len(sys.argv) > 8 else 0.0
        lon = float(sys.argv[9]) if len(sys.argv) > 9 else 0.0
        res = calc_sade_sati(y, mo, d, h, mi, tz, lat, lon)
        print_result(res)
    else:
        print("  python sade_sati.py --period ГОД МЕС ДЕНЬ ЧАС МИН TZ [LAT LON]")
