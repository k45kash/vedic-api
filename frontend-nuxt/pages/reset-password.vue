<script setup lang="ts">
useHead({ title: 'Новый пароль — Vedic' })

const auth = useAuth()
const route = useRoute()

// Токен приходит в query (?token=…). Пока писем нет — его можно вставить руками.
const token = ref(typeof route.query.token === 'string' ? route.query.token : '')
const password = ref('')
const password2 = ref('')
const error = ref('')
const loading = ref(false)
const done = ref(false)

const mismatch = computed(() => !!password2.value && password.value !== password2.value)
const canSubmit = computed(
  () => !!token.value && password.value.length >= 8 && !mismatch.value && !loading.value,
)

async function submit() {
  if (password.value !== password2.value) {
    error.value = 'Пароли не совпадают.'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.resetPassword(token.value, password.value)
    done.value = true
  } catch (e) {
    error.value = humanizeAuthError(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1>Новый пароль</h1>
    <p class="subtitle">
      Вставьте токен сброса и придумайте новый пароль (не короче 8 символов).
    </p>

    <form v-if="!done" class="birth" @submit.prevent="submit">
      <div class="row">
        <div class="field">
          <label>Токен сброса</label>
          <input v-model="token" type="text" required autocomplete="off" />
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label>Новый пароль</label>
          <input
            v-model="password"
            type="password"
            required
            minlength="8"
            autocomplete="new-password"
          />
        </div>
        <div class="field">
          <label>Повторите пароль</label>
          <input v-model="password2" type="password" required autocomplete="new-password" />
        </div>
      </div>

      <p v-if="mismatch" class="hint-bad">Пароли не совпадают.</p>

      <button type="submit" class="primary" :disabled="!canSubmit">
        {{ loading ? 'Сохраняем…' : 'Установить пароль' }}
      </button>

      <div class="auth-links">
        <NuxtLink to="/login">Вернуться ко входу</NuxtLink>
      </div>
    </form>

    <div v-else class="result">
      <div class="card">
        <p>Пароль изменён. Теперь можно <NuxtLink to="/login">войти</NuxtLink>.</p>
      </div>
    </div>

    <p v-if="error" class="error auth-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.auth-links { display: flex; gap: 18px; font-size: 13px; }
.auth-links a { color: #0071e3; text-decoration: none; }
.auth-links a:hover { text-decoration: underline; }
.hint-bad { font-size: 13px; color: #c92a2a; }
.auth-error { margin-top: 20px; }
</style>
