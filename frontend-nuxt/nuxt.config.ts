// https://nuxt.com/docs/api/configuration/nuxt-config
import { fileURLToPath } from 'node:url'

// Корень репозитория: content/ и calculators/ лежат РЯДОМ с frontend-nuxt/,
// внутрь фронтенда они не копируются (см. docs/HANDOFF.md §2).
const repoRoot = fileURLToPath(new URL('..', import.meta.url))

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  ssr: false,

  // Алиасы на внешние папки расчётов и контента (docs/HANDOFF.md §2).
  // Работают и в dev, и в `nuxt generate`; глубокие пути тоже: '~calc/tara'.
  alias: {
    '~calc': fileURLToPath(new URL('../calculators', import.meta.url)),
    '~content': fileURLToPath(new URL('../content', import.meta.url)),
  },

  vite: {
    server: {
      fs: {
        // Vite в dev не отдаёт файлы выше корня проекта (frontend-nuxt/), а
        // content/ и calculators/ лежат ВЫШЕ — иначе был бы 403
        // "The request url is outside of Vite serving allow list".
        //
        // Проверено: сейчас это подстраховка, а не необходимость — Nuxt сам
        // кладёт в allow свой workspaceDir, который для этого репозитория
        // совпадает с корнем (определяется по .git). Vite конкатенирует
        // пользовательский allow с nuxt'овым, так что запись безопасна и
        // страхует от смены способа определения workspaceDir.
        allow: [repoRoot],
      },
    },
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
