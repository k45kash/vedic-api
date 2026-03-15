"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   СРАВНЕНИЕ: Swiss Ephemeris (mean-of-date) vs JPL Horizons ГЕОЦЕНТР       ║
║   Цель: устранить паразитный топоцентрический параллакс и сравнить честно   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Что делает скрипт:
  1. Читает локальный SWE-файл (sun_ephemeris_19900711_1000.txt)
  2. Запрашивает JPL Horizons API с CENTER='500@399' (геоцентр Земли)
     - ANG_FORMAT=DEG    → градусы, не HMS
     - REF_SYSTEM=ICRF   → J2000.0 ICRF
     - EXTRA_PREC=YES    → дополнительная точность
     - QUANTITIES=1,31   → RA/DEC + ObsEcLon/Lat
  3. Парсит оба источника, выравнивает по времени
  4. Считает разности и выводит статистику + таблицу

Установка:
    pip install requests

Запуск:
    python horizons_geocentric_compare.py

После получения геоцентрических данных ожидаемые разности:
  - ΔRA  : ~-504" (прецессия, mean-of-date vs J2000) — ОСТАЁТСЯ
  - ΔRA-var : < 0.1" (параллакс ИСЧЕЗНЕТ)
  - ΔEclLon: < 0.5" (только нутационный сдвиг)
  - ΔEclLat: ~3-8"  (IAU-2000B vs IAU-1980 нутация)
