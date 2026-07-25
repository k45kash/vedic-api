# Карта зависимостей

Что от чего зависит: от API и данных до экранов. Построено по фактическим импортам
в `calculators/*.ts` и карте экранов из [`SERVICE-IA.md`](SERVICE-IA.md).
Статусы — из [`COVERAGE.md`](COVERAGE.md).

Обозначения: 🟢 работает · 🟡 калькулятор готов, данные не подключены · 🔴 не задействовано

---

## 1. Четыре слоя

```mermaid
flowchart LR
    API["<b>API (FastAPI)</b><br/>эфемериды:<br/>где стояли планеты"]
    CALC["<b>calculators/</b><br/>трактовки традиции:<br/>что это значит"]
    DATA["<b>content/</b><br/>тексты и таблицы"]
    UI["<b>Экраны (Nuxt)</b><br/>6 вкладок ×<br/>2 аудитории"]

    API -->|"числа: накшатра,<br/>титхи, лагна"| CALC
    DATA -->|"правила и веса"| CALC
    CALC -->|"вердикты<br/>и разборы"| UI
    DATA -->|"статьи, справочники<br/>напрямую"| UI
```

Ключевое: **данные питают UI двумя путями** — через калькулятор (когда нужен расчёт)
и напрямую (когда нужен просто текст). Второй путь не требует ни API, ни расчётов —
поэтому «Справочник» можно строить хоть завтра, независимо от всего остального.

---

## 2. Внутренние зависимости калькуляторов

```mermaid
flowchart TD
    types["types.ts<br/><i>без зависимостей</i>"]
    nak["nakshatra.ts"]
    tara["<b>tara.ts</b><br/><i>узловой</i>"]
    kuta["kuta.ts"]
    picker["event-picker.ts"]
    sadh["sadhana.ts"]
    chart["chart.ts"]
    adapter["api-adapter.ts"]

    nak --> tara
    types --> tara
    tara --> kuta
    tara --> picker
    tara --> sadh
    nak --> picker
    nak --> sadh
    types --> picker
    types --> sadh
    types --> chart
    types --> adapter
    chart --> adapter
```

**Что это значит на практике:**

| Тронешь | Заденет |
|---|---|
| `nakshatra.ts` | tara → и следом kuta, event-picker, sadhana (**почти всё**) |
| `tara.ts` | kuta, event-picker, sadhana (3 калькулятора) |
| `types.ts` | все, но это только типы — правки безопасны |
| `chart.ts` | api-adapter |
| `kuta.ts`, `sadhana.ts`, `event-picker.ts` | никого — листья, менять безопасно |

Порядок разбора при отладке: сломалась тара → смотри `nakshatra.ts`;
сломался подбор даты → сначала `tara.ts`, потом веса.

**Самые критичные узлы** (от скольких других зависят, посчитано по графу):

| Узел | Зависят | Почему |
|---|---|---|
| `types.ts` | 11 | общие типы, но правки безопасны — только типы |
| `nakshatra_names`, `nak_rulers_seq`, `nak_ruler_short`, `gandanta_padas` | 11 | питают `nakshatra.ts` — фундамент всего |
| `nakshatra.ts` | 10 | ярлыки и управители нужны почти каждому калькулятору |
| `tara.ts` | 7 | три калькулятора + четыре экрана |

Правило: правки в `nakshatra.ts` и его четырёх JSON требуют проверки всех
калькуляторов; правки в `kuta.ts` / `sadhana.ts` / `event-picker.ts` — локальны.

> Мелочь для точности: `api-adapter.ts` импортирует из `chart.ts` только **тип**
> (`ChartPlanetInput`). На рантайм это не влияет, но при удалении `chart.ts`
> адаптер перестанет компилироваться.

---

## 3. Что нужно для каждого экрана

Важно: **калькуляторы не ходят в API**. Они чистые функции — данные из API в них
передаёт экран. Поэтому стрелки идут «API → экран», а не «API → калькулятор».

