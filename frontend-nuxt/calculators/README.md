# calculators/ — расчётные модули (TypeScript, framework-agnostic)

Логика калькуляторов из `nakshatry_polnyy (14).html`, перенесённая 1:1 в чистые
TS-функции: без DOM, без Vue — готово к использованию в Nuxt (frontend-nuxt в
PycharmProjects/Vedic) и где угодно ещё. Подробное описание алгоритмов —
[docs/CALCULATORS.md](../docs/CALCULATORS.md).

## Модули

| Модуль | Экспорты | Что считает |
|---|---|---|
| `tara.ts` | `taraFor`, `taraChakra`, `taraFavorable` | Тара-бала дня, Наватара-чакра |
| `kuta.ts` | `ashtaKutaPartial` (+ отдельные куты) | совместимость: Гана, Йони, Тара, Нади (21 из 36 баллов) |
| `event-picker.ts` | `scoreEvent`, `listEvents` | балльная оценка дня под событие (33 события) |
| `sadhana.ts` | `sadhanaScore`, `listMetals` | день изготовления изделия (металлы планет) |
| `chart.ts` | `analyzeChart`, `houseForSign`, `signForHouse`, `dignity` | Whole Sign раскладка + трактовки |
| `nakshatra.ts` | `nakshatraFromLongitude`, `nakLabel`, `isGandantaNakshatra` | накшатра/пада по долготе, ярлыки |
| `api-adapter.ts` | `janmaFromHoroscope`, `chartFromHoroscope`, `splitTithi`, `weekdayRu` | мосты к Vedic Astrology API |
| `types.ts` | `WEEKDAYS_RU`, `PLANETS_RU`, `PLANET_SLUG`… | общие типы и константы |

## Конвенции

- Накшатры **1..27**, знаки **1..12** (Овен = 1), дома **1..12**, титхи **1..15 + пакша**
  (`'shukla' | 'krishna'`). В исходном HTML накшатры были 0-индексными.
- Все функции чистые, возвращают структуры с русскими текстами для UI
  (вердикты, построчные разборы) — рендер решает сам, как это показать.
- Данные импортируются из `../content/*.json` — модули переносятся **вместе с папкой
  `content/`**, относительный путь должен сохраниться.

## Подключение в Nuxt

`calculators/` и `content/` лежат **внутри** `frontend-nuxt/` и подключены
алиасами (`nuxt.config.ts`):

```ts
alias: {
  '~calc':    fileURLToPath(new URL('./calculators', import.meta.url)),
  '~content': fileURLToPath(new URL('./content', import.meta.url)),
}
```

Внутрь фронтенда их пришлось перенести из корня репозитория: у Railway-сервиса
фронта Root Directory = `frontend-nuxt/`, соседние каталоги в сборку не
попадают. Подробности — в `docs/PLAN.md`.

JSON-импорты Nuxt/Vite понимает из коробки (`resolveJsonModule` уже включён
в tsconfig Nuxt). Использование:

```ts
import { taraFor, scoreEvent, splitTithi, weekdayRu } from '~calc'

// Тара-бала на сегодня: janma из /api/horoscope, накшатра дня из /api/calendar
const tara = taraFor(horo.nk.num, todayNakNo)

// Оценка даты под свадьбу — данные дня из /api/panchang + /api/calendar
const { tithi, paksha } = splitTithi(panchangTithi.num)
const score = scoreEvent({
  eventId: 'wedding',
  janmaNo: horo.nk.num,
  dayNakNo: todayNakNo,
  weekday: weekdayRu(date),
  tithi, paksha,
})
```

## Проверено

- Строгий `tsc --noEmit --strict` — без ошибок.
- Тесты паритета с оригинальным JS: тара-бала — полный перебор 27×27 пар;
  куты, вето-логика событий, стоп-факторы садханы, обратимость маппинга
  дом↔знак (12×12), достоинства планет, адаптер титхи.
