"""
╔══════════════════════════════════════════════════════════════════════╗
║   ВЕДИЧЕСКАЯ АСТРОЛОГИЯ — Накшатра, Лагна, 12 Домов, Планеты        ║
║   Swiss Ephemeris (pyswisseph)                                       ║
╚══════════════════════════════════════════════════════════════════════╝

Установка:  pip install pyswisseph

Запуск:
  python nakshatra_calculator.py                   — интерактивный ввод
  python nakshatra_calculator.py --examples        — 3 примера
  python nakshatra_calculator.py --my-chart        — персональный гороскоп
  python nakshatra_calculator.py --test-boundary   — тест граничного случая
"""

import sys
import os
from datetime import datetime

import swisseph as swe

from utils import dt_to_jd, jd_to_local, dms, dms_sign, NAKSHATRAS

# ephe/ лежит рядом со скриптом; SE_EPHE_PATH переопределяет если нужно
EPHE_PATH = os.environ.get(
    "SE_EPHE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
)
swe.set_ephe_path(EPHE_PATH)
swe.set_sid_mode(swe.SIDM_LAHIRI)   # начальный режим; get_aya() переустанавливает его при каждом вызове

# ═══════════════════════════════════════════════════════════
#  СПРАВОЧНЫЕ ДАННЫЕ
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

HOUSE_MEANINGS = {
    1: "Личность, тело, внешность",
    2: "Богатство, семья, речь",
    3: "Братья/сёстры, смелость",
    4: "Мать, дом, недвижимость",
    5: "Дети, творчество, интеллект",
    6: "Враги, болезни, долги",
    7: "Партнёрство, брак, бизнес",
    8: "Трансформация, тайны",
    9: "Dharma, удача, гуру",
    10: "Карьера, статус, отец",
    11: "Прибыль, желания, друзья",
    12: "Потери, moksha, заграница",
}

PLANETS = [
    {"name": "Солнце",   "en": "Sun",     "abbr": "☉"},
    {"name": "Луна",     "en": "Moon",    "abbr": "☽"},
    {"name": "Марс",     "en": "Mars",    "abbr": "♂"},
    {"name": "Меркурий", "en": "Mercury", "abbr": "☿"},
    {"name": "Юпитер",   "en": "Jupiter", "abbr": "♃"},
    {"name": "Венера",   "en": "Venus",   "abbr": "♀"},
    {"name": "Сатурн",   "en": "Saturn",  "abbr": "♄"},
    {"name": "Раху",     "en": "Rahu",    "abbr": "☊"},
    {"name": "Кету",     "en": "Ketu",    "abbr": "☋"},
]

NK_SIZE = 360 / 27
# Порог предупреждения о близости к границе накшатры.
# Скорость Луны ≈ 13.2°/сут = 0.009°/мин → 0.25° ≈ 27 минут хода.
# 1.0° давало бы предупреждение за ~108 минут — слишком широко.
BOUNDARY_WARN = 0.25

# ═══════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ═══════════════════════════════════════════════════════════

def to_jd(dt: datetime, tz: float) -> float:
    """Local datetime + timezone → Julian Day (UTC)."""
    return dt_to_jd(dt) - tz / 24


def lon_to_sign(lon: float):
    lon = lon % 360
    return int(lon / 30) + 1, lon % 30


# ═══════════════════════════════════════════════════════════
#  АЯНАМША
# ═══════════════════════════════════════════════════════════

def get_aya(jd: float, mode=None) -> float:
    swe.set_sid_mode(mode if mode is not None else swe.SIDM_LAHIRI)
    return swe.get_ayanamsa_ut(jd)   # _ut принимает UT напрямую, без ΔT

# ═══════════════════════════════════════════════════════════
#  ЛУНА (тропическая, геоцентр / топоцентр)
# ═══════════════════════════════════════════════════════════

def moon_trop(jd: float, topo: bool = False, lat: float = 0, lon: float = 0) -> float:
    fl = swe.FLG_SWIEPH
    if topo:
        swe.set_topo(lon, lat, 0)
        fl |= swe.FLG_TOPOCTR
    pos, _ = swe.calc_ut(jd, swe.MOON, fl)
    return pos[0]

# ═══════════════════════════════════════════════════════════
#  ПЛАНЕТЫ
# ═══════════════════════════════════════════════════════════

def _planet_trop_swe(jd: float, planet_idx: int) -> float:
    """Тропическая долгота планеты через SWE.

    Раху/Кету: используем TRUE_NODE (истинный узел).
    Кету = Раху + 180°.
    """
    swe_ids = [swe.SUN, swe.MOON, swe.MARS, swe.MERCURY,
               swe.JUPITER, swe.VENUS, swe.SATURN,
               swe.TRUE_NODE, swe.TRUE_NODE]
    pos, _ = swe.calc_ut(jd, swe_ids[planet_idx], swe.FLG_SWIEPH)
    lon = pos[0]
    if planet_idx == 8:   # Кету = Раху + 180°
        lon = (lon + 180.0) % 360
    return lon


