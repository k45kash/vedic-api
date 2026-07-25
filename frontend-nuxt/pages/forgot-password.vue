<script setup lang="ts">
useHead({ title: 'Восстановление пароля — Vedic' })

const auth = useAuth()

const email = ref('')
const error = ref('')
const loading = ref(false)
const done = ref(false)

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await auth.forgotPassword(email.value)
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
    <h1>Восстановление пароля</h1>
    <p class="subtitle">
      Укажите email — бэкенд сгенерирует токен сброса.
    </p>

    <!-- Честное предупреждение: писем пока действительно нет -->
    <p class="warn">
      Внимание: отправка писем ещё не настроена (SMTP не подключён). Письмо со ссылкой
      <b>не придёт</b>. Токен сброса сейчас можно получить только из логов бэкенда и
      вручную открыть страницу
      <NuxtLink to="/reset-password">/reset-password?token=…</NuxtLink>.
    </p>

    <form v-if="!done" class="birth" @submit.prevent="submit">
      <div class="row">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" required autocomplete="username" />
        </div>
      </div>

      <button type="submit" class="primary" :disabled="loading">
        {{ loading ? 'Отправляем запрос…' : 'Запросить сброс' }}
      </button>

      <div class="auth-links">
        <NuxtLink to="/login">Вернуться ко входу</NuxtLink>
      </div>
    </form>

    <div v-else class="result">
      <div class="card">
        <p>
          Запрос принят. Бэкенд создал токен сброса для <b>{{ email }}</b>, но письмо
          не отправлено — SMTP не подключён. Возьмите токен из логов бэкенда и откройте
          <NuxtLink to="/reset-password">страницу установки нового пароля</NuxtLink>.
        </p>
      </div>
    </div>

    <p v-if="error" class="error auth-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.warn {
  margin-bottom: 24px;
  padding: 12px 16px;
  background: rgba(255, 184, 0, 0.1);
  border: 1px solid rgba(255, 184, 0, 0.3);
  border-radius: 10px;
  font-size: 13px;
  color: #715200;
  max-width: 640px;
}
.warn a { color: #715200; }
.auth-links { display: flex; gap: 18px; font-size: 13px; }
.auth-links a { color: #0071e3; text-decoration: none; }
.auth-links a:hover { text-decoration: underline; }
.auth-error { margin-top: 20px; }
</style>
