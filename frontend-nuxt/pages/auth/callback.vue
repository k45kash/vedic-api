<script setup lang="ts">
// Приёмник OAuth-возврата. Бэкенд редиректит браузер сюда:
//   /auth/callback#token=<jwt>&provider=<name>
//   /auth/callback#error=<текст>
// Хэш используется вместо query, чтобы токен не попал в логи сервера.
useHead({ title: 'Завершаем вход — Vedic' })

const auth = useAuth()

const error = ref('')
const provider = ref('')
const busy = ref(true)

const PROVIDER_RU: Record<string, string> = {
  yandex: 'Яндекс',
  vk: 'VK',
  google: 'Google',
  telegram: 'Telegram',
}

onMounted(async () => {
  const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : ''
  const params = new URLSearchParams(hash)
  const token = params.get('token')
  const err = params.get('error')
  provider.value = params.get('provider') || ''

  // Сразу вычищаем хэш, чтобы токен не остался в адресной строке и в истории.
  history.replaceState(null, '', window.location.pathname + window.location.search)

  if (err) {
    // URLSearchParams уже раскодировал значение — повторный decodeURIComponent
    // сломался бы на тексте с литеральным «%».
    error.value = err
    busy.value = false
    return
  }
  if (!token) {
    error.value = 'Провайдер не передал токен. Попробуйте войти ещё раз.'
    busy.value = false
    return
  }

  try {
    await auth.loginWithToken(token)
    await navigateTo('/dashboard', { replace: true })
  } catch (e) {
    error.value = humanizeAuthError(e)
    busy.value = false
  }
})
</script>

<template>
  <div>
    <h1>Вход через {{ PROVIDER_RU[provider] || 'соц-сеть' }}</h1>

    <p v-if="busy" class="loading">Завершаем вход…</p>

    <template v-else-if="error">
      <p class="error">{{ error }}</p>
      <p class="back">
        <NuxtLink to="/login">Вернуться на страницу входа</NuxtLink>
      </p>
    </template>
  </div>
</template>

<style scoped>
.back { margin-top: 20px; font-size: 14px; }
.back a { color: #0071e3; text-decoration: none; }
.back a:hover { text-decoration: underline; }
</style>
