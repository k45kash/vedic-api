<script setup lang="ts">
// Типы авто-импортом не тянем — импортируем явно, так надёжнее.
import type { TelegramAuthPayload } from '~/composables/useAuth'

useHead({ title: 'Вход — Vedic' })

const auth = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

// Куда вернуть после входа: ?redirect от middleware/auth, иначе дашборд.
const redirectTo = computed(() => {
  const r = route.query.redirect
  return typeof r === 'string' && r.startsWith('/') ? r : '/dashboard'
})

// Уже вошли — сразу уводим.
if (auth.isAuthenticated.value) {
  await navigateTo(redirectTo.value, { replace: true })
}

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await navigateTo(redirectTo.value)
  } catch (e) {
    error.value = humanizeAuthError(e)
  } finally {
    loading.value = false
  }
}

/* ---------- Соц-провайдеры ---------- */

const PROVIDER_RU: Record<string, string> = {
  yandex: 'Яндекс',
  vk: 'VK',
  google: 'Google',
}

const providers = ref<string[]>([])
const telegramBot = ref<string | null>(null)
const providersLoading = ref(true)
const oauthPending = ref('')

async function goOAuth(provider: string) {
  oauthPending.value = provider
  error.value = ''
  try {
    // Внутри произойдёт window.location.href = authorization_url.
    await auth.startOAuth(provider)
  } catch (e) {
    error.value = humanizeAuthError(e)
    oauthPending.value = ''
  }
}

/* ---------- Telegram Login Widget ----------
   Имя бота фронтенду неоткуда взять — оно живёт в настройках бэкенда
   (auth/config.py → telegram_bot_username). Поэтому виджет показываем ТОЛЬКО
   если GET /auth/providers вернул поле telegram_bot с именем бота.
   Нет поля (или бот не настроен) → блок просто не рендерится, страница цела.
   TODO: когда бэкенд начнёт отдавать telegram_bot в /auth/providers,
   ничего менять не нужно — виджет появится сам.                              */

const telegramBox = ref<HTMLDivElement | null>(null)

function mountTelegramWidget() {
  if (!import.meta.client || !telegramBot.value || !telegramBox.value) return

  // Виджет дёргает глобальную функцию по имени из data-onauth.
  ;(window as any).onVedicTelegramAuth = async (payload: TelegramAuthPayload) => {
    error.value = ''
    loading.value = true
    try {
      await auth.loginWithTelegram(payload)
      await navigateTo(redirectTo.value)
    } catch (e) {
      error.value = humanizeAuthError(e)
    } finally {
      loading.value = false
    }
  }

  const s = document.createElement('script')
  s.src = 'https://telegram.org/js/telegram-widget.js?22'
  s.async = true
  s.setAttribute('data-telegram-login', telegramBot.value)
  s.setAttribute('data-size', 'medium')
  s.setAttribute('data-userpic', 'false')
  s.setAttribute('data-radius', '20')
  s.setAttribute('data-request-access', 'write')
  s.setAttribute('data-onauth', 'onVedicTelegramAuth(user)')
  telegramBox.value.appendChild(s)
}

onMounted(async () => {
  const info = await auth.fetchProviders()
  providers.value = info.providers.filter((p) => p !== 'telegram')
  telegramBot.value = info.telegram_bot || null
  providersLoading.value = false
  await nextTick()
  mountTelegramWidget()
})

const hasSocial = computed(() => providers.value.length > 0 || !!telegramBot.value)
</script>

<template>
  <div>
    <h1>Вход</h1>
    <p class="subtitle">Войдите по email и паролю или через соц-сеть.</p>

    <form class="birth" @submit.prevent="submit">
      <div class="row">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" required autocomplete="username" />
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label>Пароль</label>
          <input v-model="password" type="password" required autocomplete="current-password" />
        </div>
      </div>

      <button type="submit" class="primary" :disabled="loading">
        {{ loading ? 'Входим…' : 'Войти' }}
      </button>

      <div class="auth-links">
        <NuxtLink to="/forgot-password">Забыли пароль?</NuxtLink>
        <NuxtLink to="/register">Создать аккаунт</NuxtLink>
      </div>

      <!-- Соц-провайдеры: показываем, только если бэкенд что-то включил -->
      <template v-if="!providersLoading && hasSocial">
        <div class="auth-sep"><span>Или войдите через</span></div>

        <div v-if="providers.length" class="auth-providers">
          <button
            v-for="p in providers"
            :key="p"
            type="button"
            class="social"
            :class="`social-${p}`"
            :disabled="!!oauthPending"
            @click="goOAuth(p)"
          >
            {{ oauthPending === p ? 'Переходим…' : (PROVIDER_RU[p] || p) }}
          </button>
        </div>

        <!-- Контейнер под виджет Telegram; пуст, если бот не настроен -->
        <div v-show="telegramBot" ref="telegramBox" class="auth-telegram" />
      </template>
    </form>

    <p v-if="error" class="error auth-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.auth-links { display: flex; gap: 18px; font-size: 13px; }
.auth-links a { color: #0071e3; text-decoration: none; }
.auth-links a:hover { text-decoration: underline; }

.auth-sep {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #6e6e73;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 4px;
}
.auth-sep::before, .auth-sep::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(0, 0, 0, 0.08);
}

.auth-providers { display: flex; gap: 10px; flex-wrap: wrap; }
.social {
  padding: 10px 22px;
  border: none;
  border-radius: 980px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  color: #fff;
  cursor: pointer;
  transition: opacity 0.15s;
}
.social:hover { opacity: 0.88; }
.social:disabled { opacity: 0.5; cursor: not-allowed; }
.social-yandex { background: #fc3f1d; }
.social-vk     { background: #0077ff; }
.social-google { background: #1d1d1f; }

.auth-telegram { min-height: 34px; }
.auth-error { margin-top: 20px; }
</style>
