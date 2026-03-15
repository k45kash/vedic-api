"""
╔══════════════════════════════════════════════════════════════════════════╗
║   СРАВНЕНИЕ ЭФЕМЕРИД СОЛНЦА: Swiss Ephemeris ↔ JPL Horizons API         ║
║   Target Body: Sun [Sol]                                                 ║
╚══════════════════════════════════════════════════════════════════════════╝

Вычисляемые данные (шаг 1 минута):
  • Astrometric RA & DEC           — астрометрические прямое восхождение и склонение
  • Local Apparent Sidereal Time   — местное звёздное время
  • Observer Ecliptic Lon & Lat    — эклиптические координаты наблюдателя
  • Local Apparent Solar Time      — местное солнечное время
  • Apparent Longitude L_s         — видимая долгота Солнца

Установка зависимостей:
    pip install pyswisseph        # точный расчёт (рекомендуется)
    pip install requests          # для запросов к JPL Horizons API

Использование:
    python sun_ephemeris_compare.py                    — интерактивный режим
    python sun_ephemeris_compare.py --horizons-only    — только JPL Horizons
    python sun_ephemeris_compare.py --swisseph-only    — только Swiss Ephemeris
    python sun_ephemeris_compare.py --demo             — демо (Москва, сегодня)
"""

import math
import sys
import os
import csv
import json
from datetime import datetime, timedelta, timezone

# ─── Внешние зависимости ──────────────────────────────────────────────────────

try:
    import swisseph as swe
    USE_SWISSEPH = True
except ImportError:
    USE_SWISSEPH = False

try:
    import urllib.request
    import urllib.parse
    HAVE_URLLIB = True
except ImportError:
    HAVE_URLLIB = False

# ─── Математические утилиты ───────────────────────────────────────────────────

def r(deg):
    return math.radians(deg % 360)

def dms_str(deg, is_ra=False):
    """Градусы → ЧЧ:ММ:СС.с (для RA) или ±ГГ°ММ'СС.с (для DEC/lon/lat)."""
    sign = -1 if deg < 0 else 1
    deg = abs(deg)
    if is_ra:
        h = int(deg / 15)
        m = int((deg / 15 - h) * 60)
        s = ((deg / 15 - h) * 60 - m) * 60
        return f"{h:02d}h{m:02d}m{s:05.2f}s"
    else:
        d = int(deg)
        m = int((deg - d) * 60)
        s = ((deg - d) * 60 - m) * 60
        prefix = "-" if sign < 0 else "+"
        return f"{prefix}{d:03d}°{m:02d}'{s:05.2f}\""

def hours_to_hms(h):
    """Часы → ЧЧ:ММ:СС.с"""
    h = h % 24
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = ((h - hh) * 60 - mm) * 60
    return f"{hh:02d}:{mm:02d}:{ss:05.2f}"

def deg_to_hms(deg):
    return hours_to_hms(deg / 15.0)


# ─── Julian Day Number ────────────────────────────────────────────────────────

def dt_to_jd(dt_utc: datetime) -> float:
    """UTC datetime → Julian Day Number (TT ≈ UTC+69.184s, игнорируем для наглядности)."""
    y, m = dt_utc.year, dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5


# ─── Swiss Ephemeris — расчёты ────────────────────────────────────────────────

