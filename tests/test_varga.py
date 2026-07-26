"""Тесты варг (`varga.py`) — навамша D9 и прочие вибхаги.

Тесты написаны против эталона, а не против текущего вывода (см. conftest.py):

  • правило Парашары сверяется с НЕЗАВИСИМОЙ эталонной реализацией на точной
    рациональной арифметике (`fractions.Fraction`) — она не разделяет с
    боевым кодом ни одной строки и не может «согласованно ошибаться»;
  • круг 108 пад сверяется с `content/padas.json` — таблицей, составленной
    человеком вне этого репозитория (`test_pada_wheel_matches_content_base`).
    Это самая сильная сверка схемы отсчёта: внешний источник, не зависящий
    ни от нашего кода, ни от онлайн-калькуляторов;
  • знаки навамши на двух реальных картах зафиксированы как эталоны — они
    ловят уже не схему отсчёта, а сдвиг эфемерид под ней;
  • сверка с онлайн-калькуляторами сознательно НЕ автоматизирована: они
    требуют интерактивной формы и молча подставляют свои умолчания по
    аянамше и часовому поясу. Их роль — разовая ручная проверка, а не тест;
  • границы отрезков проверяются отдельно: именно там разъезжается
    арифметика с плавающей точкой, и именно там ошибку не видно глазом.
"""

from fractions import Fraction

import pytest

import varga as v


# ═══════════════════════════════════════════════════════════
#  ЭТАЛОННЫЕ РЕАЛИЗАЦИИ (точная арифметика, независимо от varga.py)
# ═══════════════════════════════════════════════════════════

MOVABLE, FIXED, DUAL = 0, 1, 2


