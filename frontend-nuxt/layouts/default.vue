<script setup lang="ts">
const route = useRoute()
const nav = [
  { href: '/',          label: 'Накшатра'  },
  { href: '/panchang',  label: 'Панчанг'   },
  { href: '/calendar',  label: 'Календарь' },
  { href: '/sade-sati', label: 'Сади Сати' },
]
</script>

<template>
  <div>
    <nav>
      <ul>
        <li v-for="item in nav" :key="item.href">
          <NuxtLink :to="item.href" :class="{ active: route.path === item.href }">
            {{ item.label }}
          </NuxtLink>
        </li>
      </ul>
    </nav>
    <main>
      <slot />
    </main>
  </div>
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
  min-height: 100vh;
}

nav {
  background: rgba(255,255,255,0.85);
  backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}
nav ul {
  display: flex;
  gap: 0;
  list-style: none;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
nav a {
  display: block;
  padding: 16px 20px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  text-decoration: none;
  opacity: 0.6;
  transition: opacity 0.15s;
}
nav a:hover { opacity: 1; }
nav a.active { opacity: 1; color: #0071e3; }

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px;
}

h1 { font-size: 32px; font-weight: 700; letter-spacing: -0.5px; }
.subtitle { margin-top: 6px; font-size: 15px; color: #6e6e73; margin-bottom: 36px; max-width: 640px; }

form.birth {
  background: #fff;
  border-radius: 18px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.row { display: flex; gap: 16px; flex-wrap: wrap; }
.field { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 140px; }
.field label { font-size: 13px; font-weight: 500; color: #6e6e73; }
.field input {
  padding: 10px 14px;
  border-radius: 10px;
  border: none;
  background: #f5f5f7;
  font-size: 15px;
  font-family: inherit;
  color: #1d1d1f;
  outline: none;
  transition: box-shadow 0.15s;
}
.field input:focus { box-shadow: 0 0 0 3px rgba(0,113,227,0.25); }

button.primary {
  align-self: flex-start;
  padding: 12px 28px;
  background: #0071e3;
  color: #fff;
  border: none;
  border-radius: 980px;
  font-size: 15px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}
button.primary:hover { background: #0077ed; }
button.primary:disabled { opacity: 0.5; cursor: not-allowed; }

#result, .result { margin-top: 32px; display: flex; flex-direction: column; gap: 24px; }
.result h2 {
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}
.result .card {
  background: #fff;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.error { padding: 14px 18px; background: #ffe3e3; color: #c92a2a; border-radius: 10px; }
.loading { padding: 14px 0; color: #6e6e73; }
</style>
