<script setup lang="ts">
// Временная страница-заглушка после логина: показывает прототип UI
// (prototype/index.html → скопирован в public/prototype.html) внутри iframe.
// Уйдёт, когда Фаза 2 (PLAN.md) реально подключит content/+calculators/ к Nuxt.
// Доступ только для авторизованных — проверка вынесена в middleware/auth.ts.
definePageMeta({ layout: false, middleware: 'auth' })
useHead({ title: 'Прототип — Vedic' })

const auth = useAuth()
// Разворачиваем в отдельные refs — так шаблон авто-разворачивает .value.
const { email: userEmail, plan } = auth

// Профиль подтягиваем после монтирования: если токен протух, useAuth сам его
// вычистит на 401, и middleware отправит на /login при следующей навигации.
onMounted(() => {
  auth.fetchUser().catch(() => {
    if (!auth.isAuthenticated.value) navigateTo('/login')
  })
})

function logout() {
  auth.logout()
  navigateTo('/login')
}
</script>

<template>
  <div class="wrap">
    <div class="bar">
      <span>Временная страница — прототип UI, не подключён к API. См. PLAN.md, Фаза 2.</span>
      <span class="who">
        <span v-if="userEmail">{{ userEmail }} · тариф: {{ plan }}</span>
        <button class="logout-btn" @click="logout">Выйти</button>
      </span>
    </div>
    <iframe src="/prototype.html" class="frame" title="Прототип" />
  </div>
</template>

<style scoped>
.wrap { display: flex; flex-direction: column; height: 100vh; background: #000; }
.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 20px;
  background: #1d1d1f;
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
}
.who { display: flex; align-items: center; gap: 12px; flex-shrink: 0; color: #a1a1a6; }
.logout-btn {
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  background: #0071e3;
  color: #fff;
  border: none;
  border-radius: 980px;
  cursor: pointer;
  flex-shrink: 0;
}
.logout-btn:hover { background: #0077ed; }
.frame { flex: 1; border: 0; width: 100%; }
</style>