def ref_navamsa_parashara(lon: Fraction) -> int:
    """Эталон №1: буквально правило Парашары, на дробях.

    Подвижный знак — счёт от него самого, неподвижный — от 9-го от него,
    двойственный — от 5-го. Ни одного деления на нецелое: Fraction точна.
    """
    lon = lon % 360
    sign0 = int(lon // 30)                              # 0..11
    part = int((lon - sign0 * 30) // Fraction(30, 9))   # 0..8
    start = {MOVABLE: 0, FIXED: 8, DUAL: 4}[sign0 % 3]
    return (sign0 + start + part) % 12 + 1


def ref_navamsa_continuous(lon: Fraction) -> int:
    """Эталон №2: непрерывный счёт отрезков 3°20' от 0° Овна."""
    return int((lon % 360) // Fraction(10, 3)) % 12 + 1


def ref_varga_sign(lon: Fraction, divisions: int, start_fn, step: int) -> int:
    """Общий эталон «start + номер_части × шаг» на точной арифметике."""
    lon = lon % 360
    sign0 = int(lon // 30)
    part = int((lon - sign0 * 30) // Fraction(30, divisions))
    return (sign0 + start_fn(sign0 + 1) + part * step) % 12 + 1


# Точки, на которых имеет смысл сверяться: границы всех делений (включая
# «неудобные» 3°20', 4°17'8.57", 26°40') плюс середины отрезков и мелкая сетка.
def _probe_points():
    pts = set()
    for divisions in (2, 3, 7, 9, 10, 12):
        step = Fraction(30, divisions)
        for i in range(12 * divisions + 1):
            b = (i * step) % 360
            pts.add(b)                       # ровно на границе
            pts.add(b + step / 2)            # середина отрезка
    for i in range(0, 3600):                 # регулярная сетка 0.1°
        pts.add(Fraction(i, 10))
    return sorted(p % 360 for p in pts)


PROBES = _probe_points()


# ═══════════════════════════════════════════════════════════
#  СХЕМА ОТСЧЁТА НАВАМШИ
# ═══════════════════════════════════════════════════════════

def test_parashara_rule_equals_continuous_count():
    """Правило Парашары тождественно непрерывному счёту от 0° Овна.

    Это главное утверждение docstring модуля: именно оно позволяет считать
    навамшу одним делением и не заводить таблицу из 12 стартовых знаков.
    Проверяется точной арифметикой на всех границах и серединах отрезков.
    """
    for lon in PROBES:
        assert ref_navamsa_parashara(lon) == ref_navamsa_continuous(lon), lon


def test_navamsa_matches_reference_everywhere():
    """Боевой `varga_sign(lon, 9)` совпадает с точным эталоном.

    Границы отрезков исключены сознательно: в них 3°20' не представимо в
    double, и «правильный» ответ зависит от того, куда округлилось само
    входное число, — см. отдельный тест `test_boundary_rounding_is_downward`.
    """
    for lon in PROBES:
        if lon % Fraction(10, 3) == 0:
            continue
        assert v.varga_sign(float(lon), 9) == ref_navamsa_parashara(lon), lon


@pytest.mark.parametrize("lon_deg,expected_sign,why", [
    (0.0,    1,  "0° Овна — подвижный знак, счёт от себя → 1-я навамша Овен"),
    (3.3,    1,  "внутри 1-й навамши Овна"),
    (3.4,    2,  "перевалили 3°20' → 2-я навамша, Телец"),
    (29.9,   9,  "конец Овна → 9-я навамша, Стрелец"),
    (30.0,  10,  "0° Тельца: неподвижный → счёт с 9-го от него = Козерог"),
    (60.0,   7,  "0° Близнецов: двойственный → счёт с 5-го от них = Весы"),
    (90.0,   4,  "0° Рака: подвижный → счёт от себя = Рак"),
    (120.0,  1,  "0° Льва: неподвижный → 9-й от Льва = Овен"),
    (150.0, 10,  "0° Девы: двойственный → 5-й от Девы = Козерог"),
    (330.0,  4,  "0° Рыб: двойственный → 5-й от Рыб = Рак"),
    (359.9, 12,  "конец Рыб → 108-я навамша круга, снова Рыбы"),
])
def test_navamsa_anchor_points(lon_deg, expected_sign, why):
    """Опорные точки схемы отсчёта — по одной на каждое качество знака."""
    assert v.varga_sign(lon_deg, 9) == expected_sign, why


def test_navamsa_covers_each_sign_nine_times():
    """108 навамш круга раскладываются на 12 знаков ровно по 9 в каждый."""
    counts = {}
    for i in range(108):
        mid = (i + 0.5) * (360 / 108)
        s = v.varga_sign(mid, 9)
        counts[s] = counts.get(s, 0) + 1
    assert sorted(counts) == list(range(1, 13))
    assert set(counts.values()) == {9}


# ═══════════════════════════════════════════════════════════
#  ГРАНИЦЫ И АРИФМЕТИКА С ПЛАВАЮЩЕЙ ТОЧКОЙ
# ═══════════════════════════════════════════════════════════

def test_boundary_values_follow_the_actual_double():
    """На границах пад ответ согласован с РЕАЛЬНЫМ значением double.

    3°20' не представимо в double, поэтому `i * 360/108` — это не сама
    граница, а ближайшее к ней число, лежащее чуть ниже или чуть выше неё.
    Требовать «правильную» паду в отрыве от этого числа бессмысленно;
    требовать можно другое: чтобы результат в точности соответствовал тому
    числу, которое реально пришло на вход. `Fraction(x)` берёт точное
    значение double, поэтому эталон отвечает именно на этот вопрос.
    """
    for i in range(108):
        lon = i * (360 / 108)
        exact = int(Fraction(lon) % 360 // Fraction(10, 3))
        assert v.navamsa_index(lon) == exact, (i, lon)


def test_part_and_sign_never_disagree():
    """Номер части и номер знака не могут рассогласоваться.

    Раньше `varga_part` делил на 30/9, а сквозной номер считался делением
    на 360/108 — два разных округления, и на семи точках круга они давали
    разные ответы. Инвариант: сквозной номер = (знак−1)·9 + часть, всегда.
    """
    for lon in PROBES:
        f = float(lon)
        sign0 = int(f % 360 / 30)
        part = v.varga_part(f, 9)
        assert 0 <= part <= 8
        assert v.navamsa_index(f) == sign0 * 9 + part, f


def test_end_of_zodiac_does_not_overflow():
    """Конец круга не выпадает за таблицу знаков."""
    for lon in (359.999999, 359.9999999999, 360.0 - 1e-12, 360.0, 720.0, -0.000001):
        for varga in (1, 2, 3, 7, 9, 10, 12):
            assert 1 <= v.varga_sign(lon, varga) <= 12, (lon, varga)
        assert 0 <= v.navamsa_index(lon) <= 107, lon


def test_negative_and_oversized_longitudes_normalise():
    """Долготы вне [0, 360) приводятся к кругу, а не ломают расчёт."""
    for base in (0.0, 41.856, 284.394, 359.5):
        for k in (-720, -360, 360, 720):
            assert v.varga_sign(base + k, 9) == v.varga_sign(base, 9)


# ═══════════════════════════════════════════════════════════
#  СОГЛАСОВАННОСТЬ С НАКШАТРАМИ (108 навамш = 108 пад)
# ═══════════════════════════════════════════════════════════

def test_navamsa_index_matches_pada(swe):
    """Сквозной номер навамши = сквозной номер пады из `get_nk`.

    Это не совпадение, а следствие: 27 × 4 = 108 = 12 × 9, границы пад и
    навамш — одни и те же точки. На этой тождественности стоит круг 108 пад
    из `content/chart_geometry.json`.

    Границы НЕ исключаются — именно они и были больным местом (см. следующий
    тест). Сетка 0.001° по всему кругу.
    """
    from nakshatra_calculator import get_nk

    for i in range(0, 360_000):
        lon = i / 1000.0
        nk = get_nk(lon)
        expected = (nk["num"] - 1) * 4 + nk["pada"] - 1
        assert v.navamsa_index(lon) == expected, lon


def test_граница_пады_считается_точно_везде(swe):
    """Регрессия: на точных границах пад все три пути дают один ответ.

    История. `get_nk` вычислял паду двумя последовательными делениями на
    дробные шаги (360/27, потом 13°20'/4), и на числах, попавших ровно на
    границу, округления расходились: **70 границ из 108** давали неверную
    паду, местами сразу на три (на 40.0° выходила Криттика пада 4 вместо
    Рохини пада 1). `varga` считал умножением до деления — лучше, но тоже не
    точно: на 32 точках два модуля называли РАЗНЫЕ пады для одной долготы.

    Для живой карты это ничего не значило — попасть в границу с точностью до
    1e-15 практически невозможно. Но круг 108 пад и поиск момента входа Луны
    в накшатру (бисекция сходится ровно к границе) попадают туда по
    построению, то есть с вероятностью единица.

    Теперь и `utils.global_pada`, и `varga` считают через `Fraction`, то есть
    точно, и вопрос «какая пада у этого числа» имеет ровно один ответ.
    """
    from nakshatra_calculator import get_nk
    from utils import global_pada

    for i in range(108):
        for lon in (i * (360 / 360 * 10 / 3), i * (10 / 3) + 1e-9, i * (10 / 3) - 1e-9):
            эталон = int(Fraction(lon) % 360 // Fraction(10, 3))
            nk = get_nk(lon)
            assert (nk["num"] - 1) * 4 + nk["pada"] - 1 == эталон, lon
            assert v.navamsa_index(lon) == эталон, lon
            assert global_pada(lon) == эталон, lon


# ═══════════════════════════════════════════════════════════
#  ВАРГОТТАМА
# ═══════════════════════════════════════════════════════════

def test_vargottama_equals_classical_positions():
    """Варготтама ⇔ 1-я навамша подвижного / 5-я неподвижного / 9-я двойственного.

    Классическое описание варготтамы даётся и так, и через «тот же знак в
    D1 и D9». Тест проверяет, что при нашей схеме отсчёта это буквально
    одно и то же множество долгот — иначе схема выбрана неверно.
    """
    expected_part = {MOVABLE: 0, FIXED: 4, DUAL: 8}
    for i in range(108):
        mid = (i + 0.5) * (360 / 108)
        sign0 = int(mid / 30)
        part = v.varga_part(mid, 9)
        classical = part == expected_part[sign0 % 3]
        assert v.is_vargottama(mid) == classical, mid


def test_vargottama_is_one_navamsa_per_sign():
    """На круге ровно 12 варготтамных навамш — по одной на знак."""
    wheel = v.pada_wheel()
    vg = [p for p in wheel if p["vargottama"]]
    assert len(vg) == 12
    assert sorted(p["d1_sign"] for p in vg) == list(range(1, 13))
    assert all(p["d1_sign"] == p["d9_sign"] for p in vg)


@pytest.mark.parametrize("lon,expected", [
    (0.5,    True),   # 1-я навамша Овна (подвижный)
    (3.5,    False),
    (44.0,   True),   # Телец 14°, 5-я навамша неподвижного знака
    (43.0,   False),  # Телец 13° — ещё 4-я навамша, до границы 13°20' 20'
    (41.856, False),  # Меркурий карты A — Телец 11°51', 4-я навамша
    (88.0,   True),   # Близнецы 28°, 9-я навамша двойственного знака
    (270.31, True),   # Сатурн карты A — Козерог 0°18', подвижный, 1-я навамша
])
def test_vargottama_spot_checks(lon, expected):
    assert v.is_vargottama(lon) is expected


def test_vargottama_only_about_d9():
    """`is_vargottama` — только про D1/D9; обобщение живёт в `same_sign_in`.

    Термин размывают: совпадение знака в D1 и любой варге тоже иногда зовут
    варготтамой. У нас это разные функции, и на реальном примере они дают
    разный ответ — значит, подмены нет.
    """
    lon = 31.0                                # Телец 1° — 1-я двадашамша Тельца
    assert v.same_sign_in(lon, 12) is True     # знак D12 совпал с D1…
    assert v.is_vargottama(lon) is False       # …но варготтамой это не делает
    assert v.varga_sign(lon, 9) == 10          # в навамше он в Козероге

    for probe in (41.856, 270.31, 0.5):        # обобщение обязано совпадать с D9
        assert v.same_sign_in(probe, 9) is v.is_vargottama(probe)


# ═══════════════════════════════════════════════════════════
#  ПРОЧИЕ ВИБХАГИ
# ═══════════════════════════════════════════════════════════

@pytest.mark.parametrize("divisions,start_fn,step", [
    (3,  v._start_drekkana,   4),
    (7,  v._start_saptamsa,   1),
    (9,  v._start_navamsa,    1),
    (10, v._start_dasamsa,    1),
    (12, v._start_dwadasamsa, 1),
])
def test_vargas_match_exact_reference(divisions, start_fn, step):
    """Каждая варга совпадает с точным эталоном везде, кроме своих границ."""
    for lon in PROBES:
        if lon % Fraction(30, divisions) == 0:
            continue
        assert v.varga_sign(float(lon), divisions) == ref_varga_sign(
            lon, divisions, start_fn, step), (divisions, lon)


@pytest.mark.parametrize("lon,expected,why", [
    (0.0,   1, "1-я дреккана Овна — сам Овен"),
    (10.0,  5, "2-я дреккана Овна — 5-й от него, Лев"),
    (20.0,  9, "3-я дреккана Овна — 9-й от него, Стрелец"),
    (30.0,  2, "1-я дреккана Тельца — сам Телец"),
    (45.0,  6, "2-я дреккана Тельца — Дева"),
])
def test_drekkana_anchors(lon, expected, why):
    assert v.varga_sign(lon, 3) == expected, why


@pytest.mark.parametrize("lon,expected,why", [
    (0.0,   1, "нечётный знак Овен — саптамша от него самого"),
    (29.9,  7, "7-я саптамша Овна — Весы"),
    (30.0,  8, "чётный знак Телец — счёт с 7-го от него, Скорпион"),
    (59.9,  2, "7-я саптамша Тельца — от Скорпиона седьмой, снова Телец"),
])
def test_saptamsa_anchors(lon, expected, why):
    assert v.varga_sign(lon, 7) == expected, why


@pytest.mark.parametrize("lon,expected,why", [
    (0.0,   1, "нечётный Овен — дашамша от него самого"),
    (29.9, 10, "10-я дашамша Овна — Козерог"),
    (30.0, 10, "чётный Телец — счёт с 9-го от него, Козерог"),
    (59.9,  7, "10-я дашамша Тельца — Весы"),
])
def test_dasamsa_anchors(lon, expected, why):
    assert v.varga_sign(lon, 10) == expected, why


def test_dwadasamsa_starts_from_the_sign_itself():
    """D12: первая двадашамша каждого знака — сам этот знак."""
    for s in range(12):
        assert v.varga_sign(s * 30 + 0.5, 12) == s + 1
        assert v.varga_sign(s * 30 + 29.5, 12) == (s + 11) % 12 + 1


def test_hora_only_leo_and_cancer():
    """D2 населяет ровно два знака — Лев и Рак; это не дефект, а правило."""
    signs = {v.hora(i / 10)["sign_num"] for i in range(3600)}
    assert signs == {4, 5}


@pytest.mark.parametrize("lon,ruler,why", [
    (0.0,   "Солнце", "Овен нечётный — 1-я половина хора Солнца"),
    (14.99, "Солнце", "всё ещё 1-я половина Овна"),
    (15.0,  "Луна",   "2-я половина нечётного знака — хора Луны"),
    (30.0,  "Луна",   "Телец чётный — порядок обратный, 1-я половина Луны"),
    (45.0,  "Солнце", "2-я половина чётного знака — хора Солнца"),
])
def test_hora_parashari_rule(lon, ruler, why):
    assert v.hora(lon)["ruler"] == ruler, why


def test_hora_halves_split_evenly():
    """Хора Солнца и Луны делят круг пополам — по 180° каждой."""
    sun = sum(1 for i in range(36000) if v.hora(i / 100)["ruler"] == "Солнце")
    assert sun == 18000


def test_unsupported_varga_raises():
    """Незнакомая варга — явная ошибка, а не молча посчитанное число.

    Принцип модуля тот же, что у эфемерид (ARCHITECTURE.md §2): лучше
    отказ, чем правдоподобный неверный результат.
    """
    for bad in (4, 5, 6, 8, 16, 60, 0, -9):
        with pytest.raises(ValueError, match="не поддерживается"):
            v.varga_sign(100.0, bad)
        with pytest.raises(ValueError, match="не поддерживается"):
            v.varga_position(100.0, bad)


# ═══════════════════════════════════════════════════════════
#  УЗЛЫ
# ═══════════════════════════════════════════════════════════

def test_ketu_is_always_opposite_rahu_in_navamsa():
    """Кету = Раху + 180° → в навамше всегда 7-й знак от Раху.

    Не самоочевидно: +180° — это +54 навамши, и только потому, что
    54 mod 12 = 6, оппозиция узлов сохраняется и в D9. В варге с другим
    числом делений это уже неверно (см. следующий тест).
    """
    for i in range(3600):
        rahu = i / 10.0
        ketu = (rahu + 180.0) % 360
        assert v.varga_sign(ketu, 9) == (v.varga_sign(rahu, 9) + 5) % 12 + 1


@pytest.mark.parametrize("varga", [3, 7, 9, 10, 12])
def test_nodes_stay_opposite_in_all_supported_vargas(varga):
    """Оппозиция узлов сохраняется во всех варгах со сдвигом на знак.

    Свойство не универсальное, а следствие того, что 180° — это ровно 6
    знаков, номер части при сдвиге не меняется, а стартовое смещение у всех
    наших правил зависит либо от качества знака (период 3), либо от его
    чётности (период 2), либо ни от чего. Шесть делится и на 3, и на 2 —
    поэтому смещение одинаково у знака и у противоположного ему.

    Проверяем на всех пяти варгах, чтобы поймать правило, которое случайно
    сломает эту симметрию: у узлов она обязана быть.
    """
    for i in range(3600):
        rahu = i / 10.0
        ketu = (rahu + 180.0) % 360
        assert v.varga_sign(ketu, varga) == (v.varga_sign(rahu, varga) + 5) % 12 + 1


def test_nodes_share_the_same_hora():
    """А вот в D2 узлы попадают в ОДНУ хору, не в противоположные.

    Хора отображает знак на два знака, а не на двенадцать, так что понятия
    «оппозиция» в ней просто нет. Тест — страховка от попытки привести D2
    к остальным варгам «для единообразия».
    """
    for i in range(3600):
        rahu = i / 10.0
        assert v.hora((rahu + 180.0) % 360)["ruler"] == v.hora(rahu)["ruler"]


# ═══════════════════════════════════════════════════════════
#  СПРАВОЧНИК ЗНАКОВ — защита от расхождения с ядром
# ═══════════════════════════════════════════════════════════

def test_signs_match_nakshatra_calculator(swe):
    """Локальная таблица знаков совпадает с канонической в расчётном ядре.

    `varga.py` держит свою копию SIGNS, чтобы остаться чистой арифметикой и
    не тянуть swisseph. Копия — это риск разъехаться; тест его закрывает.
    """
    from nakshatra_calculator import SIGNS as CORE

    assert len(v.SIGNS) == len(CORE) == 12
    for mine, core in zip(v.SIGNS, CORE):
        assert mine["num"] == core["num"]
        assert mine["name"] == core["name"]
        assert mine["ru"] == core["ru"]
        assert mine["lord"] == core["lord"]


def test_quality_follows_element_triplicity():
    """Качества знаков идут строго по кругу: подвижный → неподвижный → двойственный."""
    order = ["movable", "fixed", "dual"]
    for i, s in enumerate(v.SIGNS):
        assert s["quality"] == order[i % 3], s["ru"]


# ═══════════════════════════════════════════════════════════
#  РЕАЛЬНЫЕ КАРТЫ — эталоны внешней сверки
# ═══════════════════════════════════════════════════════════
#
#  Долготы D1 берутся из нашего расчётного ядра, знаки D9 — эталон.
#  Смысл: поймать сдвиг эфемерид под верной схемой отсчёта. Саму схему
#  закрывает `test_pada_wheel_matches_content_base` (108 из 108 против
#  внешней таблицы), а здесь важно другое — если однажды поедет аянамша,
#  планета у границы 3°20' сменит знак навамши, и это будет видно.
#  Подробности — в docstring `varga.navamsa`.

# Карта A: 15.06.1990 14:30, Москва (55.7558 N, 37.6173 E), UTC+4 (MSD).
CHART_A = dict(year=1990, month=6, day=15, hour=14, minute=30,
               tz=4.0, lat=55.7558, lon=37.6173)

CHART_A_D9 = {
    "Лагна":    "Aries",
    "Солнце":   "Libra",
    "Луна":     "Aries",
    "Марс":     "Sagittarius",
    "Меркурий": "Aries",
    "Юпитер":   "Aries",
    "Венера":   "Scorpio",
    "Сатурн":   "Capricorn",
    "Раху":     "Taurus",
    "Кету":     "Scorpio",
}
CHART_A_VARGOTTAMA = ["Сатурн"]

# Карта B: 01.11.1985 08:00, Мумбаи (19.08 N, 72.88 E), UTC+5:30 (IST).
CHART_B = dict(year=1985, month=11, day=1, hour=8, minute=0,
               tz=5.5, lat=19.08, lon=72.88)

CHART_B_D9 = {
    "Лагна":    "Cancer",
    "Солнце":   "Aquarius",
    "Луна":     "Cancer",
    "Марс":     "Pisces",
    "Меркурий": "Virgo",
    "Юпитер":   "Taurus",
    "Венера":   "Leo",
    "Сатурн":   "Leo",
    "Раху":     "Leo",
    "Кету":     "Aquarius",
}
CHART_B_VARGOTTAMA = []


def _d9_of(birth):
    """Считает карту и возвращает знаки D9 английскими именами.

    Имена берутся из справочника по номеру знака: эталоны выше записаны так
    же, как их печатают внешние калькуляторы, — сверять глазами проще.
    """
    from nakshatra_calculator import calculate

    h = calculate(**birth)
    chart = v.navamsa_chart(h["planets"], h["lagna"]["sid_asc"])
    name = lambda n: v.SIGNS[n - 1]["name"]      # noqa: E731
    got = {p["name"]: name(p["sign_num"]) for p in chart["planets"]}
    got["Лагна"] = name(chart["lagna"]["sign_num"])
    return chart, got


@pytest.mark.parametrize("birth,expected,vargottama", [
    (CHART_A, CHART_A_D9, CHART_A_VARGOTTAMA),
    (CHART_B, CHART_B_D9, CHART_B_VARGOTTAMA),
])
def test_reference_charts_d9(swe, birth, expected, vargottama):
    chart, got = _d9_of(birth)
    assert got == expected
    assert chart["vargottama"] == vargottama


def test_navamsa_houses_count_from_navamsa_lagna(swe):
    """Дома навамши считаются от НАВАМША-лагны, а не от лагны D1.

    Ошибка соблазнительная: обе лагны лежат в одном ответе рядом. На карте A
    они разные (D1 Дева, D9 Овен), поэтому подмена сразу видна.
    """
    from nakshatra_calculator import calculate

    h = calculate(**CHART_A)
    chart, _ = _d9_of(CHART_A)
    d9_lagna = chart["lagna"]["sign_num"]
    d1_lagna = h["lagna"]["sign_num"]
    assert d9_lagna != d1_lagna, "карта-эталон выбрана так, чтобы лагны различались"

    for p in chart["planets"]:
        assert p["house"] == ((p["sign_num"] - d9_lagna) % 12) + 1


def test_horoscope_navamsa_block_carries_only_underivable_data(swe):
    """Блок для `/api/horoscope` компактен: без домов, владельцев и знаков D1.

    Он едет с КАЖДЫМ гороскопом, поэтому состав зафиксирован тестом — иначе
    в него незаметно вернётся всё, что фронт и так может вывести сам.
    """
    import json

    chart, _ = _d9_of(CHART_A)
    assert set(chart["planets"][0]) == {
        "name", "sign_num", "sign_ru", "pada_abs", "house", "vargottama"}
    assert set(chart["lagna"]) == {"sign_num", "sign_ru", "pada_abs", "vargottama"}
    size = len(json.dumps(chart, ensure_ascii=False).encode())
    assert size < 1600, f"блок навамши разросся до {size} Б"


def test_conftest_birth_matches_chart_a():
    """Карта A — та же контрольная карта, что в conftest (без дублей данных)."""
    from conftest import BIRTH_MOSCOW_1990

    assert BIRTH_MOSCOW_1990 == CHART_A


# ═══════════════════════════════════════════════════════════
#  СБОРКА ОТВЕТА
# ═══════════════════════════════════════════════════════════

def test_calc_vargas_shape(swe):
    """`calc_vargas` отдаёт все запрошенные карты и сводку варготтамы."""
    from nakshatra_calculator import calculate

    h = calculate(**CHART_A)
    res = v.calc_vargas(h["planets"], h["lagna"]["sid_asc"])

    assert set(res["charts"]) == {"D1", "D2", "D3", "D7", "D9", "D10", "D12"}
    for code, chart in res["charts"].items():
        assert len(chart["planets"]) == 9
        assert chart["source"], f"{code}: у каждой варги должно быть указано правило"
        if code == "D2":
            assert "houses" not in chart, "у хоры 12 домов не бывает"
        else:
            assert len(chart["houses"]) == 12

    assert res["vargottama"]["planets"] == CHART_A_VARGOTTAMA
    assert res["vargottama"]["lagna"] is False

    # D1 обязан вернуть исходные знаки один в один
    d1 = {p["name"]: p["sign_num"] for p in res["charts"]["D1"]["planets"]}
    assert d1 == {p["name"]: p["sign_num"] for p in h["planets"]}


def test_calc_vargas_subset(swe):
    from nakshatra_calculator import calculate

    h = calculate(**CHART_A)
    res = v.calc_vargas(h["planets"], h["lagna"]["sid_asc"], vargas=[9])
    assert set(res["charts"]) == {"D9"}


def test_calc_vargas_rejects_unknown(swe):
    from nakshatra_calculator import calculate

    h = calculate(**CHART_A)
    with pytest.raises(ValueError, match="не поддерживается"):
        v.calc_vargas(h["planets"], h["lagna"]["sid_asc"], vargas=[9, 60])


def test_pada_wheel_shape():
    """Круг 108 пад: нумерация накшатр и пад совпадает с сеткой навамш."""
    wheel = v.pada_wheel()
    assert len(wheel) == 108
    for i, p in enumerate(wheel):
        assert p["index"] == i
        assert p["nakshatra"] == i // 4 + 1
        assert p["pada"] == i % 4 + 1
        assert 1 <= p["d1_sign"] <= 12 and 1 <= p["d9_sign"] <= 12
        assert p["vargottama"] == (p["d1_sign"] == p["d9_sign"])
    # знак навамши идёт подряд по кругу
    assert [p["d9_sign"] for p in wheel[:13]] == list(range(1, 13)) + [1]


def test_pada_wheel_is_static():
    """Таблица не зависит ни от даты, ни от места — её можно кэшировать."""
    assert v.pada_wheel() == v.pada_wheel()


def test_pada_wheel_matches_content_base(content_dir):
    """Круг 108 пад совпадает с `content/padas.json` — независимым источником.

    Это самая сильная из имеющихся сверок схемы отсчёта, и она не зависит ни
    от одного онлайн-калькулятора. `padas.json` пришёл из разбора HTML-архива
    коллеги (см. docs/HANDOFF.md): таблица составлена человеком отдельно от
    нашего кода и содержит для каждой из 108 пад знак навамши, знак раши,
    владельца навамши и отметку варготтамы.

    Сверяются все четыре поля по всем 108 падам. Расхождение означает либо
    ошибку в схеме отсчёта, либо ошибку в контенте — и то и другое надо
    разбирать руками, а не подгонять.
    """
    import json

    ref = json.loads((content_dir / "padas.json").read_text(encoding="utf-8"))["padas"]
    mine = v.pada_wheel()
    assert len(ref) == len(mine) == 108

    for r, m in zip(ref, mine):
        where = f"накшатра {r['nak_no']} пада {r['pada']}"
        assert (r["nak_no"], r["pada"]) == (m["nakshatra"], m["pada"]), where
        assert r["rashi"] == m["d1_sign_ru"], f"{where}: знак раши"
        assert r["nav"] == m["d9_sign_ru"], f"{where}: знак навамши"
        assert r["vargottama"] == m["vargottama"], f"{where}: варготтама"
        assert r["nav_lord"] == v.SIGNS[m["d9_sign"] - 1]["lord"], f"{where}: владелец"
        # В контенте градусы округлены до трёх знаков (3.333 вместо 3.333333),
        # поэтому допуск — их шаг округления, а не машинная точность.
        assert abs(r["deg_abs"] - m["start_deg"]) < 5e-4, f"{where}: градус начала"
