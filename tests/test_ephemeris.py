"""Эфемериды: сидерические долготы, аянамша, топоцентр.

Главное здесь — регрессия дефекта №1 (см. docs/WORKLOG.md, «Систематический
сдвиг всех долгот»). `swe.calc_ut` без FLG_SIDEREAL отдаёт ВИДИМУЮ долготу,
то есть уже с нутацией, а `swe.get_ayanamsa_ut` — аянамшу БЕЗ неё. Разность
`trop - aya` считала нутацию дважды и давала сдвиг до 16″ по всем телам сразу.

Эталон — сам Swiss Ephemeris в режиме FLG_SIDEREAL: он единственный считает
нираяна-долготу внутри себя и нутацию дважды не учитывает. Все четыре модуля
проекта обязаны совпадать с ним и между собой.

Нутация знакопеременна с периодом ~18.6 года, поэтому одной даты мало: на
1950 году ошибочная формула давала всего −1.3″, и тест на этой дате дефект бы
проспал. Отсюда пять эпох: 1900, 1950, 2000, 2026, 2050.
"""

import pytest

import nakshatra_calculator as nc
import nakshatra_calendar as ncal
import sade_sati as ss
import Panchangam as pn

# Пять эпох на весь рабочий диапазон эфемерид. Значения ошибочной формулы
# (вычитание аянамши без нутации) на них: +16.23″, −1.30″, −15.91″, +7.36″,
# +12.86″ — знак меняется, величина тоже.
EPOCHS = [
    (1900, 6, 15, 12.0),
    (1950, 6, 15, 12.0),
    (2000, 1, 15, 12.0),
    (2026, 7, 26, 12.0),
    (2050, 6, 15, 12.0),
]

# Допуск. Правильная формула совпадает с FLG_SIDEREAL бит в бит (0.000000″),
# поэтому 0.001″ — это запас в тысячу раз, но при этом в 16 000 раз меньше
# амплитуды дефекта. Промахнуться мимо него невозможно.
TOL_ARCSEC = 1e-3


def _jd(epoch, swe):
    y, m, d, h = epoch
    return swe.julday(y, m, d, h)


def _diff_arcsec(a: float, b: float) -> float:
    """Разность долгот в угловых секундах с учётом перехода через 0°."""
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


# ═══════════════════════════════════════════════════════════════════════
#  Дефект №1: аянамша и нутация
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
def test_аянамша_совпадает_во_всех_модулях(epoch, swe):
    """Три модуля считают аянамшу своей функцией — значения обязаны сойтись.

    Именно здесь жил дефект: `Panchangam` брал FLG_SIDEREAL и был прав, а три
    остальных вычитали аянамшу вручную и расходились с ним.
    """
    jd = _jd(epoch, swe)
    a_calc = nc.get_aya(jd)
    a_cal = ncal.get_ayanamsha(jd)
    a_sade = ss.get_aya(jd)

    assert abs(a_calc - a_cal) * 3600 < TOL_ARCSEC
    assert abs(a_calc - a_sade) * 3600 < TOL_ARCSEC


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
@pytest.mark.parametrize("body", ["SUN", "MOON", "SATURN", "TRUE_NODE"])
def test_видимая_минус_аянамша_равна_flg_sidereal(epoch, body, swe):
    """Эталон: `trop - aya` обязано совпасть с FLG_SIDEREAL до долей секунды.

    Проверяется по четырём телам сразу — дефект был одинаков для всех, и это
    его характерная подпись: равномерный сдвиг всей карты, а не ошибка в одном
    теле.
    """
    jd = _jd(epoch, swe)
    idx = getattr(swe, body)

    trop = swe.calc_ut(jd, idx, swe.FLG_SWIEPH)[0][0]
    sid_swe = swe.calc_ut(jd, idx, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
    sid_ours = (trop - nc.get_aya(jd)) % 360.0

    assert abs(_diff_arcsec(sid_ours, sid_swe)) < TOL_ARCSEC, (
        f"{body} на {epoch[0]}: расхождение "
        f"{_diff_arcsec(sid_ours, sid_swe):.4f}″ — похоже на возврат нутации"
    )


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
def test_ошибочная_формула_действительно_даёт_сдвиг(epoch, swe):
    """Контрольный выстрел: убеждаемся, что тест выше вообще что-то ловит.

    Считаем ту самую разность, которая была в коде до починки
    (`get_ayanamsa_ut` — без нутации), и требуем, чтобы она отличалась от
    FLG_SIDEREAL заметно. Если Swiss Ephemeris когда-нибудь начнёт учитывать
    нутацию и в `get_ayanamsa_ut`, эта проверка упадёт первой и объяснит,
    почему остальные вдруг стали зелёными «сами собой».
    """
    jd = _jd(epoch, swe)
    aya_без_нутации = swe.get_ayanamsa_ut(jd)
    trop = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)[0][0]
    sid_swe = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]

    ошибка = abs(_diff_arcsec((trop - aya_без_нутации) % 360.0, sid_swe))
    assert ошибка > 1.0, (
        f"{epoch[0]}: ошибочная формула даёт всего {ошибка:.4f}″ — "
        "на такой дате дефект был бы незаметен, нужна другая эпоха"
    )


