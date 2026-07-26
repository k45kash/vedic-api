"""Вимшоттари-даши: суммы, порядок, баланс, границы, непрерывность.

Эталона в виде «правильного ответа» тут нет и быть не может — есть арифметика,
которую можно пересчитать независимо. Поэтому почти всё здесь инварианты:
сумма сроков ровно 120 лет, порядок управителей от накшатры Луны, длительность
антар-даши = маха × антар / 120, конец периода = начало следующего секунда в
секунду. Методическое решение, которое тесты закрепляют, — год в 365.25 суток
(пункт А3 листа для астролога), а не савана-год в 360.
"""

from datetime import datetime, timedelta

import pytest

from vimshottari import (
    DASHA_SEQUENCE, NK_SIZE, TOTAL_YEARS, YEAR_DAYS,
    calc_vimshottari, nakshatra_of,
)
from utils import NAKSHATRAS

BIRTH = datetime(1990, 6, 15, 14, 30)

# Долготы Луны, покрывающие разные накшатры и разные позиции внутри них:
# начало, середина, самый край.
ДОЛГОТЫ = [0.0, 6.5, 13.3, 13.3333333, 66.6, 123.456, 200.0, 280.75, 359.9999]


def _плоско(периоды):
    """Дерево периодов → плоский список (обход в глубину)."""
    out = []
    for p in периоды:
        out.append(p)
        out.extend(_плоско(p["sub"]))
    return out


# ═══════════════════════════════════════════════════════════════════════
#  Суммы и порядок
# ═══════════════════════════════════════════════════════════════════════


def test_сумма_сроков_ровно_120_лет():
    """Инвариант цикла Вимшоттари: 7+20+6+10+7+18+16+19+17 = 120."""
    assert sum(d["years"] for d in DASHA_SEQUENCE) == 120
    assert TOTAL_YEARS == 120.0
    assert len(DASHA_SEQUENCE) == 9


def test_порядок_управителей_канонический():
    """Кету → Венера → Солнце → Луна → Марс → Раху → Юпитер → Сатурн → Меркурий.

    Порядок задан традицией, менять его нельзя: от него зависит и стартовый
    управитель, и вся последовательность вложенных периодов.
    """
    assert [d["lord"] for d in DASHA_SEQUENCE] == [
        "Кету", "Венера", "Солнце", "Луна", "Марс",
        "Раху", "Юпитер", "Сатурн", "Меркурий",
    ]
    assert [d["years"] for d in DASHA_SEQUENCE] == [7, 20, 6, 10, 7, 18, 16, 19, 17]


def test_управители_накшатр_повторяются_циклом_из_девяти():
    """27 накшатр = три круга по девять управителей. Эталон — utils.NAKSHATRAS.

    Проверка перекрёстная: справочник накшатр и таблица даш обязаны совпадать,
    иначе стартовый управитель будет взят не тот.
    """
    for i, nk in enumerate(NAKSHATRAS):
        assert nk["lord"] == DASHA_SEQUENCE[i % 9]["lord"], nk["name"]


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_девять_маха_даш_по_кругу_от_накшатры_луны(lon):
    """Стартовый управитель — управитель накшатры Луны, дальше по кругу."""
    res = calc_vimshottari(lon, BIRTH, levels=1)
    старт = res["nakshatra"]["lord"]
    начало = [d["lord"] for d in DASHA_SEQUENCE].index(старт)

    lords = [p["lord"] for p in res["periods"]]
    assert len(lords) == 9
    assert lords == [DASHA_SEQUENCE[(начало + k) % 9]["lord"] for k in range(9)]


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_сумма_маха_даш_от_виртуального_начала_равна_120(lon):
    """Первая маха-даша урезана рождением, но полный круг всё равно 120 лет.

    Считаем от `cycle_start` (виртуальное начало стартовой махи) до конца
    девятой — должно выйти ровно 120 юлианских лет.
    """
    res = calc_vimshottari(lon, BIRTH, levels=1)
    дни = (res["periods"][-1]["dt_end"] - res["convention"]["cycle_start"]).total_seconds() / 86400
    assert дни == pytest.approx(TOTAL_YEARS * YEAR_DAYS, abs=1e-3)


