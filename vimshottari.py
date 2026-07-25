"""
╔═══════════════════════════════════════════════════════════════════╗
║   ВИМШОТТАРИ-ДАША — 120-летний цикл планетарных периодов          ║
║   Маха-даши → антар-даши (→ пратьянтар, если попросить)           ║
╚═══════════════════════════════════════════════════════════════════╝

Вимшоттари («сто двадцать») — основная система даш в джйотише. Жизнь делится
на девять больших периодов (маха-даш) по числу планет-управителей; сумма их
сроков — ровно 120 лет.

Что задаёт расчёт:
  • Стартового управителя — накшатра Луны в момент рождения.
    Накшатры привязаны к управителям циклически, с повтором каждые 9:
    Ашвини→Кету, Бхарани→Венера, Криттика→Солнце, … Ашлеша→Меркурий,
    Магха→снова Кету и так далее.
  • Баланс на момент рождения — какая доля стартовой маха-даши ещё не
    израсходована. Она равна непройденной доле накшатры Луны:
        баланс_лет = (1 - пройдено/13°20') × срок_управителя
  • Антар-даши — девять подпериодов внутри каждой маха-даши, в той же
    последовательности, начиная с управителя самой маха-даши:
        длительность_антар = длительность_маха × срок_антар_управителя / 120
    Правило применяется рекурсивно, поэтому уровни глубже (пратьянтар и т.д.)
    считаются той же формулой — см. параметр `levels`.

Модуль — чистая функция «долгота Луны + дата рождения → структура периодов».
Ни эфемерид, ни БД, ни сети: сидерическую долготу Луны считает
`nakshatra_calculator.py`, сюда она приходит уже готовым числом
(см. docs/ARCHITECTURE.md §2).

Сверка с внешним калькулятором (AstroSage, Dasha Calculator, аянамша Лахири).
Карта 17.05.1990 14:30, Ставрополь, UTC+4. Чтобы сравнивать именно арифметику
даш, а не эфемериды, на вход подавалась Луна, посчитанная самим AstroSage
(Козерог 27°53'19" = 297.888611°):
    баланс           наш 4 г 7 мес 9.2 дн   ↔  AstroSage «MARS 4 Y 7 M 9 D»
    сроки маха-даш   1683 / 6574 / 5844 / 6939 / 6209 / 2556 / 7305 / 2191 / 3652 сут
                     = 18×365.25, 16×365.25, … — год 365.25 подтверждён
    антар-даши Раху  все девять совпали с точностью до 1 суток (AstroSage
                     печатает только дату, без времени)
    состав первой (урезанной) маха-даши совпал: антар-даши Марс/Марс и
                     Марс/Раху истекли до рождения, первой идёт Марс/Юпитер
    текущий период   Юпитер / Марс — совпало
Остаточный сдвиг ~1.5 суток на длинном плече объясняется тем, что AstroSage
прибавляет целые календарные годы/месяцы/дни, а мы — точное число суток.
Мы сознательно оставили точный счёт суток: он монотонен и не зависит от
длины конкретного месяца.

Отдельно: наша Луна (Swiss Ephemeris) даёт 297.8977° против 297.8886° у
AstroSage — расхождение 33", это вопрос эфемерид/ΔT в nakshatra_calculator.py,
а не этого модуля; на реальной карте оно смещает даты ещё на ~1.6 суток.

Запуск:
    python vimshottari.py --chart 1990 5 17 14 30 297.8977
    python vimshottari.py --selftest
"""

from datetime import datetime, timedelta
from typing import List, Optional

from utils import NAKSHATRAS