def get_planet_positions(jd: float, aya: float) -> list:
    """Возвращает список планет с тропическими/сидерическими координатами,
    накшатрой, падой и знаком.
    """
    result = []
    for idx, p in enumerate(PLANETS):
        try:
            trop = _planet_trop_swe(jd, idx)
        except Exception as e:
            raise RuntimeError(f"SWE ошибка для {p['name']}: {e}") from e

        sid = (trop - aya) % 360
        sn, deg_in_sign = lon_to_sign(sid)
        nk = get_nk(sid)
        result.append({
            "idx":              idx,
            "name":             p["name"],
            "abbr":             p["abbr"],
            "available":        True,
            "trop":             round(trop, 6),
            "sid":              round(sid, 6),
            "sid_dms":          dms(sid),
            "sign_num":         sn,
            "sign":             SIGNS[sn-1]["name"],
            "sign_ru":          SIGNS[sn-1]["ru"],
            "deg_in_sign":      round(deg_in_sign, 6),
            "deg_in_sign_dms":  dms_sign(deg_in_sign),
            "nakshatra":        nk["name"],
            "nakshatra_ru":     nk["ru"],
            "pada":             nk["pada"],
            "nk_lord":          nk["lord"],
        })
    return result

# ═══════════════════════════════════════════════════════════
#  НАКШАТРА
# ═══════════════════════════════════════════════════════════

def get_nk(sid: float) -> dict:
    idx  = int(sid / NK_SIZE) % 27
    pada = int((sid % NK_SIZE) / (NK_SIZE / 4)) + 1
    deg  = sid % NK_SIZE
    n    = NAKSHATRAS[idx]
    return {**n, "pada": pada, "degrees_in_nakshatra": round(deg, 6)}

# ═══════════════════════════════════════════════════════════
#  ДИАГНОСТИКА ГРАНИЦЫ
# ═══════════════════════════════════════════════════════════

def check_boundary(jd: float, trop: float, aya: float, lat: float, lon: float) -> dict:
    sid  = (trop - aya) % 360
    pos  = sid % NK_SIZE
    dist = min(pos, NK_SIZE - pos)
    res  = {"dist_deg": round(dist, 4), "dist_arcsec": round(dist * 3600, 1),
            "is_boundary": dist < BOUNDARY_WARN, "topo": None, "aya_compare": {}}
    if not res["is_boundary"]:
        return res
    t_topo = moon_trop(jd, True, lat, lon)
    sid_t  = (t_topo - aya) % 360
    res["topo"] = {
        "delta_arcsec": round((sid_t - sid) * 3600, 2),
        "nk_geo":  get_nk(sid)["name"],
        "nk_topo": get_nk(sid_t)["name"],
        "changes": get_nk(sid)["num"] != get_nk(sid_t)["num"],
    }
    modes = {
        "Lahiri":     (swe.SIDM_LAHIRI,        "Лахири"),
        "KP":         (swe.SIDM_KRISHNAMURTI,  "Кришнамурти"),
        "TrueChitra": (swe.SIDM_TRUE_CITRA,    "True Chitra"),
    }
    for nm, (mode, lbl) in modes.items():
        a  = get_aya(jd, mode)
        s  = (trop - a) % 360
        nk = get_nk(s)
        res["aya_compare"][nm] = {"label": lbl, "aya": round(a, 4),
                                  "nk": nk["name"], "pada": nk["pada"]}
    swe.set_sid_mode(swe.SIDM_LAHIRI)   # восстанавливаем после сравнения аянамш
    res["ayas_agree"] = len(set(v["nk"] for v in res["aya_compare"].values())) == 1
    return res

# ═══════════════════════════════════════════════════════════
#  ЛАГНА И ДОМА
# ═══════════════════════════════════════════════════════════

def get_lagna(jd: float, lat: float, lon: float, aya: float) -> dict:
    _, ascmc = swe.houses(jd, lat, lon, b'W')
    trop = ascmc[0]
    sid = (trop - aya) % 360
    sn, deg = lon_to_sign(sid)

    houses = []
    for i in range(12):
        n  = ((sn - 1 + i) % 12) + 1
        sg = SIGNS[n - 1]
        houses.append({"house": i+1, "sign_num": n,
                        "sign": sg["name"], "sign_ru": sg["ru"],
                        "lord": sg["lord"], "meaning": HOUSE_MEANINGS[i+1]})
    return {
        "trop_asc":        round(trop, 6),
        "sid_asc":         round(sid, 6),
        "asc_dms":         dms(sid),
        "sign_num":        sn,
        "sign":            SIGNS[sn-1]["name"],
        "sign_ru":         SIGNS[sn-1]["ru"],
        "lord":            SIGNS[sn-1]["lord"],
        "element":         SIGNS[sn-1]["element"],
        "deg_in_sign":     round(deg, 6),
        "deg_in_sign_dms": dms_sign(deg),
        "houses":          houses,
    }