# ═══════════════════════════════════════════════════════════════════════
#  Баланс на рождение
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_баланс_пересчитан_независимо(lon):
    """Баланс = полный срок × (1 − пройденная доля накшатры).

    Долю считаем здесь заново от долготы, а не берём из ответа — иначе тест
    просто повторил бы ошибку модуля.
    """
    res = calc_vimshottari(lon, BIRTH, levels=1)
    idx = int((lon % 360) / NK_SIZE) % 27
    доля = ((lon % 360) - idx * NK_SIZE) / NK_SIZE
    срок = DASHA_SEQUENCE[[d["lord"] for d in DASHA_SEQUENCE].index(NAKSHATRAS[idx]["lord"])]["years"]

    assert res["balance"]["duration_years"] == pytest.approx(срок * (1 - доля), abs=1e-6)
    assert res["balance"]["full_years"] == срок


def test_баланс_на_самой_границе_накшатры_равен_полному_сроку():
    """Ровно на 13°20′ управитель уже сменился, а баланс — полный срок.

    Пограничный случай, на котором легко получить «минус ноль лет» или
    предыдущего управителя.
    """
    res = calc_vimshottari(NK_SIZE, BIRTH, levels=1)   # начало 2-й накшатры
    assert res["nakshatra"]["num"] == 2
    assert res["nakshatra"]["lord"] == "Венера"
    assert res["balance"]["duration_years"] == pytest.approx(20.0, abs=1e-9)
    assert res["balance"]["elapsed_years"] == pytest.approx(0.0, abs=1e-9)
    # Первая маха-даша не урезана — она начинается ровно в момент рождения
    assert res["periods"][0]["dt_start"] == BIRTH
    assert res["periods"][0]["truncated_start"] is False


def test_баланс_у_самого_конца_накшатры_почти_ноль():
    """Обратный край: до границы 1e-6 накшатры — баланса почти не осталось."""
    res = calc_vimshottari(NK_SIZE * (1 - 1e-9), BIRTH, levels=1)
    assert res["nakshatra"]["num"] == 1
    assert res["balance"]["duration_years"] < 1e-6
    assert res["periods"][0]["truncated_start"] is True


def test_первая_маха_даша_кончается_балансом():
    """Конец первой махи = рождение + баланс. Связка баланса и дерева периодов."""
    res = calc_vimshottari(123.456, BIRTH, levels=2)
    ожидаемо = BIRTH + timedelta(days=res["balance"]["duration_years"] * YEAR_DAYS)
    assert abs((res["periods"][0]["dt_end"] - ожидаемо).total_seconds()) < 1e-3
    assert res["periods"][0]["dt_end"] == res["balance"]["dt_end"]


# ═══════════════════════════════════════════════════════════════════════
#  Границы антар-даш
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_антар_даши_пропорциональны_срокам_управителей(lon):
    """Длительность антар-даши = маха × срок антара / 120.

    Первую маху пропускаем: она урезана рождением, и её антар-даши тоже.
    """
    res = calc_vimshottari(lon, BIRTH, levels=2)
    for maha in res["periods"][1:]:
        for antar in maha["sub"]:
            ожидаемо = maha["duration_years"] * antar["full_years"] / TOTAL_YEARS
            assert antar["duration_years"] == pytest.approx(ожидаемо, abs=1e-5), (
                f"{maha['lord']} / {antar['lord']}"
            )


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_антар_даши_начинаются_с_управителя_махи(lon):
    """Первая антар-даша всегда принадлежит самому управителю маха-даши.

    Кроме первой махи — там начало съедено рождением, и первая уцелевшая
    антар-даша может быть любой.
    """
    res = calc_vimshottari(lon, BIRTH, levels=2)
    lords = [d["lord"] for d in DASHA_SEQUENCE]
    for maha in res["periods"][1:]:
        assert len(maha["sub"]) == 9
        начало = lords.index(maha["lord"])
        assert [a["lord"] for a in maha["sub"]] == [
            lords[(начало + k) % 9] for k in range(9)
        ]


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_антар_даши_покрывают_маху_целиком(lon):
    """Сумма антар-даш = маха-даша: ни дыр, ни нахлёста."""
    res = calc_vimshottari(lon, BIRTH, levels=2)
    for maha in res["periods"]:
        сумма = sum(a["duration_years"] for a in maha["sub"])
        assert сумма == pytest.approx(maha["duration_years"], abs=1e-5), maha["lord"]
        assert maha["sub"][0]["dt_start"] == maha["dt_start"]
        assert maha["sub"][-1]["dt_end"] == maha["dt_end"]