# ═══════════════════════════════════════════════════════════
#  КОНСТАНТЫ СИСТЕМЫ
# ═══════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────
#  ДЛИНА ГОДА — соглашение, влияющее на даты за десятилетия вперёд.
#
#  В традиции спорят о двух вариантах:
#    • савана-год 360 суток («астрологический», по числу градусов зодиака);
#    • солнечный год ≈ 365,25 суток (юлианский).
#  Расхождение накапливается быстро: к 40 годам жизни разница между
#  вариантами превышает полгода.
#
#  Берём 365.25 — юлианский год. Причины:
#    1) это выбор подавляющего большинства современных калькуляторов и
#       программ (Jagannatha Hora, drikpanchang, astro-seek, Parashara's
#       Light), и наши даты обязаны совпадать с тем, что человек увидит
#       при проверке в стороннем сервисе;
#    2) вариант 360 суток даёт заметно более ранние даты и в готовых
#       продуктах встречается только как отдельная опция, не как default.
#  Если когда-нибудь понадобится савана-год — менять только эту константу,
#  вся остальная арифметика от неё производна.
# ──────────────────────────────────────────────────────────────────────
YEAR_DAYS = 365.25

TOTAL_YEARS = 120.0          # полный цикл Вимшоттари
NK_SIZE = 360.0 / 27         # 13°20' — размер накшатры

# Последовательность управителей и их сроки в годах.
# `id` — ключ для сопоставления с трактовками во фронтовом контенте
# (frontend-nuxt/content/yogakarma.json → dashas.planets[].id и
#  antardashas.antar[<маха>][<антар>]); `lord` — русское имя, совпадает
# с полем `lord` в utils.NAKSHATRAS и с yogakarma.json → *.name.
DASHA_SEQUENCE = [
    {"lord": "Кету",     "id": "ketu",    "en": "Ketu",    "years": 7},
    {"lord": "Венера",   "id": "shukra",  "en": "Venus",   "years": 20},
    {"lord": "Солнце",   "id": "surya",   "en": "Sun",     "years": 6},
    {"lord": "Луна",     "id": "chandra", "en": "Moon",    "years": 10},
    {"lord": "Марс",     "id": "mangala", "en": "Mars",    "years": 7},
    {"lord": "Раху",     "id": "rahu",    "en": "Rahu",    "years": 18},
    {"lord": "Юпитер",   "id": "guru",    "en": "Jupiter", "years": 16},
    {"lord": "Сатурн",   "id": "shani",   "en": "Saturn",  "years": 19},
    {"lord": "Меркурий", "id": "budha",   "en": "Mercury", "years": 17},
]

# Названия уровней вложенности (1 — маха-даша)
LEVEL_NAMES = ["Махадаша", "Антардаша", "Пратьянтардаша", "Сукшмадаша", "Пранадаша"]
MAX_LEVELS = len(LEVEL_NAMES)

# Больше 40 маха-даш (~500 лет) не строим ни при каком `until` — защита от
# бесконечного цикла, если вызывающий передаст абсурдную дату.
MAX_MAHADASHAS = 40

# ── Проверки согласованности справочников (падают на импорте, а не в проде) ──
assert sum(d["years"] for d in DASHA_SEQUENCE) == TOTAL_YEARS, \
    "Сумма сроков управителей должна быть ровно 120 лет"
assert len(DASHA_SEQUENCE) == 9
for _i, _nk in enumerate(NAKSHATRAS):
    assert _nk["lord"] == DASHA_SEQUENCE[_i % 9]["lord"], (
        f"Накшатра {_nk['name']} в utils.NAKSHATRAS имеет управителя "
        f"{_nk['lord']}, а цикл Вимшоттари даёт {DASHA_SEQUENCE[_i % 9]['lord']}"
    )

# ═══════════════════════════════════════════════════════════
#  НАКШАТРА ЛУНЫ И БАЛАНС ДАШИ
# ═══════════════════════════════════════════════════════════