def test_ошибка_знакопеременна_по_эпохам(swe):
    """Нутация меняет знак — значит и дефект менял. Одной даты для теста мало.

    Фиксируем сам этот факт: среди пяти эпох есть и положительные, и
    отрицательные значения ошибки. Это обоснование выбора списка EPOCHS.
    """
    ошибки = []
    for epoch in EPOCHS:
        jd = _jd(epoch, swe)
        trop = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)[0][0]
        sid_swe = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
        ошибки.append(_diff_arcsec((trop - swe.get_ayanamsa_ut(jd)) % 360.0, sid_swe))

    assert max(ошибки) > 0 and min(ошибки) < 0, f"ошибки: {ошибки}"


# ═══════════════════════════════════════════════════════════════════════
#  Согласие модулей между собой
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
def test_луна_calendar_против_flg_sidereal(epoch, swe):
    """`nakshatra_calendar.moon_sid` — эталон FLG_SIDEREAL.

    Здесь 13″ смещали момент входа Луны в накшатру примерно на 25 секунд.
    """
    jd = _jd(epoch, swe)
    ours = ncal.moon_sid(jd)
    ref = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
    assert abs(_diff_arcsec(ours, ref)) < TOL_ARCSEC


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
def test_сатурн_sade_sati_против_flg_sidereal(epoch, swe):
    """`sade_sati.saturn_sid` — эталон FLG_SIDEREAL.

    Сатурн идёт ~2′ в сутки, поэтому 13″ сдвигали момент смены знака почти на
    три часа, а от него зависят все границы Сад-сати.
    """
    jd = _jd(epoch, swe)
    ours = ss.saturn_sid(jd)
    ref = swe.calc_ut(jd, swe.SATURN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
    assert abs(_diff_arcsec(ours, ref)) < TOL_ARCSEC


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
def test_луна_calculator_против_panchangam(epoch, swe):
    """Два модуля разными путями — `trop - aya` и FLG_SIDEREAL — об одной Луне.

    Расхождение именно этой пары и вскрыло дефект: карта не сходилась с
    панчангом на 13″.
    """
    jd = _jd(epoch, swe)
    calc = (nc.moon_trop(jd) - nc.get_aya(jd)) % 360.0
    panch = pn.moon_lon_sid(jd)
    assert abs(_diff_arcsec(calc, panch)) < TOL_ARCSEC


@pytest.mark.parametrize("epoch", EPOCHS, ids=lambda e: str(e[0]))
def test_солнце_calculator_против_panchangam(epoch, swe):
    """То же по Солнцу: планетная таблица карты и панчанг должны сойтись."""
    jd = _jd(epoch, swe)
    trop, _ = nc._planet_trop_swe(jd, 0)          # 0 — Солнце в PLANETS
    calc = (trop - nc.get_aya(jd)) % 360.0
    assert abs(_diff_arcsec(calc, pn.sun_lon_sid(jd))) < TOL_ARCSEC


def test_карта_рождения_согласована_с_панчангом(swe):
    """Сквозная проверка на контрольной карте: `calculate()` против панчанга.

    Берём не голые функции, а публичный результат `calculate()` — тот самый,
    что уезжает в API. Он округляет долготу до 4 знаков (0.36″), поэтому
    допуск здесь крупнее.
    """
    from tests.conftest import BIRTH_MOSCOW_1990 as b

    res = nc.calculate(**b)
    jd = res["jd"]
    assert abs(_diff_arcsec(res["moon_sid"], pn.moon_lon_sid(jd))) < 1.0
    # Аянамша на этой дате — 23.7273 (после починки; до неё было 23.7237)
    assert res["aya"] == pytest.approx(23.7273, abs=1e-4)


# ═══════════════════════════════════════════════════════════════════════
#  Аянамша Лахири против определения
# ═══════════════════════════════════════════════════════════════════════


def test_лахири_обнуляется_в_285_году(swe):
    """Определение Лахири: нулевая точка — совпадение зодиаков около 285 г. н.э.

    Это независимый от нашего кода эталон: если режим аянамши где-то собьётся
    на Раман, Кришнамурти или True Chitra, ноль уедет на годы.
    """
    lo, hi = swe.julday(200, 1, 1, 0.0), swe.julday(400, 1, 1, 0.0)
    норм = lambda jd: ((swe.get_ayanamsa_ut(jd) + 180.0) % 360.0) - 180.0
    while hi - lo > 0.5:
        mid = (lo + hi) / 2
        if норм(mid) < 0:
            lo = mid
        else:
            hi = mid
    год = swe.revjul(lo)[0]
    assert год == 285, f"ноль аянамши Лахири уехал в {год} год"


def test_лахири_в_1956_году_около_23_15(swe):
    """Внешний эталон: Rashtriya Panchang задаёт Лахири ≈ 23°15′ на 21.03.1956.

    Источник — определение Комитета по реформе индийского календаря (1955),
    оно же цитируется в документации Swiss Ephemeris к SIDM_LAHIRI. Swiss даёт
    23°14′44″, то есть 16″ от круглого значения — допуск 1′ это покрывает и
    при этом ловит подмену режима аянамши (соседние отличаются на минуты и
    градусы).
    """
    aya = swe.get_ayanamsa_ut(swe.julday(1956, 3, 21, 0.0))
    assert aya == pytest.approx(23.25, abs=1.0 / 60.0)


def test_скорость_аянамши_равна_прецессии(swe):
    """Аянамша растёт со скоростью общей прецессии — ~50.3″ в год.

    Инвариант: если аянамша вдруг «поедет» с другой скоростью, значит режим
    сменился на аяанамшу с собственным ходом.
    """
    jd = swe.julday(2000, 1, 1, 0.0)
    за_год = (swe.get_ayanamsa_ut(jd + 365.25) - swe.get_ayanamsa_ut(jd)) * 3600
    assert 50.0 < за_год < 50.5, f"{за_год:.3f}″/год"


# ═══════════════════════════════════════════════════════════════════════
#  Топоцентрическая поправка Луны
# ═══════════════════════════════════════════════════════════════════════


def test_топоцентр_луны_в_пределах_параллакса(swe):
    """Суточный параллакс Луны не превышает ~1°, и он обязан быть ненулевым.

    Ноль означал бы, что FLG_TOPOCTR не доехал до `calc_ut` (или что забыли
    `set_topo`) — а от этой поправки зависит знак Луны у пограничных рождений,
    то есть весь Сад-сати.
    """
    from tests.conftest import BIRTH_MOSCOW_1990 as b

    jd = nc.to_jd(
        __import__("datetime").datetime(b["year"], b["month"], b["day"],
                                        b["hour"], b["minute"]), b["tz"])
    гео = nc.moon_trop(jd)
    топо = nc.moon_trop(jd, topo=True, lat=b["lat"], lon=b["lon"])
    сдвиг = abs(_diff_arcsec(топо, гео)) / 3600.0

    assert 0.0 < сдвиг < 1.05, f"поправка {сдвиг:.4f}° вне диапазона параллакса"


def test_топоцентр_меняется_с_широтой(swe):
    """Параллакс зависит от места: экватор и полюс не могут дать одно и то же.

    Ловит подмену `set_topo` заглушкой — при ней сдвиг был бы одинаковым.
    """
    jd = swe.julday(2026, 7, 26, 12.0)
    гео = nc.moon_trop(jd)
    экватор = _diff_arcsec(nc.moon_trop(jd, True, 0.0, 37.6), гео)
    полюс = _diff_arcsec(nc.moon_trop(jd, True, 80.0, 37.6), гео)
    assert abs(экватор - полюс) > 60.0, "поправка не зависит от широты"


def test_топоцентр_только_у_луны_заметен(swe):
    """Параллакс Сатурна ничтожен рядом с лунным — соразмерность порядков.

    Инвариант проверяет, что мы не перепутали единицы: если бы поправка Луны
    считалась, скажем, в минутах вместо градусов, это отношение развалилось бы.
    """
    jd = swe.julday(2026, 7, 26, 12.0)
    swe.set_topo(37.6173, 55.7558, 0)
    сат_гео = swe.calc_ut(jd, swe.SATURN, swe.FLG_SWIEPH)[0][0]
    сат_топо = swe.calc_ut(jd, swe.SATURN, swe.FLG_SWIEPH | swe.FLG_TOPOCTR)[0][0]
    луна = abs(_diff_arcsec(nc.moon_trop(jd, True, 55.7558, 37.6173), nc.moon_trop(jd)))
    assert abs(_diff_arcsec(сат_топо, сат_гео)) < 1.0 < луна


# ═══════════════════════════════════════════════════════════════════════
#  Скорости планет (дефект «без FLG_SPEED вместо производных нули»)
# ═══════════════════════════════════════════════════════════════════════


def test_скорости_планет_ненулевые_и_правдоподобные(swe):
    """Без FLG_SPEED Swiss Ephemeris кладёт в элементы 3..5 нули, а не скорость.

    Эталон — средние суточные движения: Луна ~13.2°, Солнце ~1°, Сатурн ~0.03°.
    Проверяем порядок величины, а не точное число.
    """
    jd = swe.julday(2026, 7, 26, 12.0)
    ожидание = {0: (0.9, 1.1), 1: (11.0, 15.5), 6: (0.0, 0.15)}   # Солнце, Луна, Сатурн
    for idx, (lo, hi) in ожидание.items():
        _, speed = nc._planet_trop_swe(jd, idx)
        assert lo <= abs(speed) <= hi, f"планета {idx}: скорость {speed}°/сут"


def test_кету_ровно_напротив_раху(swe):
    """Кету = Раху + 180° по определению — узлы это одна ось."""
    jd = swe.julday(2026, 7, 26, 12.0)
    раху, v_раху = nc._planet_trop_swe(jd, 7)
    кету, v_кету = nc._planet_trop_swe(jd, 8)
    assert abs(_diff_arcsec(кету, раху + 180.0)) < 1e-6
    assert v_кету == v_раху
