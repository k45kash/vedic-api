"""
Сравнение методов расчёта восхода/заката.

Метод 1: Meeus (текущий fallback)         ~2 мин
Метод 2: SWE rise_trans                   <1 сек (с .se1)
Метод 3: JPL Horizons API (онлайн)        <1 сек + реальная рефракция
Метод 4: astropy + IERS                   <0.1 сек (pip install astropy)
"""

import math
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta, timezone

# ═══════════════════════════════════════════════════════════
#  МЕТОД 3: JPL Horizons API
# ═══════════════════════════════════════════════════════════

def sunrise_horizons(year, month, day, lat, lon, elev_m=0,
                     temp_c=15.0, pressure_mbar=1013.25, tz_offset=3):
    """
    Восход/закат через JPL Horizons Web API.
    Точность: ~1–5 сек. Требует интернет-соединение.
    """
    import ssl
    import re

    params = {
        "format":       "json",
        "COMMAND":      "10",
        "OBJ_DATA":     "NO",
        "MAKE_EPHEM":   "YES",
        "EPHEM_TYPE":   "OBSERVER",
        "CENTER":       "coord@399",
        "COORD_TYPE":   "GEODETIC",
        "SITE_COORD":   f"{lon},{lat}",
        "SITE_COORD_ELEV": f"{elev_m}",
        "START_TIME":   f"{year}-{month:02d}-{day:02d}",
        "STOP_TIME":    f"{year}-{month:02d}-{day+1:02d}",
        "STEP_SIZE":    "1 DAYS",
        "QUANTITIES":   "29",
        "ANG_FORMAT":   "DEG",
        "TIME_DIGITS":  "SECONDS",
        "CSV_FORMAT":   "NO",
        "CAL_FORMAT":   "BOTH",
        "APPARENT":     "REFRACTED",
        "EXTRA_PREC":   "YES",
    }

    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)

    # Пробуем три варианта SSL — обходим корпоративные прокси/самоподписанные сертификаты
    contexts = [
        ssl.create_default_context(),                        # стандартный
        ssl._create_unverified_context(),                    # без верификации
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),             # явный TLS
    ]
    contexts[2].check_hostname = False
    contexts[2].verify_mode    = ssl.CERT_NONE

    data = None
    for ctx in contexts:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = json.loads(resp.read().decode())
            break
        except Exception:
            continue

    if data is None:
        return None, None, "Не удалось подключиться к JPL Horizons (SSL / сеть)"

    result_text = data.get("result", "")

    for line in result_text.split('\n'):
        if '*r' in line and '*s' in line:
            times = re.findall(r'\d{2}:\d{2}:\d{2}(?:\.\d+)?', line)
            if len(times) >= 2:
                def add_tz(t_str, tz):
                    p = t_str.split(':')
                    h = int(p[0]); m = int(p[1]); s = float(p[2])
                    total = h*3600 + m*60 + s + tz*3600
                    total %= 86400
                    hh=int(total//3600); mm=int((total%3600)//60); ss=int(total%60)
                    return f"{hh:02d}:{mm:02d}:{ss:02d}"
                return add_tz(times[0], tz_offset), add_tz(times[-1], tz_offset), None

    # Отладка: выводим начало ответа чтобы увидеть реальный формат
    raw_sample = result_text[:600].replace('\n', ' ↵ ')
    return None, None, f"Не удалось распарсить. Начало ответа:\n       {raw_sample}"


# ═══════════════════════════════════════════════════════════
#  МЕТОД 4: astropy
# ═══════════════════════════════════════════════════════════

def sunrise_astropy(year, month, day, lat, lon, elev_m=0, tz_offset=3):
    """
    Восход/закат через astropy + astroplan.

    Точность: ~0.1–1 сек.
    Преимущество: IERS таблицы для Delta T, встроенная рефракция,
                  поддержка высоты, пользовательский горизонт.
    Установка: pip install astropy astroplan

    Внутри использует собственные эфемериды (ERFA/SOFA),
    по точности сравнимые с DE430.
    """
    try:
        from astropy.coordinates import EarthLocation, AltAz, get_body
        from astropy.time import Time
        import astropy.units as u
        from astroplan import Observer
    except ImportError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else "astropy/astroplan"
        return None, None, (
            f"Не установлено: {missing}\n"
            f"    Установка: pip install astropy astroplan\n"
            f"    После установки даёт точность ~0.1-1 сек без интернета"
        )

    location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=elev_m*u.m)
    observer = Observer(location=location, timezone=f"Etc/GMT{-tz_offset:+d}")

    dt = datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
    t  = Time(dt)

    try:
        # h0 = -50' = рефракция (34') + полудиаметр Солнца (16')
        # Это официальный стандарт восхода/заката (USNO, IAU, SWE)
        # = момент появления ВЕРХНЕГО КРАЯ диска над горизонтом
        H0 = -50 * u.arcmin

        rise = observer.sun_rise_time(t, which='nearest', horizon=H0)
        sset = observer.sun_set_time(t,  which='nearest', horizon=H0)

        rise_local = rise.to_datetime(timezone=timezone(timedelta(hours=tz_offset)))
        set_local  = sset.to_datetime(timezone=timezone(timedelta(hours=tz_offset)))

        return (rise_local.strftime("%H:%M:%S"),
                set_local.strftime("%H:%M:%S"), None)
    except Exception as e:
        return None, None, str(e)