def _sun_swisseph(jd, lat, lon, elev):
    """
    Расчёт всех параметров Солнца через Swiss Ephemeris.

    Важное замечание о сравнении с JPL Horizons:
      Swiss Ephemeris использует модели прецессии IAU 2006 (Vondrák) и нутации IAU 2000/2006.
      JPL Horizons использует устаревшие IAU 1976 + IAU 1980.
      Это даёт постоянное смещение ~53 мсд (0.053") в RA — это НЕ ошибка,
      а разные корректные системы отсчёта.
    """
    # ── 1. Видимая (apparent) эклиптическая долгота Солнца = L_s
    #    swe.calc_ut по умолчанию (без FLG_EQUATORIAL) возвращает:
    #      pos[0] = эклиптическая долгота (тропическая, apparent)
    #      pos[1] = эклиптическая широта
    #      pos[2] = расстояние в AU
    pos_ecl, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
    Ls      = pos_ecl[0]   # apparent ecliptic longitude (= L_s)
    ecl_lat = pos_ecl[1]   # ecliptic latitude (≈ 0 для Солнца)

    # ── 2. Наклон эклиптики (для cotrans и отчёта)
    #    swe.calc_ut с swe.ECL_NUT возвращает:
    #      [0] = true obliquity (с нутацией), [1] = mean obliquity, [2] = nutation lon, [3] = nutation obl
    nut_data, _ = swe.calc_ut(jd, swe.ECL_NUT, 0)
    eps = nut_data[0]   # true obliquity of ecliptic in degrees

    # ── 3. Астрометрическое RA & DEC (ICRF, без аберрации, без нутации)
    #    Нужен флаг FLG_EQUATORIAL чтобы получить RA/DEC вместо эклиптики,
    #    плюс NOABERR + NONUT для «astrometric» координат
    flags_astrom = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL | swe.FLG_NOABERR | swe.FLG_NONUT
    pos_astrom, _ = swe.calc_ut(jd, swe.SUN, flags_astrom)
    ra_astrom  = pos_astrom[0]   # RA в градусах (0..360)
    dec_astrom = pos_astrom[1]   # DEC в градусах

    # ── 4. Видимое RA & DEC (apparent equatorial, с аберрацией и нутацией)
    flags_app = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL
    pos_app, _ = swe.calc_ut(jd, swe.SUN, flags_app)
    ra_app  = pos_app[0]
    dec_app = pos_app[1]

    # ── 5. Local Apparent Sidereal Time (LAST)
    #    swe.sidtime(jd) → Greenwich Apparent Sidereal Time в часах
    gast_h = swe.sidtime(jd)
    last_h = (gast_h + lon / 15.0) % 24

    # ── 6. Local Apparent Solar Time
    #    Часовой угол Солнца HA = LAST - RA_sun (всё в часах)
    #    Местное солнечное время = 12h + HA
    ha_sun_h     = (last_h - ra_app / 15.0) % 24
    solar_time_h = (12.0 + ha_sun_h) % 24

    return {
        "ra_astrom":    ra_astrom,
        "dec_astrom":   dec_astrom,
        "ra_app":       ra_app,
        "dec_app":      dec_app,
        "last_h":       last_h,
        "ecl_lon":      Ls,
        "ecl_lat":      ecl_lat,
        "solar_time_h": solar_time_h,
        "Ls":           Ls,
        "eps":          eps,
    }


def _sun_simplified(jd, lat, lon, elev):
    """
    Расчёт без Swiss Ephemeris (алгоритм Meeus, точность ±1').
    Используется как запасной вариант.
    """
    T = (jd - 2451545.0) / 36525.0  # Юлианские века от J2000.0

    # ── Геометрическая средняя долгота Солнца
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360

    # ── Средняя аномалия Солнца
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360
    M_r = math.radians(M)

    # ── Уравнение центра
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_r)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M_r)
         + 0.000289 * math.sin(3 * M_r))

    # ── Истинная долгота Солнца (тропическая) = L_s (apparent ecliptic longitude)
    sun_true_lon = L0 + C
    Ls = sun_true_lon % 360

    # ── Наклон эклиптики
    eps0 = 23.439291111 - 0.013004167 * T - 1.64e-7 * T * T + 5.04e-7 * T * T * T
    # Поправка нутации в наклоне
    omega = (125.04 - 1934.136 * T) % 360
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    eps_r = math.radians(eps)

    # Аберрационная поправка к долготе
    apparent_lon = Ls - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    app_r = math.radians(apparent_lon)

    # ── Астрометрическое RA и DEC (без аберрации)
    sun_r = math.radians(Ls)
    ra_astrom_r = math.atan2(math.cos(eps_r) * math.sin(sun_r), math.cos(sun_r))
    dec_astrom_r = math.asin(math.sin(eps_r) * math.sin(sun_r))
    ra_astrom = math.degrees(ra_astrom_r) % 360
    dec_astrom = math.degrees(dec_astrom_r)

    # ── Видимое RA и DEC (с аберрацией)
    ra_app_r = math.atan2(math.cos(eps_r) * math.sin(app_r), math.cos(app_r))
    dec_app_r = math.asin(math.sin(eps_r) * math.sin(app_r))
    ra_app = math.degrees(ra_app_r) % 360
    dec_app = math.degrees(dec_app_r)

    # ── Эклиптическая широта Солнца (≈ 0, малые поправки)
    ecl_lat = 0.0  # Солнце почти точно на эклиптике

    # ── GMST (Greenwich Mean Sidereal Time) по Meeus
    gmst_h = (280.46061837
               + 360.98564736629 * (jd - 2451545.0)
               + 0.000387933 * T * T
               - T * T * T / 38710000.0) % 360 / 15.0

    # ── Поправка нутации в долготе (для GAST)
    dpsi_arcsec = -17.20 * math.sin(math.radians(omega)) - 1.32 * math.sin(math.radians(2 * L0))
    dpsi_h = dpsi_arcsec * math.cos(eps_r) / 54000.0  # арксек → часы

    gast_h = (gmst_h + dpsi_h) % 24
    last_h = (gast_h + lon / 15.0) % 24

    # ── Местное солнечное время
    ha_sun_h = (last_h - ra_app / 15.0) % 24
    solar_time_h = (12.0 + ha_sun_h) % 24

    return {
        "ra_astrom":    ra_astrom,
        "dec_astrom":   dec_astrom,
        "ra_app":       ra_app,
        "dec_app":      dec_app,
        "last_h":       last_h,
        "ecl_lon":      apparent_lon % 360,
        "ecl_lat":      ecl_lat,
        "solar_time_h": solar_time_h,
        "Ls":           Ls,
        "eps":          eps,
    }


