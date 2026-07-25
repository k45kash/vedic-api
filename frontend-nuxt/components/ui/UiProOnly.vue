<script setup lang="ts">
/**
 * Обёртка для блоков, которые видны только в режиме «Астролог» (.pro).
 * Видимостью управляет CSS: `.vd-app.is-pro .pro { display:block }` —
 * так же, как в прототипе, без лишних перерисовок при переключении режима.
 */
</script>

<template>
  <div class="pro">
    <slot />
  </div>
</template>
