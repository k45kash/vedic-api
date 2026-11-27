<script setup lang="ts">
// Старые ссылки открывают Панчангу в кабинете с теми же параметрами.
definePageMeta({
  redirect: to => ({ path: '/panchang-day-v2', query: to.query, hash: to.hash }),
})
</script>

<template>
  <div />
</template>