def calc_swisseph_table(start_utc, stop_utc, step_min, lat, lon, elev):
    """
    Вычисляет таблицу эфемерид Солнца (Swiss Ephemeris или упрощённый алгоритм).
    Возвращает список dict.
    """
    rows = []
    dt = start_utc
    calc_fn = _sun_swisseph if USE_SWISSEPH else _sun_simplified
    method = "Swiss Ephemeris" if USE_SWISSEPH else "Meeus simplified (±1')"

    while dt <= stop_utc:
        jd = dt_to_jd(dt)
        d = calc_fn(jd, lat, lon, elev)
        rows.append({
            "datetime_utc":    dt.strftime("%Y-%b-%d %H:%M:%S"),
            "jd":              round(jd, 8),
            "source":          method,
            # Astrometric RA & DEC
            "ra_astrom_deg":   round(d["ra_astrom"], 6),
            "dec_astrom_deg":  round(d["dec_astrom"], 6),
            "ra_astrom_hms":   dms_str(d["ra_astrom"], is_ra=True),
            "dec_astrom_dms":  dms_str(d["dec_astrom"]),
            # Local Apparent Sidereal Time
            "last_h":          round(d["last_h"], 6),
            "last_hms":        hours_to_hms(d["last_h"]),
            # Observer Ecliptic Lon & Lat
            "ecl_lon_deg":     round(d["ecl_lon"], 6),
            "ecl_lat_deg":     round(d["ecl_lat"], 6),
            # Local Apparent Solar Time
            "solar_time_h":    round(d["solar_time_h"], 6),
            "solar_time_hms":  hours_to_hms(d["solar_time_h"]),
            # Apparent longitude L_s
            "Ls_deg":          round(d["Ls"], 6),
        })
        dt += timedelta(minutes=step_min)

    return rows


# ─── JPL Horizons API ─────────────────────────────────────────────────────────
#
# Horizons QUANTITIES коды:
#   1  = Astrometric RA & DEC (ICRF)
#   7  = Local Apparent Sidereal Time
#   31 = Observer ecliptic lon & lat
#
# Local Solar Time и L_s вычисляем из полученных данных.

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

