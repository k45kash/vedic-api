<script setup lang="ts">
useHead({ title: 'Вход — Vedic' })

const auth = useAuth()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

if (auth.isAuthenticated.value) {
  await navigateTo('/dashboard')
}

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await navigateTo('/dashboard')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1>Вход</h1>
    <p class="subtitle">Временный вход для внутренних тестов — email и пароль.</p>

    <form class="birth" @submit.prevent="submit">
      <div class="row">
        <div class="field">
          <label>Email</label>
          <input type="email" v-model="email" required autocomplete="username" />
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label>Пароль</label>
          <input type="password" v-model="password" required autocomplete="current-password" />
        </div>
      </div>
      <button type="submit" class="primary" :disabled="loading">
        {{ loading ? 'Входим…' : 'Войти' }}
      </button>
    </form>

    <p v-if="error" class="error">Ошибка: {{ error }}</p>
  </div>
</template>