def test_третий_уровень_тоже_считается():
    """Пратьянтар-даши: 9×9×9 = 729 периодов, каждый пропорционален родителю."""
    res = calc_vimshottari(123.456, BIRTH, levels=3)
    все = _плоско(res["periods"])
    assert len([p for p in все if p["level"] == 3]) > 700
    maha = res["periods"][1]
    antar = maha["sub"][0]
    for prat in antar["sub"]:
        ожидаемо = antar["duration_years"] * prat["full_years"] / TOTAL_YEARS
        assert prat["duration_years"] == pytest.approx(ожидаемо, abs=1e-6)


# ═══════════════════════════════════════════════════════════════════════
#  Непрерывность
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_конец_периода_равен_началу_следующего(lon):
    """Дыра между периодами означала бы день без даши — такого не бывает."""
    res = calc_vimshottari(lon, BIRTH, levels=2)
    for уровень in (res["periods"], *[m["sub"] for m in res["periods"]]):
        for a, b in zip(уровень, уровень[1:]):
            assert a["dt_end"] == b["dt_start"], f"{a['lord']} → {b['lord']}"


@pytest.mark.parametrize("lon", ДОЛГОТЫ)
def test_все_периоды_строго_положительны(lon):
    """Нулевой или отрицательный период — верный признак ошибки урезания.

    Проверяем сами даты, а не поле `duration_years`: оно округлено до шести
    знаков и у сверхкоротких обрезков схлопывается в ноль (см. xfail ниже).
    """
    for p in _плоско(calc_vimshottari(lon, BIRTH, levels=2)["periods"]):
        assert p["dt_end"] > p["dt_start"], p["lord"]
        assert p["duration_years"] >= 0


@pytest.mark.xfail(strict=False, reason=(
    "Найдено тестом: у рождения в доли секунды от границы накшатры остаток "
    "первой маха-даши меньше 1e-6 года, и round(span, 6) в `_finalize` даёт "
    "duration_years = 0.0 (а duration_days = 0.0 после round(..., 2)). Сами "
    "даты периода при этом верные и различаются, то есть период не потерян — "
    "но потребитель API увидит «0 дней» у периода, который реально длится "
    "несколько секунд. Не чиним: правка вне tests/."))
def test_сверхкороткий_период_не_округляется_в_ноль():
    """Долгота в 3e-8° от границы: остаток первой махи ~1 секунда."""
    res = calc_vimshottari(13.3333333, BIRTH, levels=2)
    нулевые = [p for p in _плоско(res["periods"]) if p["duration_years"] == 0.0]
    assert not нулевые, [p["lord"] for p in нулевые]


def test_ровно_один_активный_период_на_уровне():
    """`is_current` — не «какой-то», а ровно один на каждом уровне вложенности."""
    res = calc_vimshottari(123.456, BIRTH, levels=2,
                           as_of=datetime(2026, 7, 26, 12, 0))
    активные = [p for p in res["periods"] if p["is_current"]]
    assert len(активные) == 1
    assert len([a for a in активные[0]["sub"] if a["is_current"]]) == 1
    assert res["current"]["mahadasha"]["lord"] == активные[0]["lord"]
    assert res["current"]["label"].count("/") == 1


def test_активный_период_содержит_момент_as_of():
    """Проверка не флага, а самого попадания даты в интервал."""
    момент = datetime(2026, 7, 26, 12, 0)
    res = calc_vimshottari(123.456, BIRTH, levels=2, as_of=момент)
    maha = res["current"]["mahadasha"]
    antar = res["current"]["antardasha"]
    assert maha["dt_start"] <= момент < maha["dt_end"]
    assert antar["dt_start"] <= момент < antar["dt_end"]
    assert maha["dt_start"] <= antar["dt_start"] and antar["dt_end"] <= maha["dt_end"]


# ═══════════════════════════════════════════════════════════════════════
#  Соглашение о длине года (пункт А3)
# ═══════════════════════════════════════════════════════════════════════