def nakshatra_of(moon_sid_lon: float) -> dict:
    """Накшатра по сидерической долготе + доля, пройденная внутри неё.

    Возвращает справочные поля накшатры (num/name/ru/lord/gana/symbol),
    паду 1-4 и `elapsed_fraction` ∈ [0, 1) — сколько накшатры уже пройдено.
    Ровно на границе (`elapsed_fraction == 0`) накшатра считается новой,
    то есть управитель уже сменился, а баланс равен полному сроку.
    """
    lon = float(moon_sid_lon) % 360.0
    idx = int(lon / NK_SIZE) % 27
    deg_in_nk = lon - idx * NK_SIZE
    # Защита от накопленной ошибки округления у самой границы
    if deg_in_nk < 0:
        deg_in_nk = 0.0
    elif deg_in_nk >= NK_SIZE:
        deg_in_nk = NK_SIZE - 1e-12

    nk = NAKSHATRAS[idx]
    return {
        **nk,
        "sid_lon":              round(lon, 6),
        "pada":                 int(deg_in_nk / (NK_SIZE / 4)) + 1,
        "degrees_in_nakshatra": round(deg_in_nk, 6),
        "elapsed_fraction":     deg_in_nk / NK_SIZE,
    }


def _lord_index(lord: str) -> int:
    """Позиция управителя в последовательности Вимшоттари (0-8)."""
    for i, d in enumerate(DASHA_SEQUENCE):
        if d["lord"] == lord:
            return i
    raise ValueError(f"Неизвестный управитель даши: {lord!r}")


# ═══════════════════════════════════════════════════════════
#  ПОСТРОЕНИЕ ДЕРЕВА ПЕРИОДОВ
#
#  Внутри всё считается в «годах от виртуального начала цикла» — момента,
#  когда стартовая маха-даша началась бы, роди человек ровно на границе
#  накшатры. Рождение приходится на `elapsed_years` этой шкалы. Такой
#  подход даёт точные границы (складываются целые сроки управителей)
#  и позволяет корректно урезать первый период по дате рождения.
# ═══════════════════════════════════════════════════════════


def _build_subtree(lord_idx: int, y_start: float, span: float,
                   level: int, max_level: int) -> List[dict]:
    """Девять подпериодов внутри отрезка [y_start, y_start+span] в годах.

    Порядок — от управителя родительского периода, длительность каждого
    пропорциональна его сроку: span × срок / 120.
    """
    if level > max_level:
        return []
    nodes = []
    y = y_start
    for k in range(9):
        li = (lord_idx + k) % 9
        d = DASHA_SEQUENCE[li]
        sub_span = span * d["years"] / TOTAL_YEARS
        nodes.append({
            "_lord_idx": li,
            "_y0":       y,
            "_y1":       y + sub_span,
            "level":     level,
            "sub":       _build_subtree(li, y, sub_span, level + 1, max_level),
        })
        y += sub_span
    # Последнюю границу подтягиваем к родительской: иначе накопленная ошибка
    # сложения девяти дробей даёт расхождение в доли секунды.
    if nodes:
        nodes[-1]["_y1"] = y_start + span
    return nodes


def _clip(nodes: List[dict], y_from: float) -> List[dict]:
    """Отбрасывает периоды, целиком прошедшие до `y_from`; пересекающий —
    урезает слева. Нужно для первой маха-даши: к рождению часть её (и часть
    её антар-даш) уже прошла.
    """
    out = []
    for n in nodes:
        if n["_y1"] <= y_from:
            continue
        if n["_y0"] < y_from:
            n["_y0"] = y_from
            n["_truncated_start"] = True
            n["sub"] = _clip(n["sub"], y_from)
        out.append(n)
    return out