# ═══════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════

def calculate(year, month, day, hour, minute, tz, lat, lon):
    dt   = datetime(year, month, day, hour, minute)
    jd   = to_jd(dt, tz)
    aya  = get_aya(jd)

    trop = moon_trop(jd)
    sid  = (trop - aya) % 360
    nk   = get_nk(sid)

    lg      = get_lagna(jd, lat, lon, aya)
    bd      = check_boundary(jd, trop, aya, lat, lon)
    planets = get_planet_positions(jd, aya)

    # Определяем дом для каждой планеты (Whole Sign)
    lagna_sign = lg["sign_num"]
    for p in planets:
        p["house"] = ((p["sign_num"] - lagna_sign) % 12) + 1

    return {
        "input":   {"date": f"{day:02d}/{month:02d}/{year}",
                    "time": f"{hour:02d}:{minute:02d}",
                    "tz": tz, "lat": lat, "lon": lon},
        "jd":          round(jd, 6),
        "aya":         round(aya, 4),
        "moon_trop":   round(trop, 4),
        "moon_sid":    round(sid, 4),
        "moon_dms":    dms(sid),
        "method":      "Swiss Ephemeris (файлы DE431, ~0.001\")",
        "nk":          nk,
        "lagna":       lg,
        "boundary":    bd,
        "planets":     planets,
    }

# ═══════════════════════════════════════════════════════════
#  ВЫВОД РЕЗУЛЬТАТА
# ═══════════════════════════════════════════════════════════

def print_result(res):
    W = 68

    def row(l, v, w=26):
        print(f"  {l:<{w}}: {v}")

    print("\n" + "═" * W)
    print("  🌙  ВЕДИЧЕСКАЯ АСТРОЛОГИЯ")
    print("═" * W)
    i = res["input"]
    row("Дата", f"{i['date']}  {i['time']}")
    row("UTC", f"+{i['tz']}  |  lat {i['lat']}°  lon {i['lon']}°")
    row("Метод", res["method"])

    # ── Луна ──────────────────────────────────────────────
    print(f"\n  ── ЛУНА ──────────────────────────────────────────────────")
    row("Julian Day",        res["jd"])
    row("Аянамша Лахири",    dms(res["aya"]))
    row("Луна тропическая",  dms(res["moon_trop"]))
    row("Луна сидерическая", res["moon_dms"])

    # ── Накшатра Луны ─────────────────────────────────────
    n = res["nk"]
    print(f"\n  ── НАКШАТРА ЛУНЫ ─────────────────────────────────────────")
    row("Накшатра",      f"#{n['num']}  {n['name']}  ({n['ru']})")
    row("Пада",          f"{n['pada']} / 4")
    row("Владелец",      n["lord"])
    row("Символ",        n["symbol"])
    row("Гана",          n["gana"])
    row("Внутри накшатры", f"{n['degrees_in_nakshatra']:.4f}°  ({n['degrees_in_nakshatra']*3600:.0f}\")")

    # ── Диагностика границы ───────────────────────────────
    b = res["boundary"]
    if b["is_boundary"]:
        print(f"\n  ⚠  ЛУНА У ГРАНИЦЫ НАКШАТРЫ")
        row("До границы", f"{b['dist_deg']:.4f}°  ({b['dist_arcsec']:.0f}\")")
        if b.get("topo"):
            t   = b["topo"]
            chg = "❌ МЕНЯЕТСЯ!" if t["changes"] else "✅ та же"
            print(f"  Топоцентр ({t['delta_arcsec']:+.1f}\"): {t['nk_geo']} → {t['nk_topo']}  [{chg}]")
        if b.get("aya_compare"):
            ag = "✅ OK" if b.get("ayas_agree") else "❌ РАСХОЖДЕНИЕ"
            print(f"  Аянамши [{ag}]:")
            for nm, v in b["aya_compare"].items():
                print(f"    {nm:<12}: {v['nk']} пада {v['pada']}")
        print(f"  ➜ Уточни время рождения (1 мин ≈ 0.5' Луны)")
    else:
        pct = b["dist_deg"] / NK_SIZE * 100
        print(f"\n  ✅ Луна устойчиво в накшатре  ({b['dist_deg']:.3f}° = {pct:.1f}% до границы)")

    # ── Лагна ─────────────────────────────────────────────
    lg = res["lagna"]
    print(f"\n  ── ЛАГНА (АСЦЕНДЕНТ) ─────────────────────────────────────")
    row("Лагна сидерическая", lg["asc_dms"])
    row("Знак Лагны",   f"#{lg['sign_num']}  {lg['sign']}  ({lg['sign_ru']})")
    row("Владелец",     lg["lord"])
    row("Стихия",       lg["element"])
    row("Градусов в знаке", lg["deg_in_sign_dms"])

    # ── Планеты ───────────────────────────────────────────
    print(f"\n  ── ПЛАНЕТЫ ────────────────────────────────────────────────────")
    hdr = f"  {'Планета':<12}{'Знак':<13}{'Градус':<12}{'Дом':<5}{'Накшатра':<18}{'Пада':<6}Владелец накш."
    print(hdr)
    print("  " + "─" * 72)
    for p in res["planets"]:
        print(f"  {p['abbr']+' '+p['name']:<12}"
              f"{p['sign_ru']:<13}"
              f"{p['deg_in_sign_dms']:<12}"
              f"{p['house']:<5}"
              f"{p['nakshatra_ru']:<18}"
              f"{p['pada']:<6}"
              f"{p['nk_lord']}")

    # ── 12 Домов ─────────────────────────────────────────
    print(f"\n  ── 12 ДОМОВ (Whole Sign) ─────────────────────────────────")
    house_planets = {}
    for p in res["planets"]:
        house_planets.setdefault(p["house"], []).append(p["abbr"] + p["name"])

    print(f"  {'Дом':<5}{'Знак':<13}{'Владелец':<11}{'Планеты':<20}Значение")
    print("  " + "─" * (W - 2))
    for h in lg["houses"]:
        pl = ", ".join(house_planets.get(h["house"], [])) or "—"
        print(f"  {h['house']:<5}{h['sign_ru']:<13}{h['lord']:<11}{pl:<20}{h['meaning']}")

    print("═" * W + "\n")