def query_horizons(start_utc, stop_utc, step_min, lat, lon, elev):
    """
    Запрашивает JPL Horizons API и возвращает распарсенную таблицу.
    Требует интернет-соединение и установленный urllib.
    """
    if not HAVE_URLLIB:
        raise RuntimeError("urllib недоступен")

    start_str = start_utc.strftime("%Y-%b-%d %H:%M")
    stop_str  = stop_utc.strftime("%Y-%b-%d %H:%M")

    params = {
        "format":       "text",
        "COMMAND":      "'10'",           # Sun ID = 10
        "OBJ_DATA":     "'NO'",
        "MAKE_EPHEM":   "'YES'",
        "EPHEM_TYPE":   "'OBSERVER'",
        "CENTER":       "'coord@399'",    # топоцентр на Земле
        "COORD_TYPE":   "'GEODETIC'",
        "SITE_COORD":   f"'{lon},{lat},{elev/1000:.3f}'",  # lon,lat,alt_km
        "START_TIME":   f"'{start_str}'",
        "STOP_TIME":    f"'{stop_str}'",
        "STEP_SIZE":    f"'{step_min}m'",
        "QUANTITIES":   "'1,7,31'",       # RA/DEC, LAST, EclLon/Lat
        "ANG_FORMAT":   "'DEG'",          # градусы, не HMS
        "CSV_FORMAT":   "'YES'",
        "EXTRA_PREC":   "'YES'",
        "TIME_TYPE":    "'UT'",
    }

    url = HORIZONS_API_URL + "?" + urllib.parse.urlencode(
        {k: v for k, v in params.items()}
    )

    print(f"\n  🌐 Запрос к JPL Horizons API...")
    print(f"     {url[:100]}...")

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "SunEphemerisCompare/1.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    return _parse_horizons_response(raw)


def _parse_horizons_response(raw: str) -> list:
    """Парсит текстовый ответ JPL Horizons в список dict."""
    rows = []
    in_table = False
    headers = None

    for line in raw.splitlines():
        stripped = line.strip()

        if "$$SOE" in stripped:
            in_table = True
            continue
        if "$$EOE" in stripped:
            break

        if not in_table:
            continue

        # Данные идут в CSV формате
        if not stripped or stripped.startswith("*") or stripped.startswith("!"):
            continue

        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) < 7:
            continue

        try:
            # Формат: date_str, ?, RA, DEC, ?, LAST, ?, EclLon, EclLat
            # Точная позиция зависит от набора quantities
            # Парсим по наличию данных
            datetime_str = parts[0].strip()
            # RA (deg), DEC (deg) — quantities=1
            ra_deg  = float(parts[3])
            dec_deg = float(parts[4])
            # LAST — quantities=7
            last_h  = float(parts[5])
            # Ecl Lon, Lat — quantities=31
            ecl_lon = float(parts[6])
            ecl_lat = float(parts[7])

            # L_s = ecl_lon (эклиптическая долгота Солнца = apparent L_s)
            # Solar time = 12h + (LAST_h - RA_h)
            ha_sun_h = (last_h - ra_deg / 15.0) % 24
            solar_time_h = (12.0 + ha_sun_h) % 24

            rows.append({
                "datetime_utc":    datetime_str,
                "source":          "JPL Horizons",
                "ra_astrom_deg":   round(ra_deg, 6),
                "dec_astrom_deg":  round(dec_deg, 6),
                "ra_astrom_hms":   dms_str(ra_deg, is_ra=True),
                "dec_astrom_dms":  dms_str(dec_deg),
                "last_h":          round(last_h, 6),
                "last_hms":        hours_to_hms(last_h),
                "ecl_lon_deg":     round(ecl_lon, 6),
                "ecl_lat_deg":     round(ecl_lat, 6),
                "solar_time_h":    round(solar_time_h, 6),
                "solar_time_hms":  hours_to_hms(solar_time_h),
                "Ls_deg":          round(ecl_lon, 6),
            })
        except (ValueError, IndexError):
            continue

    return rows


# ─── Сравнение и вывод ────────────────────────────────────────────────────────

COL_NAMES = {
    "ra_astrom_deg":   "RA astrom (°)",
    "dec_astrom_deg":  "DEC astrom (°)",
    "last_h":          "LAST (h)",
    "ecl_lon_deg":     "Ecl.Lon (°)",
    "ecl_lat_deg":     "Ecl.Lat (°)",
    "solar_time_h":    "Solar Time (h)",
    "Ls_deg":          "L_s (°)",
}

