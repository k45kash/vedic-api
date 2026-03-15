"""
Верификация Swiss Ephemeris — проверяет что файловые эфемериды
подключены и дают результаты, совпадающие с JHora/Kala.

Тест-кейс: 11.07.1990 13:45 UTC+4 (= 09:45 UTC), Ставрополь.
Эталон: данные JHora (Image 2 из сессии сравнения).

Запуск:  python swe_verify.py
"""

import os, sys

try:
    import swisseph as swe
except ImportError:
    print("ОШИБКА: pyswisseph не установлен  →  pip install pyswisseph")
    sys.exit(1)

EPHE_PATH = os.environ.get(
    "SE_EPHE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
)
swe.set_ephe_path(EPHE_PATH)
swe.set_sid_mode(swe.SIDM_LAHIRI)

W = 70
JD_TEST = 2448083.90625   # 11.07.1990 09:45 UTC

# ═══════════════════════════════════════════════════════════
#  Эталон: JHora (сидерические градусы внутри знака, Лахири)
#  Источник: скриншот Image 2 из сессии сравнения
# ═══════════════════════════════════════════════════════════
def dms_to_deg(d, m, s=0):
    return d + m / 60 + s / 3600

JHORA_SID_IN_SIGN = {
    #           градус в знаке  накшатра        пада
    "Солнце":   (dms_to_deg(25,  7,  9), "Пунарвасу",       2),
    "Луна":     (dms_to_deg( 4, 14, 46), "Дхаништха",       4),
    "Марс":     (dms_to_deg( 5, 27, 14), "Ашвини",          2),
    "Меркурий": (dms_to_deg( 5,  7, 11), "Пушья",           1),
    "Юпитер":   (dms_to_deg(27, 54, 36), "Пунарвасу",       3),
    "Венера":   (dms_to_deg(25, 47, 23), "Мригашира",       1),
    "Сатурн":   (dms_to_deg(28, 32,  2), "Уттарашадха",     1),
    "Раху":     (dms_to_deg(13, 34,  1), "Шравана",         2),
    "Кету":     (dms_to_deg(13, 34,  1), "Пушья",           4),
}

PLANETS = [
    (swe.SUN,       "Солнце"),
    (swe.MOON,      "Луна"),
    (swe.MARS,      "Марс"),
    (swe.MERCURY,   "Меркурий"),
    (swe.JUPITER,   "Юпитер"),
    (swe.VENUS,     "Венера"),
    (swe.SATURN,    "Сатурн"),
    (swe.TRUE_NODE, "Раху"),
    (swe.TRUE_NODE, "Кету"),
]

NAKSHATRAS = ["Ашвини","Бхарани","Криттика","Рохини","Мригашира","Ардра",
              "Пунарвасу","Пушья","Ашлеша","Магха","Пурва Пхалгуни",
              "Уттара Пхалгуни","Хаста","Читра","Свати","Вишакха","Анурадха",
              "Джьештха","Мула","Пурвашадха","Уттарашадха","Шравана",
              "Дхаништха","Шатабхиша","Пурвабхадра","Уттарабхадра","Ревати"]

NK_SIZE   = 360 / 27
PADA_SIZE = NK_SIZE / 4

def fmt_dms(deg_in_sign):
    d = int(deg_in_sign)
    mf = (deg_in_sign - d) * 60; m = int(mf)
    s = (mf - m) * 60
    return f"{d}°{m:02d}'{s:04.1f}\""

def get_nk(sid):
    idx  = int(sid / NK_SIZE) % 27
    pada = int((sid % NK_SIZE) / PADA_SIZE) + 1
    return NAKSHATRAS[idx], pada

# ── Режим ──────────────────────────────────────────────────
_, probe_ret = swe.calc_ut(JD_TEST, swe.MOON, swe.FLG_SWIEPH)
swiss_active = bool(probe_ret & swe.FLG_SWIEPH)

print("\n" + "═" * W)
print("  Swiss Ephemeris — верификация")
print("═" * W)
print(f"  Путь эфемерид : {EPHE_PATH}")
print(f"  Режим         : {'✅ Swiss (DE431/DE441)' if swiss_active else '❌ Moshier — файлы .se1 не найдены!'}")
print(f"  Тест-кейс     : 11.07.1990 13:45 UTC+4  |  JD {JD_TEST}")
print(f"  Эталон        : JHora (сидерические долготы, аянамша Лахири)")

# ── Аянамша ────────────────────────────────────────────────
aya = swe.get_ayanamsa_ut(JD_TEST)
aya_ref = 23.722  # JHora эталон
aya_err_arcsec = (aya - aya_ref) * 3600
print(f"\n  Аянамша Лахири: {fmt_dms(aya)}  (JHora ≈ {fmt_dms(aya_ref)},  Δ = {aya_err_arcsec:+.1f}\")")

# ── Таблица планет ─────────────────────────────────────────
print()
print(f"  {'Планета':<11} {'Наш (°в знаке)':<17} {'JHora (°в знаке)':<18} {'Δ (\")':<8} {'Накшатра':<16} Пада  OK?")
print("  " + "─" * (W - 2))

all_ok = True
for i, (pid, name) in enumerate(PLANETS):
    pos, ret = swe.calc_ut(JD_TEST, pid, swe.FLG_SWIEPH)
    trop = pos[0]
    if name == "Кету":
        trop = (trop + 180.0) % 360
    sid = (trop - aya) % 360
    deg_in_sign = sid % 30
    nk_name, pada = get_nk(sid)

    ref = JHORA_SID_IN_SIGN.get(name)
    if ref:
        ref_deg, ref_nk, ref_pada = ref
        delta_arcsec = (deg_in_sign - ref_deg) * 3600
        nk_ok  = nk_name == ref_nk
        pada_ok = pada == ref_pada
        mark = "✅" if abs(delta_arcsec) < 60 and nk_ok and pada_ok else "❌"
        if mark == "❌":
            all_ok = False
        ref_str = fmt_dms(ref_deg)
        delta_str = f"{delta_arcsec:+.1f}\""
    else:
        ref_str = "—"; delta_str = "—"; mark = "  "

    print(f"  {name:<11} {fmt_dms(deg_in_sign):<17} {ref_str:<18} {delta_str:<8} {nk_name:<16} {pada}     {mark}")

# ── Итог ───────────────────────────────────────────────────
print()
print("═" * W)
if not swiss_active:
    print("  ❌ Файловые эфемериды не подключены")
    print(f"     Проверь папку: {EPHE_PATH}")
    print("     Нужны файлы: semo_18.se1 (Луна) + sepl_18.se1 (планеты)")
    print("     Скачать: https://www.astro.com/ftp/swisseph/ephe/")
elif all_ok:
    print("  ✅ Все планеты совпадают с JHora в пределах 60\"")
    print("     Swiss Ephemeris работает корректно")
else:
    print("  ⚠  Некоторые позиции расходятся с эталоном > 60\"")
    print("     Возможные причины:")
    print("     — Неполный набор .se1 файлов (нужны semo_18 + sepl_18)")
    print("     — Разные версии аянамши в настройках")
print("═" * W + "\n")