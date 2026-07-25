// https://nuxt.com/docs/api/configuration/nuxt-config
import { fileURLToPath } from 'node:url'

// content/ и calculators/ лежат ВНУТРИ frontend-nuxt/. Это вынужденно:
// у Railway-сервиса фронта Root Directory = frontend-nuxt/, и в сборку
// попадает только эта папка — соседние каталоги репозитория недоступны
// (сборка падала с "Could not load /calculators/nakshatra"). См. PLAN.md.

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  ssr: false,

  // Алиасы на расчёты и контент. Глубокие пути тоже работают: '~calc/tara'.
  // Папки внутри проекта, поэтому vite.server.fs.allow больше не нужен.
  alias: {
    '~calc': fileURLToPath(new URL('./calculators', import.meta.url)),
    '~content': fileURLToPath(new URL('./content', import.meta.url)),
  },
  app: {
    head: {
      title: 'Vedic',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
  // Дизайн-токены кабинета. Правила заскоуплены под .vd-app / body.vd-scope,
  // поэтому глобальные стили старой раскладки (layouts/default.vue) не меняются.
  css: ['~/assets/css/tokens.css'],
  runtimeConfig: {
    public: {
      apiUrl: 'https://vedic-api-production-626f.up.railway.app',
    },
  },
  nitro: {
    prerender: {
      // Раздаём статику без SPA-фолбэка (serve без -s), поэтому каждый маршрут
      // должен получить свой index.html. Краулер не найдёт /auth/callback —
      // на него никто не ссылается, он открывается редиректом от бэкенда.
      routes: [
        '/login',
        '/register',
        '/forgot-password',
        '/reset-password',
        '/auth/callback',
        '/dashboard',
        '/me',
        '/today',
        '/pick-date',
      ],
    },
  },
  // Vite 7 не создаёт отдельный SSR-сервер, из-за чего vite-node IPC-сокет
  // в dev не инициализируется ("Vite Node IPC socket path not configured").
  // Environment API запускает resolveServer сразу и выставляет socketPath.
  experimental: {
    viteEnvironmentApi: true,
  },
  devtools: { enabled: false },
})