```mermaid
flowchart LR
    tz["/api/tz"] --> horo["/api/horoscope"]
    panch["/api/panchang"]
    cal["/api/calendar"]

    horo --> s1["Обо мне / Карта"]
    horo --> s2["Сегодня"]
    horo --> s3["Подобрать дату"]
    horo -.автозаполнение.-> s4["Совместимость"]
    horo --> s5["Практики"]
    panch --> s2
    panch --> s3
    panch --> s5
    cal --> s2
    cal --> s3
    cal --> s5
    s6["Справочник"]

    c1["chart.ts"] --> s1
    c2["tara.ts"] --> s2
    c3["event-picker.ts"] --> s3
    c4["kuta.ts"] --> s4
    c5["sadhana.ts"] --> s5
    c6["nakshatra.ts"] --> s6
```

### Сложность экранов (посчитано по графу)

| Экран | Узлов нужно | API | Комментарий |
|---|---|---|---|
| **Справочник** | 20 | **не нужен** | можно строить хоть сейчас, независимо ни от чего |
| **Совместимость** | 16 | horoscope (опц.) | самый простой с расчётом; работает и на ручном вводе |
| **Практики** | 20 | все 4 | садхана требует дат, мантры — нет |
| **Подобрать дату** | 21 | все 4 | |
| **Обо мне / Карта** | 23 | tz + horoscope | не нужны панчанга и календарь |
| **Сегодня** | 26 | все 4 | самый связанный экран |

### Детально по экранам

| Экран | API | Калькуляторы | Данные | Статус |
|---|---|---|---|---|
| **Обо мне / Карта** | `/tz` → `/horoscope` | chart, nakshatra | nakshatras, placements, houses, signs · 🔴 chart_geometry, padas, yogakarma, planet_in_nakshatra, retrograde | 🟡 |
| **Сегодня** | `/panchang`, `/calendar` | tara | tara_bala · 🔴 panchanga, tithi, muhurta30, tara_school, tara_dana | 🟡 |
| **Подобрать дату** | `/calendar`, `/panchang` | event-picker → tara, nakshatra | events_muhurta (7 из 33), tithi, picker_weights | 🟡 |
| **Совместимость** | `/horoscope` ×2 (опц.) | kuta → tara | nakshatras | 🟢 |
| **Практики** | `/calendar`, `/panchang` (садхана) | sadhana → tara, nakshatra | sadhana, mantra_upaya, planet_stories | 🟢 |
| **Справочник** | **не нужен** | nakshatra (ярлыки) | nakshatras, glossary, padas, signs, houses · 🔴 filter_defs, planet_in_nakshatra, sources | 🟢 |

Сквозные для всех экранов: `disclaimers`, `ui_texts`, `design_tokens`, `ui_colors` (🔴 не подключены).

---

## 4. Цепочка разблокировки

Почему форма рождения — первая задача: от неё зависит почти всё персональное.

```mermaid
flowchart TD
    form["<b>Форма рождения</b><br/>дата · время · место"]
    tzc["/api/tz<br/>часовой пояс"]
    h["/api/horoscope"]
    janma["Джанма-накшатра<br/>+ лагна + планеты"]

    form --> tzc --> h --> janma
    janma --> me["Обо мне / Карта"]
    janma --> tarad["Тара-бала дня<br/>→ Сегодня"]
    janma --> pick["Личный фактор<br/>→ Подбор даты"]
    janma --> kutas["Автозаполнение<br/>→ Совместимость"]
    janma --> sadh["Тара получателя<br/>→ Садхана"]
```

Пока формы нет, все эти экраны работают на демо-данных или требуют ручного ввода
накшатры. Один шаг закрывает пять зависимостей.

**Что НЕ зависит от формы** (можно делать параллельно):
Справочник целиком, общая панчанга дня (без личной тары), совместимость по
ручному вводу двух накшатр, мантры и истории планет.

---

## 5. Зависимости данных от источника

Весь `content/` восстановим из исходного HTML-архива:

```mermaid
flowchart LR
    html["nakshatry_polnyy.html<br/><i>архив коллеги</i>"]
    script["content/extract_data.py"]
    json["content/*.json<br/>34 файла"]
    html --> script --> json
```

Если архив обновится — данные пересобираются скриптом, ручных правок в JSON быть
не должно (иначе они потеряются при пересборке).

Исключение: `disclaimers.json` и `ui_texts.json` дособирались отдельно —
при пересборке их надо переносить руками.
