<script setup lang="ts">
useHead({ title: 'Регистрация — Vedic' })

const auth = useAuth()

const email = ref('')
const password = ref('')
const password2 = ref('')
const error = ref('')
const loading = ref(false)

if (auth.isAuthenticated.value) {
  await navigateTo('/dashboard', { replace: true })
}

// Совпадение паролей проверяем на лету, кнопку блокируем.
const mismatch = computed(() => !!password2.value && password.value !== password2.value)
const canSubmit = computed(
  () => !!email.value && password.value.length >= 8 && !mismatch.value && !loading.value,
)

async function submit() {
  if (password.value !== password2.value) {
    error.value = 'Пароли не совпадают.'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.register(email.value, password.value)
    // Регистрация прошла — сразу входим тем же логином/паролем.
    await auth.login(email.value, password.value)
    await navigateTo('/dashboard')
  } catch (e) {
    error.value = humanizeAuthError(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1>Регистрация</h1>
    <p class="subtitle">Создайте аккаунт по email. Пароль — не короче 8 символов.</p>

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
        {{ loading ? 'Создаём аккаунт…' : 'Зарегистрироваться' }}
      </button>

      <div class="auth-links">
        <NuxtLink to="/login">Уже есть аккаунт? Войти</NuxtLink>
      </div>
    </form>

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
