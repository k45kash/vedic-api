<script setup lang="ts">
definePageMeta({
  layout: false,
  middleware: [() => navigateTo('/me', { replace: true })],
})
</script>

<template>
  <div />
</template>