def _finalize(nodes: List[dict], epoch: datetime, y_now: Optional[float],
              parent_lord_idx: Optional[int]) -> List[dict]:
    """Годы-от-эпохи → публичная структура с датами и признаком is_current."""
    out = []
    for n in nodes:
        d = DASHA_SEQUENCE[n["_lord_idx"]]
        span = n["_y1"] - n["_y0"]
        is_current = (y_now is not None and n["_y0"] <= y_now < n["_y1"])
        parent = DASHA_SEQUENCE[parent_lord_idx] if parent_lord_idx is not None else None

        item = {
            "level":           n["level"],
            "level_name":      LEVEL_NAMES[n["level"] - 1],
            "lord":            d["lord"],
            "lord_id":         d["id"],
            "lord_en":         d["en"],
            "parent_lord":     parent["lord"] if parent else None,
            "parent_lord_id":  parent["id"] if parent else None,
            "dt_start":        _to_dt(epoch, n["_y0"]),
            "dt_end":          _to_dt(epoch, n["_y1"]),
            "duration_years":  round(span, 6),
            "duration_days":   round(span * YEAR_DAYS, 2),
            "full_years":      d["years"],
            "truncated_start": n.get("_truncated_start", False),
            "is_current":      is_current,
            "sub":             _finalize(n["sub"], epoch, y_now, n["_lord_idx"]),
        }
        if is_current:
            item["progress"] = round((y_now - n["_y0"]) / span, 4) if span > 0 else 0.0
            item["years_remaining"] = round(n["_y1"] - y_now, 4)
            item["days_remaining"] = round((n["_y1"] - y_now) * YEAR_DAYS, 1)
        out.append(item)
    return out


def _to_dt(epoch: datetime, years: float) -> datetime:
    """Годы от эпохи → datetime. Год = YEAR_DAYS суток (см. комментарий выше)."""
    return epoch + timedelta(days=years * YEAR_DAYS)


def _find_current(nodes: List[dict]) -> Optional[dict]:
    """Самый глубокий активный период — маха/антар/… — плоской цепочкой."""
    for n in nodes:
        if n["is_current"]:
            deeper = _find_current(n["sub"])
            return {"period": n, "deeper": deeper}
    return None


def _current_chain(nodes: List[dict]) -> List[dict]:
    """Цепочка активных периодов сверху вниз: [маха, антар, …]."""
    chain = []
    cur = nodes
    while True:
        found = None
        for n in cur:
            if n["is_current"]:
                found = n
                break
        if found is None:
            break
        chain.append(found)
        cur = found["sub"]
    return chain


# ═══════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════