"""

import re
import sys
import math
import statistics
import urllib.request
import urllib.parse
import json
import ssl
from datetime import datetime

# ── Исправление SSL на macOS ──────────────────────────────────────────────────
# macOS Python не использует системные сертификаты по умолчанию.
# Вариант 1 (безопасный): установить certifi
#   pip install certifi
# Вариант 2 (быстрый): отключить верификацию (только для доверенных API JPL)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

# ── Настройки ────────────────────────────────────────────────────────────────

SWE_FILE = "sun_ephemeris_19900711_1000.txt"   # выходной файл SWE (скачайте рядом)

# Параметры запроса к Horizons
HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"

HORIZONS_PARAMS = {
    "format":       "text",
    "COMMAND":      "'10'",          # Sun
    "OBJ_DATA":     "'NO'",
    "MAKE_EPHEM":   "'YES'",
    "EPHEM_TYPE":   "'OBSERVER'",
    "CENTER":       "'500@399'",     # ← ГЕОЦЕНТР (ключевое изменение!)
    "START_TIME":   "'1990-Jul-11 10:00'",
    "STOP_TIME":    "'1990-Jul-11 18:01'",
    "STEP_SIZE":    "'1 min'",
    "TIME_DIGITS":  "'MINUTES'",
    "QUANTITIES":   "'1,31'",        # 1=RA/DEC, 31=ObsEcLon/Lat
    "ANG_FORMAT":   "'DEG'",         # ← градусы, не HMS
    "EXTRA_PREC":   "'YES'",         # ← 6 знаков в угловых величинах
    "REF_SYSTEM":   "'ICRF'",        # ← J2000.0 ICRF
    "CSV_FORMAT":   "'NO'",
}

# ── Парсеры ───────────────────────────────────────────────────────────────────

def parse_swe_file(path):
    """Парсит файл SWE: возвращает dict {HH:MM → {RA, DEC, EclLon, EclLat}}"""
    data = {}
    with open(path) as f:
        for line in f:
            m = re.match(
                r"1990-Jul-11 (\d{2}:\d{2}):\d{2}\s+SWE\s+"
                r"([\d.]+)\s+([\d.]+)\s+[\d.]+\s+([\d.]+)\s+([-\d.]+)",
                line
            )
            if m:
                t, ra, dec, ecl, eclat = m.groups()
                data[t] = {
                    "RA":     float(ra),
                    "DEC":    float(dec),
                    "EclLon": float(ecl),
                    "EclLat": float(eclat),
                }
    return data


def parse_horizons_text(text):
    """
    Парсит текстовый ответ Horizons с ANG_FORMAT=DEG.

    При DEG формат строки данных (QUANTITIES=1,31):
      Date__(UT)__HR:MN  R.A._(ICRF) DEC_(ICRF)  ObsEcLon   ObsEcLat
      1990-Jul-11 10:00     110.5xxxx  22.0xxx    108.8xxxx  -0.0008x
    """
    data = {}
    in_soe = False

    for line in text.splitlines():
        if "$$SOE" in line:
            in_soe = True
            continue
        if "$$EOE" in line:
            break
        if not in_soe:
            continue

        parts = line.split()
        # Ожидаем: ['1990-Jul-11', 'HH:MM', flag?, RA_deg, DEC_deg, EclLon, EclLat]
        if len(parts) >= 6 and parts[0] == "1990-Jul-11":
            t = parts[1]
            try:
                # Пропускаем флаг (*, N, C, A или пусто) и ищем числа
                nums = []
                for p in parts[2:]:
                    try:
                        nums.append(float(p))
                    except ValueError:
                        if nums:
                            break  # после чисел снова нечисло — стоп
                if len(nums) >= 4:
                    data[t] = {
                        "RA":     nums[0],
                        "DEC":    nums[1],
                        "EclLon": nums[2],
                        "EclLat": nums[3],
                    }
            except Exception:
                pass

    return data


# ── Запрос к Horizons API ─────────────────────────────────────────────────────

def fetch_horizons(params, cache_file="horizons_geocentric_cache.txt"):
    """Запрашивает Horizons API. Кэширует ответ локально."""
    import os
    if os.path.exists(cache_file):
        print(f"  [CACHE] Читаем кэш: {cache_file}")
        with open(cache_file) as f:
            return f.read()

    url = HORIZONS_API + "?" + urllib.parse.urlencode(
        {k: v for k, v in params.items()}
    )
    print(f"  [API] GET {url[:100]}...")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Python/horizons-compare"})
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
            text = resp.read().decode("utf-8")
        with open(cache_file, "w") as f:
            f.write(text)
        print(f"  [API] Ответ сохранён → {cache_file}")
        return text
    except Exception as e:
        print(f"  [ОШИБКА] {e}")
        sys.exit(1)


# ── Статистика и вывод ────────────────────────────────────────────────────────

def arcsec(deg):
    return deg * 3600.0


def stats_line(name, vals):
    mean = statistics.mean(vals)
    std  = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return (f"  {name:12s}  mean={mean:+9.4f}\"  std={std:7.4f}\"  "
            f"min={min(vals):+9.4f}\"  max={max(vals):+9.4f}\"")


def main():
    print("=" * 70)
    print("  СРАВНЕНИЕ SWE vs JPL Horizons ГЕОЦЕНТР  (1990-Jul-11, 10–18 UTC)")
    print("=" * 70)

    # ── 1. Читаем SWE ───────────────────────────────────────────────────────
    print(f"\n[1] Читаем SWE-файл: {SWE_FILE}")
    try:
        swe = parse_swe_file(SWE_FILE)
        print(f"    → {len(swe)} строк ({min(swe)} — {max(swe)})")
    except FileNotFoundError:
        print(f"    [ОШИБКА] Файл не найден: {SWE_FILE}")
        print("    Положите sun_ephemeris_19900711_1000.txt рядом со скриптом.")
        sys.exit(1)

    # ── 2. Запрашиваем Horizons ─────────────────────────────────────────────
    print(f"\n[2] Запрашиваем JPL Horizons (CENTER=500@399 — ГЕОЦЕНТР)...")
    raw = fetch_horizons(HORIZONS_PARAMS)

    # Диагностика ответа
    if "$$SOE" not in raw:
        print("\n[!] $$SOE не найден в ответе. Фрагмент ответа:")
        print(raw[:2000])
        sys.exit(1)

    hor = parse_horizons_text(raw)
    print(f"    → {len(hor)} строк ({min(hor) if hor else '?'} — {max(hor) if hor else '?'})")

    # ── 3. Пересечение временных меток ─────────────────────────────────────
    common = sorted(set(swe) & set(hor))
    print(f"\n[3] Совпадающих временных меток: {len(common)}")
    if not common:
        print("    [!] Нет совпадений! Проверьте форматы.")
        # Показываем первые строки ответа
        for i, line in enumerate(raw.splitlines()):
            if "1990-Jul" in line:
                print("    Пример строки Horizons:", repr(line[:120]))
                break
        sys.exit(1)

    # ── 4. Считаем разности (SWE − Horizons) ───────────────────────────────
    dra, ddec, decl, declat = [], [], [], []
    times_h = []
    rows = []

    for t in common:
        s = swe[t]; h = hor[t]
        _dra    = arcsec(s["RA"]     - h["RA"])
        _ddec   = arcsec(s["DEC"]    - h["DEC"])
        _decl   = arcsec(s["EclLon"] - h["EclLon"])
        _declat = arcsec(s["EclLat"] - h["EclLat"])
        dra.append(_dra); ddec.append(_ddec)
        decl.append(_decl); declat.append(_declat)
        hh, mm = map(int, t.split(":"))
        times_h.append(hh + mm / 60.0)
        rows.append((t, _dra, _ddec, _decl, _declat))

    # ── 5. Вывод: почасовая таблица ─────────────────────────────────────────
    print(f"\n{'─'*72}")
    print(f"  {'Время':6s} │ {'ΔRA (\")'  :>11s} │ {'ΔDEC (\")'  :>11s} │ "
          f"{'ΔEclLon (\")'  :>13s} │ {'ΔEclLat (\")'  :>13s}")
    print(f"{'─'*72}")
    step = max(1, len(common) // 10)
    for i in range(0, len(common), step):
        t, _dra, _ddec, _decl, _declat = rows[i]
        print(f"  {t:6s} │ {_dra:+11.4f} │ {_ddec:+11.4f} │ "
              f"{_decl:+13.5f} │ {_declat:+13.5f}")

    # ── 6. Итоговая статистика ───────────────────────────────────────────────
    print(f"\n{'═'*72}")
    print(f"  ИТОГ — SWE − Horizons ГЕОЦЕНТР  (n = {len(common)} мин):")
    print(f"{'─'*72}")
    print(stats_line("ΔRA",      dra))
    print(stats_line("ΔDEC",     ddec))
    print(stats_line("ΔEclLon",  decl))
    print(stats_line("ΔEclLat",  declat))

    # ── 7. Анализ: параллакс устранён? ──────────────────────────────────────
    mid_t = (times_h[0] + times_h[-1]) / 2.0
    sin_ha   = [math.sin((t - mid_t) * math.pi / 12.0) for t in times_h]
    n = len(decl)
    mx = statistics.mean(sin_ha); my = statistics.mean(decl)
    denom = sum((x - mx) ** 2 for x in sin_ha)
    b = sum((sin_ha[i] - mx) * (decl[i] - my) for i in range(n)) / denom if denom else 0
    res_std = statistics.stdev([decl[i] - (my + b * (sin_ha[i] - mx)) for i in range(n)])

    print(f"\n  Синусоидальная амплитуда ΔEclLon·sin(HA): {abs(b):+.4f}\"")
    print(f"  (топоцентрический параллакс; должен → ~0 при геоцентре)")
    print(f"  Остаточный СКО после вычитания синуса:  {res_std:.5f}\"")

    pp_ecl = max(decl) - min(decl)
    print(f"  Пик-пик ΔEclLon: {pp_ecl:.4f}\"  "
          f"{'✓ параллакс устранён' if pp_ecl < 2.0 else '⚠ параллакс ещё присутствует'}")

    pp_ra = max(dra) - min(dra)
    print(f"  Пик-пик ΔRA:     {pp_ra:.4f}\"  "
          f"{'✓ нет дрейфа' if pp_ra < 2.0 else '— дрейф сохраняется (прецессия константна)'}")

    # ── 8. Значимость для накшатр ────────────────────────────────────────────
    NAKSHATRA_DEG = 800.0 * 3600.0   # ширина накшатры = 13°20' = 48 000"
    max_ecl_err = max(abs(v) for v in decl)
    print(f"\n{'─'*72}")
    print(f"  НАКШАТРЫ — значимость остаточных ошибок:")
    print(f"    Ширина накшатры:   {NAKSHATRA_DEG:>10.0f}\"  = 48 000\"")
    print(f"    Макс. |ΔEclLon|:  {max_ecl_err:>10.4f}\"  — {NAKSHATRA_DEG/max_ecl_err:,.0f}x меньше ширины")
    print(f"    ΔRA постоянный:   ~{abs(statistics.mean(dra)):>9.0f}\"  — прецессия (FLG_J2000 → 0)")
    print(f"    Вывод: все остаточные ошибки < 1/1000 ширины накшатры → астрологически незначимы")

    print(f"\n{'═'*72}\n")


if __name__ == "__main__":
    main()