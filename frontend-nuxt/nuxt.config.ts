// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  ssr: false,
  app: {
    head: {
      title: 'Vedic',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
  runtimeConfig: {
    public: {
      apiUrl: 'https://vedic-api-production-626f.up.railway.app',
    },
  },
  devtools: { enabled: false },
})