def calc_vimshottari(moon_sid_lon: float,
                     birth_dt: datetime,
                     levels: int = 2,
                     until: Optional[datetime] = None,
                     as_of: Optional[datetime] = None) -> dict:
    """Периоды Вимшоттари-даши от натальной Луны.

    Параметры
    ---------
    moon_sid_lon : сидерическая долгота Луны при рождении, градусы 0-360
                   (аянамша Лахири — та же, что во всём проекте).
    birth_dt     : дата и время рождения. Наивный datetime; все даты в ответе
                   возвращаются в той же шкале, что и он. Передали местное
                   время — получите местное, передали UTC — получите UTC.
    levels       : глубина вложенности. 1 — только маха-даши, 2 — плюс
                   антар-даши (по умолчанию). Формула рекурсивна, поэтому
                   3 и глубже (пратьянтар, сукшма, прана) тоже работают,
                   но в продукте не используются: 3-й уровень — это уже
                   729 периодов на цикл.
    until        : до какого момента строить. По умолчанию — один полный
                   круг из девяти маха-даш (первая урезана балансом).
                   Если дата дальше — круг управителей продолжается.
    as_of        : момент, на который определяется активный период
                   (`is_current`). По умолчанию — «сейчас».

    Возвращает
    ----------
    dict со следующими разделами:

      input       — эхо аргументов (moon_sid_lon, birth_dt, levels, until)
      nakshatra   — num, name, ru, lord, pada, degrees_in_nakshatra,
                    elapsed_fraction (доля накшатры, пройденная к рождению)
      balance     — баланс стартовой маха-даши: lord, lord_id, full_years,
                    elapsed_years, duration_years, duration_days, dt_end
      convention  — year_days, year_note, cycle_years, cycle_start (виртуальное
                    начало стартовой маха-даши), cycle_end, sequence
      periods     — список маха-даш, каждая:
                      level, level_name, lord, lord_id, lord_en,
                      parent_lord, parent_lord_id (None для маха-даши),
                      dt_start, dt_end, duration_years, duration_days,
                      full_years (полный срок управителя по таблице),
                      truncated_start (True у первой — урезана рождением),
                      is_current, sub — список антар-даш той же структуры
                      (у активного периода дополнительно progress,
                       years_remaining, days_remaining)
      current     — as_of, mahadasha, antardasha, deeper, label («Раху / Венера»)
      method      — краткое описание метода

    `lord_id` совпадает с ключами frontend-nuxt/content/yogakarma.json:
    dashas.planets[].id и antardashas.antar[<lord_id махи>][<lord_id антара>].

    Ошибки
    ------
    ValueError — некорректная долгота, `levels` вне 1..5, `until` раньше
    рождения.
    """
    # ── валидация ────────────────────────────────────────────────────
    try:
        lon = float(moon_sid_lon)
    except (TypeError, ValueError):
        raise ValueError(f"moon_sid_lon должна быть числом, получено {moon_sid_lon!r}")
    if lon != lon or lon in (float("inf"), float("-inf")):
        raise ValueError("moon_sid_lon должна быть конечным числом")
    if not isinstance(birth_dt, datetime):
        raise ValueError("birth_dt должен быть datetime")
    if not isinstance(levels, int) or not (1 <= levels <= MAX_LEVELS):
        raise ValueError(f"levels должен быть целым от 1 до {MAX_LEVELS}")
    if until is not None and until <= birth_dt:
        raise ValueError("until должна быть позже даты рождения")

    # ── стартовый управитель и баланс ────────────────────────────────
    nk = nakshatra_of(lon)
    start_idx = _lord_index(nk["lord"])
    start_years = DASHA_SEQUENCE[start_idx]["years"]

    elapsed_fraction = nk["elapsed_fraction"]
    elapsed_years = elapsed_fraction * start_years        # «съедено» до рождения
    balance_years = start_years - elapsed_years           # остаток на рождение

    # Виртуальное начало цикла — момент, когда стартовая маха-даша началась бы,
    # роди человек ровно на границе накшатры. От него ведём всю шкалу лет,
    # рождение приходится на отметку elapsed_years.
    epoch = birth_dt - timedelta(days=elapsed_years * YEAR_DAYS)

    # ── сколько маха-даш строить ─────────────────────────────────────
    n_maha = 9
    if until is not None:
        until_years = (until - epoch).total_seconds() / 86400.0 / YEAR_DAYS
        y = 0.0
        n_maha = 0
        while n_maha < MAX_MAHADASHAS:
            y += DASHA_SEQUENCE[(start_idx + n_maha) % 9]["years"]
            n_maha += 1
            if y >= until_years and n_maha >= 9:
                break

    # ── дерево периодов ──────────────────────────────────────────────
    maha_nodes = []
    y = 0.0
    for k in range(n_maha):
        li = (start_idx + k) % 9
        span = float(DASHA_SEQUENCE[li]["years"])
        maha_nodes.append({
            "_lord_idx": li,
            "_y0":       y,
            "_y1":       y + span,
            "level":     1,
            "sub":       _build_subtree(li, y, span, 2, levels),
        })
        y += span

    # Урезаем всё, что прошло до рождения (первая маха-даша и её подпериоды)
    maha_nodes = _clip(maha_nodes, elapsed_years)

    as_of = as_of or datetime.now()
    y_now = (as_of - epoch).total_seconds() / 86400.0 / YEAR_DAYS

    periods = _finalize(maha_nodes, epoch, y_now, None)
    chain = _current_chain(periods)

    # ── сводка по активному моменту ──────────────────────────────────
    def _brief(p: Optional[dict]) -> Optional[dict]:
        if p is None:
            return None
        return {
            "lord":            p["lord"],
            "lord_id":         p["lord_id"],
            "lord_en":         p["lord_en"],
            "parent_lord":     p["parent_lord"],
            "parent_lord_id":  p["parent_lord_id"],
            "level":           p["level"],
            "level_name":      p["level_name"],
            "dt_start":        p["dt_start"],
            "dt_end":          p["dt_end"],
            "duration_years":  p["duration_years"],
            "progress":        p.get("progress"),
            "years_remaining": p.get("years_remaining"),
            "days_remaining":  p.get("days_remaining"),
        }

    current = {
        "as_of":      as_of,
        "mahadasha":  _brief(chain[0] if len(chain) > 0 else None),
        "antardasha": _brief(chain[1] if len(chain) > 1 else None),
        "deeper":     [_brief(p) for p in chain[2:]],
        # Строка вида «Раху / Венера» — удобна для заголовка на фронте
        "label":      " / ".join(p["lord"] for p in chain) if chain else None,
    }

    return {
        "input": {
            "moon_sid_lon": round(lon, 6),
            "birth_dt":     birth_dt,
            "levels":       levels,
            "until":        until,
        },
        "nakshatra": {
            "num":                  nk["num"],
            "name":                 nk["name"],
            "ru":                   nk["ru"],
            "lord":                 nk["lord"],
            "pada":                 nk["pada"],
            "degrees_in_nakshatra": nk["degrees_in_nakshatra"],
            "elapsed_fraction":     round(elapsed_fraction, 8),
        },
        "balance": {
            # Баланс стартовой маха-даши на момент рождения
            "lord":           DASHA_SEQUENCE[start_idx]["lord"],
            "lord_id":        DASHA_SEQUENCE[start_idx]["id"],
            "full_years":     start_years,
            "elapsed_years":  round(elapsed_years, 6),
            "duration_years": round(balance_years, 6),
            "duration_days":  round(balance_years * YEAR_DAYS, 2),
            "dt_end":         _to_dt(epoch, start_years),
        },
        "convention": {
            "year_days":     YEAR_DAYS,
            "year_note":     "юлианский год 365.25 суток (стандарт JHora / "
                             "drikpanchang / astro-seek); альтернатива — "
                             "савана-год 360 суток",
            "cycle_years":   TOTAL_YEARS,
            "cycle_start":   epoch,   # виртуальное начало стартовой маха-даши
            "cycle_end":     _to_dt(epoch, sum(d["years"] for d in DASHA_SEQUENCE)),
            "sequence":      [{"lord": d["lord"], "id": d["id"], "years": d["years"]}
                              for d in DASHA_SEQUENCE],
        },
        "periods": periods,
        "current": current,
        "method":  "Vimshottari (120 лет), стартовый управитель — по накшатре "
                   "натальной Луны (Лахири)",
    }


