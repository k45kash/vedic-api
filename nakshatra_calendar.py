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

import sys
import os
from datetime import datetime, date

import swisseph as swe

from utils import dt_to_jd, jd_to_local, _bisect, dms, NAKSHATRAS

EPHE_PATH = os.environ.get(
    "SE_EPHE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
)
swe.set_ephe_path(EPHE_PATH)
swe.set_sid_mode(swe.SIDM_LAHIRI)   # начальный режим; get_ayanamsha() переустанавливает при каждом вызове

# ═══════════════════════════════════════════════════════════
#  СПРАВОЧНИК НАКШАТР
# ═══════════════════════════════════════════════════════════

NK_SIZE   = 360.0 / 27      # 13.3333…°
PADA_SIZE = NK_SIZE / 4     #  3.3333…°

# ═══════════════════════════════════════════════════════════
#  УТИЛИТЫ ВРЕМЕНИ
# ═══════════════════════════════════════════════════════════

def fmt_duration(hours: float) -> str:
    h = int(hours); m = int((hours - h) * 60)
    return f"{h}ч {m:02d}м"

def fmt_range(dt_s: datetime, dt_e: datetime):
    """'дата? время → дата? время' — дата у конца только если другой день."""
    s = dt_s.strftime("%d.%m.%Y %H:%M:%S")
    same_day = dt_s.date() == dt_e.date()
    e = dt_e.strftime("%H:%M:%S") if same_day else dt_e.strftime("%d.%m.%Y %H:%M:%S")
    return s, e

# ═══════════════════════════════════════════════════════════
#  АЯНАМША И ЛУНА
# ═══════════════════════════════════════════════════════════

def get_ayanamsha(jd: float) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa_ut(jd)


def moon_sid(jd: float, topo: bool = False, lat: float = 0.0, lon: float = 0.0) -> float:
    """Сидерическая долгота Луны (0-360°). topo=True — топоцентрическая."""
    aya = get_ayanamsha(jd)
    fl = swe.FLG_SWIEPH
    if topo and (lat != 0.0 or lon != 0.0):
        swe.set_topo(lon, lat, 0)
        fl |= swe.FLG_TOPOCTR
    pos, _ = swe.calc_ut(jd, swe.MOON, fl)
    return (pos[0] - aya) % 360


def nk_idx(jd: float, lat: float = 0.0, lon: float = 0.0) -> int:
    return int(moon_sid(jd, lat=lat, lon=lon) / NK_SIZE) % 27


def pada_idx(jd: float, lat: float = 0.0, lon: float = 0.0) -> int:
    return int((moon_sid(jd, lat=lat, lon=lon) % NK_SIZE) / PADA_SIZE)


def boundary_flag(moon_lon: float, moon_speed_dpd: float = 13.2) -> str:
    """Предупреждение если Луна входит в паду уже близко к её концу (< 30 мин)."""
    pos_in_pada = moon_lon % PADA_SIZE
    dist_to_end = PADA_SIZE - pos_in_pada
    margin_min  = dist_to_end / (moon_speed_dpd / (24 * 60))
    if margin_min < 10:
        return f"  ⚠ пада заканчивается через {margin_min:.0f} мин"
    if margin_min < 30:
        return f"  ! короткая пада ({margin_min:.0f} мин)"
    return ""

# ═══════════════════════════════════════════════════════════
#  РАСЧЁТ: накшатры + пады за период
# ═══════════════════════════════════════════════════════════

def calc_calendar(
        date_start: date, date_end: date,
        tz: float, lat: float = 0.0, lon: float = 0.0,
        step_h: float = 1.0, prec_sec: float = 1.0,
) -> list:
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
    jd_s = dt_to_jd(datetime(date_start.year, date_start.month, date_start.day))         - tz/24
    jd_e = dt_to_jd(datetime(date_end.year,   date_end.month,   date_end.day, 23, 59, 59)) - tz/24

    step     = step_h / 24.0
    use_topo = lat != 0.0 or lon != 0.0

    _nk  = lambda jd: nk_idx(jd,  lat, lon)
    _pd  = lambda jd: pada_idx(jd, lat, lon)
    _sid = lambda jd: moon_sid(jd, topo=use_topo, lat=lat, lon=lon)

    # ── 1. Находим все переходы накшатр ──────────────────
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
            # jd_nx < ne: переход точно в ne — это граница накшатры, не пады
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
            padas.append({
                "pada":       _pd(ps) + 1,
                "jd_start":   ps, "jd_end":   pe,
                "dt_start":   jd_to_local(ps, tz),
                "dt_end":     jd_to_local(pe, tz),
                "moon_start": _sid(ps),
                "moon_end":   _sid(pe),
                "duration_h": (pe - ps) * 24,
                "boundary":   boundary_flag(_sid(ps)),
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

def print_calendar(entries: list, date_start: date, date_end: date,
                   tz: float, lat: float, lon: float):
    """Накшатры + пады с временем и позицией Луны."""
    W = 68
    tz_str   = f"UTC{'+' if tz >= 0 else ''}{tz:g}"
    topo_str = "топоцентр" if (lat != 0.0 or lon != 0.0) else "геоцентр"
    print("\n" + "═" * W)
    print("  КАЛЕНДАРЬ НАКШАТР ЛУНЫ")
    print("═" * W)
    print(f"  Период  : {date_start.strftime('%d.%m.%Y')} — {date_end.strftime('%d.%m.%Y')}")
    print(f"  Часовой : {tz_str}  |  lat {lat}°  lon {lon}°")
    print(f"  Метод   : Swiss Ephemeris (DE431, ~0.001\")")
    print(f"  Позиция : {topo_str}  |  Аянамша: Лахири  |  Точность: ±1 сек")
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
    return d_s, d_e, tz, lat, lon

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
                print_calendar(entries, ex["start"], ex["end"], ex["tz"], ex["lat"], ex["lon"])

        elif cmd == "--period" and len(sys.argv) >= 7:
            d_s  = parse_date(sys.argv[2])
            d_e  = parse_date(sys.argv[3])
            tz   = float(sys.argv[4])
            lat  = float(sys.argv[5])
            lon  = float(sys.argv[6])
            entries = calc_calendar(d_s, d_e, tz, lat, lon)
            print_calendar(entries, d_s, d_e, tz, lat, lon)

        else:
            print("Использование:")
            print("  python nakshatra_calendar.py")
            print("  python nakshatra_calendar.py --examples")
            print("  python nakshatra_calendar.py --period ГГГГ-ММ-ДД ГГГГ-ММ-ДД TZ LAT LON")
    else:
        try:
            d_s, d_e, tz, lat, lon = get_input()
            print("\n  Вычисляю...")
            entries = calc_calendar(d_s, d_e, tz, lat, lon)
            print_calendar(entries, d_s, d_e, tz, lat, lon)
        except KeyboardInterrupt:
            print("\n\nВыход.")
