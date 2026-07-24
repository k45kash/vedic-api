# Vedic — сервис ведической астрологии

Веб-сервис расчётов по джьотиш: панчанг, накшатры, гороскоп (лагна и планеты),
календарь транзитов Луны, циклы Сатурна (Сади Сати).

Расчёты выполняются на **Swiss Ephemeris** (файлы DE431) с аянамшей **Лахири**.
Никаких приближённых формул и фолбэков — только эфемериды.

| Что | Стек | Адрес |
|-----|------|-------|
| Backend (API) | Python 3.11, FastAPI, pyswisseph | `vedic-api-production-626f.up.railway.app` |
| Frontend | Nuxt 3 (SPA, `ssr: false`), Vue 3 | `vedic-nuxt-front-production.up.railway.app` |
| База | MongoDB | сервис на Railway + Volume |

Подробности — в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Текущие задачи и ход работ — в [`docs/PLAN.md`](docs/PLAN.md).

---

## Структура репозитория

```
.
├── main.py                     # FastAPI-приложение: все HTTP-эндпоинты
│
├── Panchangam.py               # расчёт панчанга: титхи, мухурты, хоры
├── nakshatra_calculator.py     # гороскоп: накшатра, лагна, положение планет
├── nakshatra_calendar.py       # календарь транзитов Луны по накшатрам
├── sade_sati.py                # Сади Сати + Аштама/Кантака Шани
├── utils.py                    # общее: таблица накшатр, dms_sign, dt_to_jd
│
├── auth/                       # авторизация (fastapi-users + MongoDB)
│   ├── config.py               #   настройки из окружения / .env
│   ├── db.py                   #   подключение Mongo + init Beanie
│   ├── models.py               #   модель User (plan/role) и схемы
│   ├── users.py                #   UserManager, JWT, зависимости доступа
│   └── router.py               #   сборка auth-роутов
│
├── frontend-nuxt/              # фронтенд (Nuxt 3) — канонический UI
│   ├── pages/                  #   index (накшатра), panchang, calendar, sade-sati
│   ├── components/             #   BirthForm, CityField, LagnaChart
│   ├── composables/            #   useApi, useBirthForm, useFormatters
│   ├── layouts/default.vue     #   навигация и общие стили
│   └── nuxt.config.ts          #   apiUrl, ssr:false, флаги сборки
│
├── calculators/                # трактовки традиции (TS, без фреймворка) — не подключены
│   └── (tara/kuta/event-picker/sadhana/chart/nakshatra + api-adapter)
├── content/                    # контентная база джйотиша (34 JSON, 1,4 МБ) — не подключена
├── prototype/index.html        # кликабельный референс UI (демо-данные, не прод-код)
│
├── ephe/                       # эфемериды Swiss Ephemeris (данные расчётов)
│
├── docs/                       # архитектура, план работ, IA/дизайн контентного слоя
├── requirements.txt            # зависимости Python
├── .env.example                # шаблон секретов (реальный .env не коммитится)
├── Procfile / nixpacks.toml    # деплой бэкенда на Railway
└── runtime.txt                 # python-3.11
```

`calculators/` и `content/` — расчёты-трактовки и контент джйотиша поверх эфемерид
(тара-бала, совместимость, подбор даты события и т.д.). Готовы, но пока не
подключены к Nuxt — что уже сделано и что дальше см. [`docs/HANDOFF.md`](docs/HANDOFF.md),
[`docs/COVERAGE.md`](docs/COVERAGE.md) и фазу в [`docs/PLAN.md`](docs/PLAN.md).

---

## Запуск локально

### Backend

```bash
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

Документация API: <http://localhost:8000/docs>

Для работы авторизации нужен `.env` (скопируй из `.env.example` и заполни).
Без базы данных сервер стартует нормально — auth просто отключается,
публичные расчёты продолжают работать.

### Frontend

```bash
cd frontend-nuxt
npm install
npm run dev          # http://localhost:3000, с hot-reload
```

Сборка статики: `npm run build` → `.output/public`.

> Требуется Node ≥ 22.12 (нужен для Vite 7).

---

## API

Публичные (без авторизации):

| Метод | Путь | Назначение |
|-------|------|-----------|
| POST | `/api/panchang` | титхи, мухурты, хоры за период |
| POST | `/api/horoscope` | накшатра, лагна, планеты по дате рождения |
| POST | `/api/calendar` | транзиты Луны по накшатрам |
| POST | `/api/sade-sati` | циклы Сатурна: Сади Сати, Аштама, Кантака |
| GET | `/api/tz` | часовой пояс и offset по координатам и дате |
| GET | `/api/debug` | диагностика: версия, эфемериды, аянамша |

Авторизация: `/auth/*` (регистрация, JWT-логин, сброс пароля) и `/users/me`.
Подробно — в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