# ═══════════════════════════════════════════════════════════
#  ВЫВОД РЕЗУЛЬТАТА
# ═══════════════════════════════════════════════════════════

def print_result(res: dict, show_sub: bool = True) -> None:
    W = 74
    print("\n" + "═" * W)
    print("  ВИМШОТТАРИ-ДАША")
    print("═" * W)
    nk = res["nakshatra"]
    i  = res["input"]
    b  = res["balance"]
    print(f"  Рождение   : {i['birth_dt']:%Y-%m-%d %H:%M}")
    print(f"  Луна       : {i['moon_sid_lon']:.4f}°  →  {nk['ru']} ({nk['name']}), пада {nk['pada']}")
    print(f"  Управитель : {nk['lord']}   пройдено накшатры {nk['elapsed_fraction']*100:.3f}%")
    print(f"  Баланс     : {b['duration_years']:.4f} лет ({b['duration_days']:.1f} дн) "
          f"→ до {b['dt_end']:%Y-%m-%d}")
    print(f"  Год        : {res['convention']['year_days']} суток")
    print()
    print("─" * W)
    for p in res["periods"]:
        mark = " ← сейчас" if p["is_current"] else ""
        trunc = " (урезана рождением)" if p["truncated_start"] else ""
        print(f"  {p['lord']:<10} {p['dt_start']:%Y-%m-%d} → {p['dt_end']:%Y-%m-%d}  "
              f"{p['duration_years']:>7.3f} лет{trunc}{mark}")
        if show_sub:
            for s in p["sub"]:
                smark = " ←" if s["is_current"] else ""
                print(f"      {s['lord']:<10} {s['dt_start']:%Y-%m-%d} → "
                      f"{s['dt_end']:%Y-%m-%d}  {s['duration_years']:>6.3f}{smark}")
            if p["sub"]:
                print()
    c = res["current"]
    print("─" * W)
    if c["mahadasha"]:
        m = c["mahadasha"]
        print(f"  На {c['as_of']:%Y-%m-%d}: {c['label']}")
        print(f"    махадаша  {m['lord']:<10} до {m['dt_end']:%Y-%m-%d}  "
              f"(пройдено {m['progress']*100:.1f}%)")
        if c["antardasha"]:
            a = c["antardasha"]
            print(f"    антардаша {a['lord']:<10} до {a['dt_end']:%Y-%m-%d}  "
                  f"({a['days_remaining']:.0f} дн осталось)")
    else:
        print("  На указанный момент активного периода в выборке нет")
    print("═" * W + "\n")


