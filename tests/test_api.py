"""Smoke-тесты HTTP-слоя: контракт ответов и часовые пояса.

Здесь не проверяется астрономия — на неё есть остальные файлы. Проверяется
то, что ломается при перекладывании данных: код ответа, набор ключей, связь
между эндпоинтами (один и тот же гороскоп должен давать одну и ту же даша).

Отдельная и самая содержательная часть — `/api/tz`. Летом 1990 года Москва
жила по UTC+4: декретный час плюс летнее время. Сервис, который подставит
привычные +3, сдвинет карту на час — и все накшатры у пограничных рождений
уедут молча. Это реальная ловушка, а не гипотетическая.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import BIRTH_MOSCOW_1990

МОСКВА = dict(lat=55.7558, lon=37.6173)
ДЕЛИ = dict(lat=28.6139, lon=77.2090)


@pytest.fixture(scope="module")
def client():
    """TestClient без контекстного менеджера — lifespan (и Mongo) не поднимаем.

    Публичные калькуляторы от базы не зависят: `main.lifespan` специально
    терпит её отсутствие. Тестам она не нужна и только замедляла бы прогон.
    """
    import main

    return TestClient(main.app)


# ═══════════════════════════════════════════════════════════════════════
#  /api/tz — исторические часовые пояса
# ═══════════════════════════════════════════════════════════════════════


def test_москва_летом_1990_это_utc_плюс_4(client):
    """Контрольная ловушка: декретное время + летнее = UTC+4.

    Именно это смещение стоит в BIRTH_MOSCOW_1990 и во всех сверках с
    Prokerala и Serennu. Ответ +3 означал бы карту, сдвинутую на час.
    """
    r = client.get("/api/tz", params=dict(**МОСКВА, year=1990, month=6, day=15,
                                          hour=14, minute=30))
    assert r.status_code == 200
    d = r.json()
    assert d["offset_hours"] == 4.0
    assert d["offset_str"] == "UTC+4"
    assert d["is_dst"] is True
    assert d["tz_name"] == "Europe/Moscow"


@pytest.mark.parametrize("дата,смещение,летнее", [
    ((1990, 1, 15), 3.0, False),   # зима 1990 — только декретный час
    ((1990, 6, 15), 4.0, True),    # лето 1990 — декретный + летнее
    ((1991, 6, 15), 3.0, True),    # декретный час отменён весной 1991
    ((2011, 7, 1), 4.0, False),    # «вечное лето» 2011-2014: +4 без флага DST
    ((2015, 7, 1), 3.0, False),    # возврат на постоянное «зимнее»
    ((2026, 7, 26), 3.0, False),   # сегодня
])
def test_история_московского_времени(дата, смещение, летнее, client):
    """Пять переломов московского времени за 36 лет — все обязаны отработать.

    Эталон — база tzdata (через pytz), а не наши представления о том, «как
    обычно». 1991 год показателен: летнее время есть, а смещение уже +3.
    """
    y, m, d = дата
    r = client.get("/api/tz", params=dict(**МОСКВА, year=y, month=m, day=d,
                                          hour=12, minute=0))
    assert r.status_code == 200
    assert r.json()["offset_hours"] == смещение, r.json()
    assert r.json()["is_dst"] is летнее


def test_дробное_смещение_дели(client):
    """Индия — UTC+5:30. Округление до целых часов сломало бы всю панчангу."""
    r = client.get("/api/tz", params=dict(**ДЕЛИ, year=2026, month=7, day=26))
    assert r.status_code == 200
    assert r.json()["offset_hours"] == 5.5
    assert r.json()["tz_name"] == "Asia/Kolkata"


def test_несуществующее_время_при_переводе_часов(client):
    """Ночь перевода стрелок вперёд: 02:30 26.03.1989 в Москве не существовало.

    Такое время нельзя молча «поправить» — ответ должен быть явной ошибкой.
    """
    r = client.get("/api/tz", params=dict(**МОСКВА, year=1989, month=3, day=26,
                                          hour=2, minute=30))
    assert r.status_code == 400


@pytest.mark.parametrize("lon,смещение", [(-140.0, -9.0), (-160.0, -11.0), (-30.0, -2.0)])
def test_середина_океана_даёт_морскую_зону(lon, смещение, client):
    """В открытом океане зоны нет — timezonefinder отдаёт номинальную Etc/GMT.

    Проверяем не «404», а осмысленность: смещение обязано соответствовать
    долготе (15° на час). Иначе рождение на корабле уехало бы на полсуток.
    """
    r = client.get("/api/tz", params=dict(lat=0.0, lon=lon,
                                          year=2026, month=7, day=26))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["offset_hours"] == смещение
    assert d["offset_hours"] == pytest.approx(round(lon / 15), abs=1.0)


# ═══════════════════════════════════════════════════════════════════════
#  /api/horoscope
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def гороскоп(client):
    r = client.post("/api/horoscope", json=BIRTH_MOSCOW_1990)
    assert r.status_code == 200, r.text
    return r.json()


def test_гороскоп_отдаёт_ожидаемые_ключи(гороскоп):
    """Контракт ответа: разделы, на которые опирается кабинет."""
    assert {"jd", "aya", "moon_sid", "moon_dms", "nk", "lagna", "planets",
            "boundary", "dasha_current"} <= set(гороскоп)
    assert {"num", "name", "ru", "lord", "pada"} <= set(гороскоп["nk"])
    assert {"sid_asc", "sign_num", "houses"} <= set(гороскоп["lagna"])
    assert len(гороскоп["lagna"]["houses"]) == 12


def test_девять_планет_с_полными_полями(гороскоп):
    """Семь грах плюс Раху и Кету, у каждой знак, дом, накшатра и ретро-флаг."""
    планеты = гороскоп["planets"]
    assert len(планеты) == 9
    assert [p["name"] for p in планеты][:2] == ["Солнце", "Луна"]
    for p in планеты:
        assert 1 <= p["sign_num"] <= 12
        assert 1 <= p["house"] <= 12
        assert 1 <= p["pada"] <= 4
        assert 0 <= p["sid"] < 360
        assert isinstance(p["retro"], bool)
        assert isinstance(p["is_stationary"], bool)
    # Солнце и Луна ретроградными не бывают никогда
    for p in планеты[:2]:
        assert p["retro"] is False


def test_дома_целознаковые_и_считаются_от_лагны(гороскоп):
    """Whole Sign: дом планеты = смещение её знака от знака лагны.

    Проверяется формулой, а не сравнением с записанным значением.
    """
    лагна = гороскоп["lagna"]["sign_num"]
    for p in гороскоп["planets"]:
        assert p["house"] == (p["sign_num"] - лагна) % 12 + 1, p["name"]
    знаки = [h["sign_num"] for h in гороскоп["lagna"]["houses"]]
    assert знаки == [(лагна - 1 + i) % 12 + 1 for i in range(12)]


def test_накшатра_согласована_с_долготой_луны(гороскоп):
    """Номер накшатры выводится из сидерической долготы, а не хранится отдельно."""
    ожидаемо = int(гороскоп["moon_sid"] / (360 / 27)) % 27 + 1
    assert гороскоп["nk"]["num"] == ожидаемо
    assert гороскоп["nk"]["pada"] == int(
        (гороскоп["moon_sid"] % (360 / 27)) / (360 / 27 / 4)) + 1


def test_текущая_даша_приезжает_вместе_с_гороскопом(гороскоп):
    """Плитка «маха-даша» работает от `/api/horoscope`, без второго запроса."""
    d = гороскоп["dasha_current"]
    assert d is not None, гороскоп.get("dasha_error")
    assert d["mahadasha"]["lord"]
    assert d["antardasha"]["lord"]
    assert d["label"] == f"{d['mahadasha']['lord']} / {d['antardasha']['lord']}"


# ═══════════════════════════════════════════════════════════════════════
#  /api/dasha
# ═══════════════════════════════════════════════════════════════════════


def test_dasha_отдаёт_дерево_и_сходится_с_гороскопом(client, гороскоп):
    """Полное дерево живёт отдельно, но обязано совпасть с плиткой гороскопа.

    Два эндпоинта считают от одной и той же Луны — расхождение означало бы,
    что где-то потерялись координаты или время рождения.
    """
    r = client.post("/api/dasha", json={**BIRTH_MOSCOW_1990, "levels": 2})
    assert r.status_code == 200, r.text
    d = r.json()
    assert {"nakshatra", "balance", "convention", "periods", "current"} <= set(d)
    assert len(d["periods"]) == 9
    assert all(len(p["sub"]) >= 1 for p in d["periods"])
    assert d["nakshatra"]["num"] == гороскоп["nk"]["num"]
    assert d["current"]["mahadasha"]["lord"] == гороскоп["dasha_current"]["mahadasha"]["lord"]
    assert d["convention"]["year_days"] == 365.25


def test_dasha_уровень_1_легче_уровня_2(client):
    """`levels` реально управляет глубиной — иначе экономия трафика мнимая."""
    один = client.post("/api/dasha", json={**BIRTH_MOSCOW_1990, "levels": 1})
    два = client.post("/api/dasha", json={**BIRTH_MOSCOW_1990, "levels": 2})
    assert один.status_code == два.status_code == 200
    assert all(p["sub"] == [] for p in один.json()["periods"])
    assert len(два.content) > len(один.content) * 3


# ═══════════════════════════════════════════════════════════════════════
#  /api/panchang
# ═══════════════════════════════════════════════════════════════════════


def test_panchang_отдаёт_титхи_йоги_караны_и_дни(client):
    """Задачи 2.12: ключи `yogas` и `karanas` добавлены, прежние не потеряны."""
    r = client.post("/api/panchang", json=dict(
        date_start="2026-07-25", date_end="2026-07-27", tz=3.0, **МОСКВА))
    assert r.status_code == 200, r.text
    d = r.json()
    assert {"tithis", "yogas", "karanas", "days"} <= set(d)
    assert len(d["days"]) == 3
    assert d["tithis"] and d["yogas"] and d["karanas"]

    for t in d["tithis"]:
        assert 1 <= t["num"] <= 30
        assert t["paksha"] in ("Шукла", "Кришна")
    for y in d["yogas"]:
        assert 1 <= y["num"] <= 27
        assert isinstance(y["is_stop"], bool)
    for k in d["karanas"]:
        assert 1 <= k["num"] <= 11
        assert isinstance(k["is_bhadra"], bool)
    for день in d["days"]:
        assert len(день["muhurtas"]) == 30
        assert len(день["horas"]) == 24


def test_panchang_на_полярной_широте_не_падает(client):
    """Мурманск в июне — полярный день: `rise_trans` не находит восхода.

    Ответ должен остаться валидным (сработает запасной расчёт по Meeus),
    а не превратиться в 500.
    """
    r = client.post("/api/panchang", json=dict(
        date_start="2026-06-21", date_end="2026-06-21", tz=3.0,
        lat=68.9585, lon=33.0827))
    assert r.status_code == 200, r.text
    день = r.json()["days"][0]
    assert len(день["muhurtas"]) == 30


# ═══════════════════════════════════════════════════════════════════════
#  /api/calendar
# ═══════════════════════════════════════════════════════════════════════


def test_calendar_отдаёт_накшатры_с_падами(client):
    """Транзиты Луны: накшатры за период, у каждой — пады со временем."""
    r = client.post("/api/calendar", json=dict(
        date_start="2026-07-25", date_end="2026-07-28", tz=3.0, **МОСКВА))
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d, list) and len(d) >= 3
    for запись in d:
        assert 1 <= запись["nk_num"] <= 27
        assert запись["padas"]
        assert all(1 <= p["pada"] <= 4 for p in запись["padas"])
        assert запись["dt_start"] < запись["dt_end"]
    # Накшатры сменяются подряд по кругу — пропуск означал бы промах поиска
    for a, b in zip(d, d[1:]):
        assert b["nk_num"] == a["nk_num"] % 27 + 1
        assert a["dt_end"] == b["dt_start"]


# ═══════════════════════════════════════════════════════════════════════
#  /api/sade-sati
# ═══════════════════════════════════════════════════════════════════════


def test_sade_sati_отдаёт_циклы_и_фазы(client, гороскоп):
    """Сад-сати строится от знака натальной Луны — он же в гороскопе.

    Три фазы идут по знакам 12-1-2 от Луны, Аштама — 8-й, Кантака — 4-й.
    Это определения, поэтому проверяются формулой.
    """
    r = client.post("/api/sade-sati", json=BIRTH_MOSCOW_1990)
    assert r.status_code == 200, r.text
    d = r.json()
    assert {"natal_moon", "phase_signs", "sade_sati_cycles",
            "ashtama_shani_periods", "kantaka_shani_periods", "current"} <= set(d)

    луна = d["natal_moon"]["sign_num"]
    assert луна == int(гороскоп["moon_sid"] / 30) + 1
    assert d["phase_signs"]["aarohini"]["sign_num"] == (луна - 2) % 12 + 1
    assert d["phase_signs"]["madhya"]["sign_num"] == луна
    assert d["phase_signs"]["avarohini"]["sign_num"] == луна % 12 + 1
    assert d["ashtama_sign"]["sign_num"] == (луна + 6) % 12 + 1
    assert d["kantaka_sign"]["sign_num"] == (луна + 2) % 12 + 1


def test_sade_sati_цикл_длится_около_семи_с_половиной_лет(client):
    """Название говорит само: «семь с половиной». Сатурн идёт знак ~2.5 года.

    Разброс задают ретроградные возвраты, поэтому рамка широкая — но цикл в
    два года или в двадцать означал бы ошибку в поиске переходов.
    """
    r = client.post("/api/sade-sati", json=BIRTH_MOSCOW_1990)
    циклы = r.json()["sade_sati_cycles"]
    assert len(циклы) >= 3, "за 120 лет Сад-сати обязана прийти хотя бы трижды"
    целые = [c for c in циклы if not c["truncated_start"] and not c["truncated_end"]]
    assert целые
    for c in целые:
        assert 6.5 <= c["duration_years"] <= 9.0, c["duration_years"]


# ═══════════════════════════════════════════════════════════════════════
#  Общее
# ═══════════════════════════════════════════════════════════════════════


def test_корень_отвечает(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_debug_показывает_используемую_аянамшу(client):
    """Диагностика обязана печатать то же число, что вычитают модули.

    Иначе при разборе расхождений она уводит в сторону — ровно это и мешало
    поймать дефект №1.
    """
    import swisseph as swe
    import nakshatra_calculator as nc

    r = client.get("/api/debug")
    assert r.status_code == 200
    d = r.json()
    assert d["sidm_lahiri_const"] == int(swe.SIDM_LAHIRI)
    jd = swe.julday(*[int(x) for x in d["aya_now_date"][:10].split("-")],
                    int(d["aya_now_date"][11:13]) + int(d["aya_now_date"][14:16]) / 60)
    assert d["aya_now"] == pytest.approx(nc.get_aya(jd), abs=1e-5)


@pytest.mark.parametrize("путь,тело", [
    ("/api/horoscope", {"year": 1990}),                       # нет обязательных полей
    ("/api/panchang", {"date_start": "не дата", "tz": 3.0}),
    ("/api/dasha", {**BIRTH_MOSCOW_1990, "levels": 99}),      # levels вне 1..5
])
def test_мусор_на_входе_не_даёт_двухсотку(путь, тело, client):
    """Некорректный запрос — 4xx или 5xx, но не «успешный» пустой ответ."""
    r = client.post(путь, json=тело)
    assert r.status_code >= 400, r.text