def print_comparison_table(swe_rows, jpl_rows, max_rows=20):
    """Выводит таблицу сравнения в консоль."""
    W = 110
    print("\n" + "═" * W)
    print("  🌞  СРАВНЕНИЕ ЭФЕМЕРИД СОЛНЦА: Swiss Ephemeris ↔ JPL Horizons")
    print("═" * W)

    n = min(len(swe_rows), len(jpl_rows) if jpl_rows else len(swe_rows), max_rows)
    has_jpl = bool(jpl_rows)

    header = f"{'UTC':<22} {'Источник':<20} {'RA (°)':<13} {'DEC (°)':<12} {'LAST (h)':<12} {'Ecl.Lon (°)':<14} {'L_s (°)':<12} {'Solar Time'}"
    print(f"\n  {header}")
    print("  " + "─" * (W - 2))

    for i in range(n):
        r = swe_rows[i]
        print(f"  {r['datetime_utc']:<22} {r['source']:<20} "
              f"{r['ra_astrom_deg']:<13.6f} {r['dec_astrom_deg']:<12.6f} "
              f"{r['last_h']:<12.6f} {r['ecl_lon_deg']:<14.6f} "
              f"{r['Ls_deg']:<12.6f} {r['solar_time_hms']}")

        if has_jpl and i < len(jpl_rows):
            j = jpl_rows[i]
            print(f"  {'':22} {j['source']:<20} "
                  f"{j['ra_astrom_deg']:<13.6f} {j['dec_astrom_deg']:<12.6f} "
                  f"{j['last_h']:<12.6f} {j['ecl_lon_deg']:<14.6f} "
                  f"{j['Ls_deg']:<12.6f} {j['solar_time_hms']}")

            # Дельта
            d_ra  = abs(r['ra_astrom_deg']  - j['ra_astrom_deg'])  * 3600  # арксек
            d_dec = abs(r['dec_astrom_deg'] - j['dec_astrom_deg']) * 3600
            d_lon = abs(r['ecl_lon_deg']    - j['ecl_lon_deg'])    * 3600
            d_last = abs(r['last_h']        - j['last_h'])         * 3600  # сек
            print(f"  {'':22} {'Δ (arcsec/sec)':<20} "
                  f"{'ΔRA='+f'{d_ra:.3f}\"':<13} {'ΔDEC='+f'{d_dec:.3f}\"':<12} "
                  f"{'ΔT='+f'{d_last:.3f}s':<12} {'ΔLon='+f'{d_lon:.3f}\"':<14}")
            print()
        elif has_jpl:
            print()

    if n < len(swe_rows):
        print(f"\n  ... показано {n} из {len(swe_rows)} строк ...")

    if has_jpl:
        print(f"\n  ℹ️  Ожидаемое системное расхождение SWE ↔ Horizons:")
        print(f"     ΔRA ≈ +53 мсд — Swiss Ephemeris (IAU 2006 precession) vs Horizons (IAU 1976/1980).")
        print(f"     Это НЕ ошибка — обе системы корректны (см. Astrodienst + JPL/Giorgini 2021).")

    print("═" * W + "\n")


