<script setup lang="ts">
// Старый /dashboard больше не показывает прототип в iframe: кабинет теперь
// собран на Nuxt-компонентах. Маршрут остаётся только как редирект — на него
// ведут старые ссылки и переход после входа.
// Файл public/prototype.html сохранён как справочный материал.
definePageMeta({
  layout: false,
  // Сначала обычная проверка входа, затем перенос на «Обо мне».
  middleware: ['auth', () => navigateTo('/me', { replace: true })],
})
</script>

<template>
  <div />
</template>