# ═══════════════════════════════════════════════════════════
#  САМОПРОВЕРКА
# ═══════════════════════════════════════════════════════════

def _selftest() -> None:
    """Инварианты системы: суммы, границы накшатр, крайние положения Луны."""
    ok = 0

    # 1. Сумма сроков управителей = 120 лет
    assert sum(d["years"] for d in DASHA_SEQUENCE) == 120
    ok += 1

    # 2. Полный цикл маха-даш = ровно 120 лет от виртуального начала
    r = calc_vimshottari(297.8977, datetime(1990, 5, 17, 14, 30), levels=2)
    span = (r["convention"]["cycle_end"] - r["convention"]["cycle_start"])
    assert abs(span.total_seconds() - 120 * YEAR_DAYS * 86400) < 1.0, span
    ok += 1

    # 3. Сумма антар-даш внутри каждой (неурезанной) маха-даши = её длительности
    for p in r["periods"]:
        if p["truncated_start"] or not p["sub"]:
            continue
        s = sum((x["dt_end"] - x["dt_start"]).total_seconds() for x in p["sub"])
        t = (p["dt_end"] - p["dt_start"]).total_seconds()
        assert abs(s - t) < 1.0, (p["lord"], s, t)
        # и границы стыкуются без дыр
        assert p["sub"][0]["dt_start"] == p["dt_start"]
        assert p["sub"][-1]["dt_end"] == p["dt_end"]
        for a, b in zip(p["sub"], p["sub"][1:]):
            assert a["dt_end"] == b["dt_start"]
    ok += 1

    # 4. Маха-даши стыкуются без дыр и идут в порядке Вимшоттари
    for a, b in zip(r["periods"], r["periods"][1:]):
        assert a["dt_end"] == b["dt_start"], (a["lord"], b["lord"])
        ia, ib = _lord_index(a["lord"]), _lord_index(b["lord"])
        assert ib == (ia + 1) % 9
    ok += 1

    # 5. Первая маха-даша урезана и её антар-даши тоже: сумма = урезанной длине
    p0 = r["periods"][0]
    assert p0["truncated_start"]
    assert p0["dt_start"] == datetime(1990, 5, 17, 14, 30)
    s = sum((x["dt_end"] - x["dt_start"]).total_seconds() for x in p0["sub"])
    t = (p0["dt_end"] - p0["dt_start"]).total_seconds()
    assert abs(s - t) < 1.0, (s, t)
    ok += 1

    # 6. Граница накшатры: ровно на стыке управитель уже новый, баланс полный
    bd = datetime(2000, 1, 1, 12, 0)
    for k in range(27):
        r0 = calc_vimshottari(k * NK_SIZE, bd, levels=1)
        assert r0["nakshatra"]["num"] == k + 1, (k, r0["nakshatra"]["num"])
        assert r0["nakshatra"]["lord"] == NAKSHATRAS[k]["lord"]
        assert abs(r0["balance"]["duration_years"] - r0["balance"]["full_years"]) < 1e-9
        assert not r0["periods"][0]["truncated_start"]
        assert r0["periods"][0]["dt_start"] == bd
    ok += 1

    # 7. Самый конец накшатры: баланс ≈ 0, первая маха-даша почти нулевая
    r1 = calc_vimshottari(NK_SIZE - 1e-9, bd, levels=2)     # конец Ашвини (Кету)
    assert r1["nakshatra"]["name"] == "Ashwini"
    assert r1["balance"]["duration_years"] < 1e-8, r1["balance"]
    assert r1["periods"][0]["lord"] == "Кету"
    assert r1["periods"][1]["lord"] == "Венера"
    ok += 1

    # 8. Самое начало накшатры: баланс = полный срок
    r2 = calc_vimshottari(1e-9, bd, levels=2)               # начало Ашвини
    assert abs(r2["balance"]["duration_years"] - 7) < 1e-6, r2["balance"]
    ok += 1

    # 9. 0° и 360° дают одно и то же; отрицательные и >360 нормализуются
    a = calc_vimshottari(0.0, bd, levels=1)
    b = calc_vimshottari(360.0, bd, levels=1)
    c = calc_vimshottari(-62.1023, bd, levels=1)
    d = calc_vimshottari(360.0 - 62.1023, bd, levels=1)
    assert a["periods"][0]["dt_end"] == b["periods"][0]["dt_end"]
    assert c["periods"][0]["dt_end"] == d["periods"][0]["dt_end"]
    ok += 1

    # 10. levels=1 не даёт подпериодов, levels=3 даёт 9×9 на маха-дашу
    assert all(p["sub"] == [] for p in calc_vimshottari(297.8977, bd, levels=1)["periods"])
    r3 = calc_vimshottari(297.8977, bd, levels=3)
    full = [p for p in r3["periods"] if not p["truncated_start"]][0]
    assert len(full["sub"]) == 9 and all(len(s["sub"]) == 9 for s in full["sub"])
    ok += 1

    # 11. is_current — ровно один период на каждом уровне
    mid = r["periods"][3]
    probe = mid["dt_start"] + (mid["dt_end"] - mid["dt_start"]) / 2
    r4 = calc_vimshottari(297.8977, datetime(1990, 5, 17, 14, 30), levels=2, as_of=probe)
    assert sum(1 for p in r4["periods"] if p["is_current"]) == 1
    cur = [p for p in r4["periods"] if p["is_current"]][0]
    assert cur["lord"] == mid["lord"]
    assert sum(1 for s in cur["sub"] if s["is_current"]) == 1
    ok += 1

    # 12. until продлевает цикл дальше девяти маха-даш
    r5 = calc_vimshottari(297.8977, datetime(1990, 5, 17, 14, 30), levels=1,
                          until=datetime(2150, 1, 1))
    assert len(r5["periods"]) > 9
    assert r5["periods"][-1]["dt_end"] >= datetime(2150, 1, 1)
    ok += 1

    # 13. Валидация входа
    for bad in (lambda: calc_vimshottari("abc", bd),
                lambda: calc_vimshottari(10.0, "1990-01-01"),
                lambda: calc_vimshottari(10.0, bd, levels=0),
                lambda: calc_vimshottari(10.0, bd, levels=9),
                lambda: calc_vimshottari(10.0, bd, until=bd)):
        try:
            bad()
        except ValueError:
            pass
        else:
            raise AssertionError("ожидалась ValueError")
    ok += 1

    print(f"  Самопроверка: {ok}/13 групп инвариантов пройдено ✅")


# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        _selftest()
    elif len(sys.argv) >= 8 and sys.argv[1] == "--chart":
        y, mo, d, h, mi = map(int, sys.argv[2:7])
        moon = float(sys.argv[7])
        lv = int(sys.argv[8]) if len(sys.argv) > 8 else 2
        print_result(calc_vimshottari(moon, datetime(y, mo, d, h, mi), levels=lv))
    else:
        print("  python vimshottari.py --chart ГОД МЕС ДЕНЬ ЧАС МИН MOON_SID_LON [LEVELS]")
        print("  python vimshottari.py --selftest")