# ═══════════════════════════════════════════════════════════
#  ИНТЕРАКТИВНЫЙ ВВОД
# ═══════════════════════════════════════════════════════════

def ask(p, cast, err):
    while True:
        try:
            return cast(input(p).strip())
        except Exception:
            print(f"  Ошибка: {err}")

# ═══════════════════════════════════════════════════════════
#  ПРИМЕРЫ
# ═══════════════════════════════════════════════════════════

EXAMPLES = [
    {"name": "Москва    15.05.1990 14:30", "p": (1990,  5, 15, 14, 30,  3.0,  55.75,  37.62)},
    {"name": "Мумбаи    01.11.1985 08:00", "p": (1985, 11,  1,  8,  0,  5.5,  19.08,  72.88)},
    {"name": "Нью-Йорк  21.03.2000 12:00", "p": (2000,  3, 21, 12,  0, -5.0,  40.71, -74.01)},
]

MY_CHART = {
    # Ставрополь, июль 1990 — летнее время СССР: MSK стандарт UTC+3,
    # но действовало летнее время → UTC+4
    "name": "Ставрополь  11.07.1990 13:45  (UTC+4, летнее время)",
    "p":    (1990, 7, 11, 13, 45, 4.0, 45.043317, 41.969110),
}

BOUNDARY_EX = {
    "name": "Тест граничного случая",
    "p":    (1990, 7, 11, 10, 0, 0.0, 45.04, 41.97),
}

# ═══════════════════════════════════════════════════════════
#  ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--examples":
            for ex in EXAMPLES:
                print(f"\n{'─'*68}\n  📍 {ex['name']}")
                print_result(calculate(*ex["p"]))
        elif cmd == "--my-chart":
            ex = MY_CHART
            print(f"\n{'─'*68}\n  📍 {ex['name']}")
            print_result(calculate(*ex["p"]))
        elif cmd == "--test-boundary":
            ex = BOUNDARY_EX
            print(f"\n{'─'*68}\n  🔍 {ex['name']}")
            print_result(calculate(*ex["p"]))
        else:
            print("Аргументы: --examples  |  --my-chart  |  --test-boundary")
    else:
        try:
            print("\n🌙  Ведическая астрология — Накшатра + Планеты + Дома")
            print("─" * 56)
            raw = ask("Дата (ДД/ММ/ГГГГ): ",
                      lambda s: tuple(map(int, s.split("/"))), "ДД/ММ/ГГГГ")
            d, mo, y = raw
            t = ask("Время (ЧЧ:ММ): ",
                    lambda s: tuple(map(int, s.split(":"))), "ЧЧ:ММ")
            h, mi = t
            tz  = ask("UTC+?: ", float, "число")
            lat = ask("Широта:  ", float, "число")
            lon = ask("Долгота: ", float, "число")
            print_result(calculate(y, mo, d, h, mi, tz, lat, lon))
        except KeyboardInterrupt:
            print("\nВыход.")