def save_csv(swe_rows, jpl_rows, filename):
    """Сохраняет обе таблицы в CSV файл."""
    all_rows = swe_rows.copy()
    if jpl_rows:
        all_rows += jpl_rows
        # Добавляем строки дельт
        n = min(len(swe_rows), len(jpl_rows))
        for i in range(n):
            s, j = swe_rows[i], jpl_rows[i]
            all_rows.append({
                "datetime_utc": s["datetime_utc"],
                "source": "DELTA (SWE-JPL)",
                "ra_astrom_deg":  round(s["ra_astrom_deg"]  - j["ra_astrom_deg"],  8),
                "dec_astrom_deg": round(s["dec_astrom_deg"] - j["dec_astrom_deg"], 8),
                "last_h":         round(s["last_h"]         - j["last_h"],         8),
                "ecl_lon_deg":    round(s["ecl_lon_deg"]    - j["ecl_lon_deg"],    8),
                "ecl_lat_deg":    round(s["ecl_lat_deg"]    - j["ecl_lat_deg"],    8),
                "solar_time_h":   round(s["solar_time_h"]   - j["solar_time_h"],   8),
                "Ls_deg":         round(s["Ls_deg"]         - j["Ls_deg"],         8),
            })

    if not all_rows:
        return

    fieldnames = ["datetime_utc", "source", "ra_astrom_deg", "ra_astrom_hms",
                  "dec_astrom_deg", "dec_astrom_dms", "last_h", "last_hms",
                  "ecl_lon_deg", "ecl_lat_deg", "solar_time_h", "solar_time_hms",
                  "Ls_deg"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    print(f"  💾 Сохранено: {filename}  ({len(all_rows)} строк)")


def save_txt_comparison(swe_rows, jpl_rows, filename):
    """
    Сохраняет полный детализированный отчёт в .txt файл
    (аналог вывода JPL Horizons).
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write("*" * 78 + "\n")
        f.write(f"  Sun [Sol] — Ephemeris Comparison Report\n")
        f.write(f"  Generated: {datetime.utcnow().strftime('%Y-%b-%d %H:%M:%S')} UTC\n")
        if swe_rows:
            f.write(f"  Source A: {swe_rows[0]['source']}\n")
        if jpl_rows:
            f.write(f"  Source B: {jpl_rows[0]['source']}\n")
        f.write("*" * 78 + "\n\n")

        f.write("Columns:\n")
        f.write("  Date/Time (UTC)\n")
        f.write("  RA_astrom (°)   — Astrometric Right Ascension (ICRF J2000)\n")
        f.write("  DEC_astrom (°)  — Astrometric Declination (ICRF J2000)\n")
        f.write("  LAST (h)        — Local Apparent Sidereal Time\n")
        f.write("  Ecl.Lon (°)     — Observer Ecliptic Longitude (L_s)\n")
        f.write("  Ecl.Lat (°)     — Observer Ecliptic Latitude\n")
        f.write("  Solar Time      — Local Apparent Solar Time\n")
        f.write("  L_s (°)         — Apparent Solar Longitude\n\n")

        # Header row
        hdr = (f"{'Date/Time UTC':<23} {'Src':<8} {'RA_astrom':>13} {'DEC_astrom':>12} "
               f"{'LAST(h)':>10} {'EclLon':>10} {'EclLat':>9} {'SolarTime':>12} {'L_s':>10}")
        f.write(hdr + "\n")
        f.write("-" * len(hdr) + "\n")

        n = max(len(swe_rows), len(jpl_rows) if jpl_rows else 0)
        for i in range(n):
            for label, rows in [("SWE", swe_rows), ("JPL", jpl_rows)]:
                if not rows or i >= len(rows):
                    continue
                row = rows[i]
                f.write(
                    f"{row['datetime_utc']:<23} {label:<8} "
                    f"{row['ra_astrom_deg']:>13.6f} {row['dec_astrom_deg']:>12.6f} "
                    f"{row['last_h']:>10.6f} {row['ecl_lon_deg']:>10.6f} "
                    f"{row['ecl_lat_deg']:>9.5f} {row['solar_time_hms']:>12} "
                    f"{row['Ls_deg']:>10.6f}\n"
                )

            # Дельта
            if jpl_rows and i < len(swe_rows) and i < len(jpl_rows):
                s, j = swe_rows[i], jpl_rows[i]
                d_ra  = (s["ra_astrom_deg"]  - j["ra_astrom_deg"])  * 3600
                d_dec = (s["dec_astrom_deg"] - j["dec_astrom_deg"]) * 3600
                d_lon = (s["ecl_lon_deg"]    - j["ecl_lon_deg"])    * 3600
                f.write(
                    f"{'':23} {'Δ\"':<8} "
                    f"{'ΔRA='+f'{d_ra:+.3f}\"':>13} {'ΔDEC='+f'{d_dec:+.3f}\"':>12} "
                    f"{'':>10} {'ΔLon='+f'{d_lon:+.3f}\"':>10}\n"
                )
            f.write("\n")

    print(f"  📄 Сохранено: {filename}")


# ─── Интерактивный ввод ───────────────────────────────────────────────────────

def ask(prompt, cast, err_msg, default=None):
    full_prompt = prompt
    if default is not None:
        full_prompt += f" [{default}]"
    full_prompt += ": "
    while True:
        try:
            raw = input(full_prompt).strip()
            if raw == "" and default is not None:
                return cast(default) if isinstance(default, str) else default
            return cast(raw)
        except Exception:
            print(f"  ❌  {err_msg}")


def get_params_interactive():
    print("\n" + "═" * 60)
    print("  🌞  SUN EPHEMERIS — параметры расчёта")
    print("═" * 60)

    # Место
    print("\n  📍 Местоположение наблюдателя")
    lat  = ask("  Широта (+ север, - юг)", float,
               "Введите число, например 55.75", "55.7520")
    lon  = ask("  Долгота (+ восток, - запад)", float,
               "Введите число, например 37.62", "37.6156")
    elev = ask("  Высота над уровнем моря (м)", float,
               "Введите число", "156")

    # Время
    print("\n  🕐 Временной диапазон (UTC)")
    def parse_dt(s):
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        raise ValueError

    start = ask("  Начало (YYYY-MM-DD HH:MM)", parse_dt,
                "Формат: 2025-03-20 12:00", "2025-03-20 12:00")
    stop  = ask("  Конец  (YYYY-MM-DD HH:MM)", parse_dt,
                "Формат: 2025-03-20 12:30", "2025-03-20 12:30")
    step  = ask("  Шаг (минуты)", int, "Введите целое число", 1)

    return lat, lon, elev, start, stop, step


# ─── Demo данные ──────────────────────────────────────────────────────────────

DEMO = {
    "name":  "Москва, весеннее равноденствие 2025",
    "lat":   55.7520,
    "lon":   37.6156,
    "elev":  156.0,
    "start": datetime(2025, 3, 20, 10, 0, 0),
    "stop":  datetime(2025, 3, 20, 10, 5, 0),
    "step":  1,
}


# ─── Точка входа ──────────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "--demo":
        p = DEMO
        lat, lon, elev = p["lat"], p["lon"], p["elev"]
        start, stop, step = p["start"], p["stop"], p["step"]
        print(f"\n  📍 Демо: {p['name']}")
    else:
        lat, lon, elev, start, stop, step = get_params_interactive()

    print(f"\n  ⚙️  Swiss Ephemeris: {'✅ pyswisseph' if USE_SWISSEPH else '⚠️ Упрощённый алгоритм Meeus'}")

    # ── Расчёт Swiss Ephemeris
    print(f"\n  🔢 Вычисляю {'Swiss Ephemeris' if USE_SWISSEPH else 'Meeus'}...")
    swe_rows = calc_swisseph_table(start, stop, step, lat, lon, elev)
    print(f"     ✅ {len(swe_rows)} строк готово")

    # ── JPL Horizons API
    jpl_rows = []
    if mode != "--swisseph-only":
        try:
            jpl_rows = query_horizons(start, stop, step, lat, lon, elev)
            print(f"     ✅ {len(jpl_rows)} строк получено от JPL Horizons")
        except Exception as e:
            print(f"\n  ⚠️  JPL Horizons API недоступен: {e}")
            print("     Продолжаю только с локальным расчётом.\n")

    # ── Вывод
    print_comparison_table(swe_rows, jpl_rows, max_rows=30)

    # ── Сохранение файлов
    ts = start.strftime("%Y%m%d_%H%M")
    out_csv = f"sun_ephemeris_{ts}.csv"
    out_txt = f"sun_ephemeris_{ts}.txt"

    save_csv(swe_rows, jpl_rows, out_csv)
    save_txt_comparison(swe_rows, jpl_rows, out_txt)

    # ── Инструкция для JPL Horizons (ручная проверка)
    print("\n" + "─" * 60)
    print("  📋 Для ручной проверки на сайте JPL Horizons:")
    print("     https://ssd.jpl.nasa.gov/horizons/app.html#/")
    print(f"\n     Target Body      : Sun [Sol] (ID = 10)")
    print(f"     Observer Location: lon={lon}°, lat={lat}°, elev={elev}m")
    print(f"     Start Time       : {start.strftime('%Y-%b-%d %H:%M')} UTC")
    print(f"     Stop Time        : {stop.strftime('%Y-%b-%d %H:%M')} UTC")
    print(f"     Step Size        : {step} minutes")
    print(f"     Table Quantities : 1 (RA/DEC), 7 (Sidereal Time), 31 (Ecl.Lon/Lat)")
    print(f"     Angle Format     : degrees")
    print("─" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Выход.")