# ═══════════════════════════════════════════════════════════
#  МЕТОД 5: учёт реальных метеоданных (концептуально)
# ═══════════════════════════════════════════════════════════

def refraction_correction_minutes(temp_c, pressure_mbar,
                                   base_temp=15.0, base_pressure=1013.25):
    """
    Поправка к времени восхода за счёт нестандартных условий (мин).
    Формула: δR = R_std × (P/P0) × (T0/T)
    где R_std ≈ 34.5' — стандартная рефракция у горизонта.

    Возвращает: Δ в минутах (+ = восход позже стандарта).
    """
    T0 = base_temp + 273.15
    T  = temp_c    + 273.15
    P0 = base_pressure
    P  = pressure_mbar

    R_std     = 34.5 / 60   # градусы
    R_actual  = R_std * (P / P0) * (T0 / T)
    delta_R   = R_actual - R_std  # градусы

    # Скорость Солнца у горизонта ~0.25°/мин
    sun_speed = 0.25  # °/мин
    delta_min = delta_R / sun_speed

    return round(delta_min, 2)


# ═══════════════════════════════════════════════════════════
#  ДЕМОНСТРАЦИЯ
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    lat, lon, elev = 45.043317, 41.969110, 450
    tz = 3

    print("\n" + "═"*60)
    print("  Точность расчёта восхода/заката — сравнение методов")
    print("═"*60)
    print(f"  Ставрополь 13.03.2026  |  lat {lat}°  lon {lon}°  UTC+{tz}")
    print(f"  Эталон (время.ру / astro.com): 06:27 / 18:15")
    print()

    # ── Метод 1: Meeus (реальный расчёт) ──────────────────
    import math
    def _dt_to_jd(y, mo, d, h=0):
        if mo <= 2: y -= 1; mo += 12
        A = int(y/100); B = 2 - A + int(A/4)
        return int(365.25*(y+4716)) + int(30.6001*(mo+1)) + d + h/24 + B - 1524.5

    def _sun_params(jd):
        T   = (jd - 2451545.0) / 36525.0
        L0  = (280.46646 + 36000.76983*T) % 360
        M   = math.radians((357.52911 + 35999.05029*T) % 360)
        C   = ((1.914602 - 0.004817*T)*math.sin(M)
              + 0.019993*math.sin(2*M) + 0.000289*math.sin(3*M))
        sl  = (L0 + C) % 360
        om  = 125.04 - 1934.136*T
        al  = math.radians(sl - 0.00569 - 0.00478*math.sin(math.radians(om)))
        ep  = math.radians(23.439291111 - 0.013004167*T
                           + 0.000164*math.sin(math.radians(om)))
        dec = math.asin(math.sin(ep)*math.sin(al))
        ra  = math.degrees(math.atan2(math.cos(ep)*math.sin(al), math.cos(al))) % 360
        eot = ((L0 - 0.0057183 - ra + 180*(round((L0-ra)/180))) * 4)
        return dec, eot

    jd0 = _dt_to_jd(2026, 3, 13)
    dec, eot = _sun_params(jd0)
    lat_r = math.radians(lat)
    cos_H = (math.sin(math.radians(-0.8333)) - math.sin(lat_r)*math.sin(dec)) / \
            (math.cos(lat_r)*math.cos(dec))
    H_h   = math.degrees(math.acos(cos_H)) / 15.0
    noon  = 12.0 - lon/15.0 - eot/60.0
    def _hms(h_utc):
        t = (h_utc + tz) % 24
        return f"{int(t):02d}:{int((t%1)*60):02d}:{int(((t%1)*60%1)*60):02d}"
    print(f"  1. Meeus:          {_hms(noon-H_h)} / {_hms(noon+H_h)}")

    # ── Метод 2: SWE rise_trans (реальный вызов) ──────────
    try:
        import swisseph as swe, os as _os
        swe.set_ephe_path(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ephe"))
        geopos   = (lon, lat, elev/1000)
        jd_start = _dt_to_jd(2026, 3, 12, 21)  # 21:00 UTC накануне = до любого восхода

        # Определяем сигнатуру установленной версии
        import inspect
        try:
            sig = str(inspect.signature(swe.rise_trans))
            print(f"  2. SWE сигнатура: rise_trans{sig}")
        except Exception:
            try:
                doc = (swe.rise_trans.__doc__ or "")[:300]
                print(f"  2. SWE doc: {doc}")
            except Exception:
                pass

        def _rt(rsmi):
            # Правильная сигнатура (из docstring):
            # rise_trans(tjdut, body, rsmi, geopos, atpress, attemp, flags)
            try:
                ret, t = swe.rise_trans(jd_start, swe.SUN, rsmi,
                                        geopos, 1013.25, 15.0,
                                        swe.FLG_SWIEPH)
                if ret == 0 and t[0] > 0:
                    frac = ((t[0]+0.5)%1)*24 + tz; frac %= 24
                    ts = f"{int(frac):02d}:{int((frac%1)*60):02d}:{int(((frac%1)*60%1)*60):02d}"
                    return ts, "OK"
                return None, f"ret={ret}, t={t[0]:.4f}"
            except Exception as e:
                return None, f"{type(e).__name__}: {e}"

        r_swe, r_info = _rt(swe.CALC_RISE)
        s_swe, s_info = _rt(swe.CALC_SET)
        if r_swe and s_swe:
            _, retf = swe.calc_ut(_dt_to_jd(2026, 3, 13, 12), swe.SUN, swe.FLG_SWIEPH)
            eph = "DE431" if retf & swe.FLG_SWIEPH else "Moshier"
            print(f"  2. SWE ({eph}):   {r_swe} / {s_swe}")
        else:
            print(f"  2. SWE rise_trans: нет результата")
            print(f"       rise: {r_info}")
            print(f"       set:  {s_info}")
    except ImportError:
        print(f"  2. SWE:            не установлен")
    except Exception as e:
        print(f"  2. SWE:            ошибка — {e}")

    # ── Метод 3: JPL Horizons ─────────────────────────────
    print(f"\n  Запрашиваем JPL Horizons API...")
    r3, s3, err3 = sunrise_horizons(2026, 3, 13, lat, lon, elev_m=elev, tz_offset=tz)
    print(f"  3. JPL Horizons:   {r3+' / '+s3 if r3 else 'недоступен ('+err3+')'}")

    # ── Метод 4: astropy ──────────────────────────────────
    print(f"\n  Проверяем astropy...")
    r4, s4, err4 = sunrise_astropy(2026, 3, 13, lat, lon, elev_m=elev, tz_offset=tz)
    if err4:
        for i, line in enumerate(err4.split('\n')):
            print(("  4. astropy:        " if i == 0 else "                     ") + line)
    else:
        print(f"  4. astropy:        {r4} / {s4}")

    # ── Влияние метеоусловий ──────────────────────────────
    print("\n" + "─"*60)
    print("  Влияние реальных метеоусловий на рефракцию:")
    for label, t_c, p in [
        ("Стандарт (15°C, 1013 мбар)", 15, 1013.25),
        ("Жара (+35°C, 1013 мбар)",    35, 1013.25),
        ("Мороз (-20°C, 1013 мбар)",  -20, 1013.25),
        ("Высокое давл. (15°C, 1040)", 15, 1040.0),
        ("Низкое давл. (15°C, 980)",   15,  980.0),
        ("Зима (-10°C, 1030 мбар)",   -10, 1030.0),
    ]:
        d = refraction_correction_minutes(t_c, p)
        print(f"  {label:<38}: {abs(d):.1f} мин {'позже' if d > 0 else 'раньше'}")

    print()
    print("  Максимум без метеоданных: ~10-15 сек.")
    print("═"*60)