def test_год_равен_365_25_суток():
    """Методическое решение А3: юлианский год, а не савана-год в 360 суток.

    Цена вопроса — полгода на конце текущего периода Юпитера контрольной карты.
    Если константу когда-нибудь поменяют, это должно быть осознанным решением,
    а не побочным эффектом правки.
    """
    assert YEAR_DAYS == 365.25
    res = calc_vimshottari(0.0, BIRTH, levels=1)
    assert res["convention"]["year_days"] == 365.25
    # Полный срок Кету — ровно 7 × 365.25 суток
    кету = res["periods"][0]
    полный = (res["balance"]["dt_end"] - res["convention"]["cycle_start"]).total_seconds() / 86400
    assert полный == pytest.approx(7 * 365.25, abs=1e-6)
    assert кету["full_years"] == 7


# ═══════════════════════════════════════════════════════════════════════
#  Устойчивость: високосные, границы, валидация
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("birth", [
    datetime(2000, 2, 29, 12, 0),    # високосный день
    datetime(1900, 2, 28, 23, 59),   # 1900 — НЕ високосный
    datetime(2024, 12, 31, 23, 59),  # конец года
    datetime(2025, 1, 1, 0, 0),      # начало года
])
def test_високосные_и_граничные_даты_рождения(birth):
    """Даты не должны ронять расчёт и не должны портить непрерывность.

    Арифметика ведётся в юлианских годах через timedelta, но 29 февраля —
    классическое место, где ломается наивное «прибавить N лет».
    """
    res = calc_vimshottari(123.456, birth, levels=2)
    assert res["periods"][0]["dt_start"] == birth
    for a, b in zip(res["periods"], res["periods"][1:]):
        assert a["dt_end"] == b["dt_start"]


@pytest.mark.parametrize("k", range(27))
def test_каждая_накшатра_даёт_своего_стартового_управителя(k):
    """Проходим по всем 27 накшатрам ровно посередине — накшатра и лорд сходятся."""
    lon = k * NK_SIZE + NK_SIZE / 2
    res = calc_vimshottari(lon, BIRTH, levels=1)
    assert res["nakshatra"]["num"] == k + 1
    assert res["nakshatra"]["lord"] == NAKSHATRAS[k]["lord"]
    assert res["periods"][0]["lord"] == NAKSHATRAS[k]["lord"]
    # Ровно посередине накшатры прошло половина срока
    assert res["balance"]["duration_years"] == pytest.approx(
        res["balance"]["full_years"] / 2, abs=1e-9)


@pytest.mark.parametrize("сдвиг", [-1e-7, 0.0, 1e-7])
def test_накшатра_на_границе_не_прыгает(сдвиг):
    """Долгота у самой границы 13°20′: пада и номер обязаны быть согласованы.

    Здесь легко получить паду 5 или отрицательный остаток из-за накопленной
    ошибки округления.
    """
    nk = nakshatra_of(NK_SIZE + сдвиг)
    assert 1 <= nk["pada"] <= 4
    assert 0.0 <= nk["elapsed_fraction"] < 1.0
    assert nk["num"] in (1, 2)


def test_долгота_нормализуется_по_кругу():
    """370° и 10° — одна и та же точка зодиака."""
    a = calc_vimshottari(10.0, BIRTH, levels=1)
    b = calc_vimshottari(370.0, BIRTH, levels=1)
    assert a["nakshatra"] == b["nakshatra"]
    assert a["balance"]["duration_years"] == b["balance"]["duration_years"]


@pytest.mark.parametrize("плохо", [
    dict(moon_sid_lon="не число", birth_dt=BIRTH),
    dict(moon_sid_lon=float("nan"), birth_dt=BIRTH),
    dict(moon_sid_lon=10.0, birth_dt="2020-01-01"),
    dict(moon_sid_lon=10.0, birth_dt=BIRTH, levels=0),
    dict(moon_sid_lon=10.0, birth_dt=BIRTH, levels=99),
])
def test_некорректный_ввод_даёт_valueerror(плохо):
    """Мусор на входе должен падать явно, а не считаться молча."""
    with pytest.raises(ValueError):
        calc_vimshottari(**плохо)
