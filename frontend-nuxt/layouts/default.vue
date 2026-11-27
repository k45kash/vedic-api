<script setup lang="ts">
const route = useRoute()
const auth = useAuth()
const { isAuthenticated, email: userEmail } = auth

useHead({ bodyAttrs: { class: 'vd-public' } })

// Профиль подтягиваем один раз при монтировании, если токен есть:
// нужен email в шапке; на 401 useAuth сам вычистит протухший токен.
onMounted(() => {
  if (isAuthenticated.value && !auth.user.value) auth.fetchUser().catch(() => null)
})

async function onLogout() {
  auth.logout()
  await navigateTo('/login')
}
</script>

<template>
  <div class="public-shell">
    <nav aria-label="Основная навигация">
      <ul class="public-navigation">
        <li><NuxtLink to="/" class="public-brand">Vedic</NuxtLink></li>

        <!-- Гость: ссылка на вход. Залогинен: профиль + выход. -->
        <template v-if="!isAuthenticated">
          <li class="nav-right">
            <NuxtLink to="/login" :class="{ active: route.path === '/login' }">Вход</NuxtLink>
          </li>
        </template>
        <template v-else>
          <li class="nav-right">
            <NuxtLink to="/me">
              {{ userEmail || 'Профиль' }}
            </NuxtLink>
          </li>
          <li>
            <button type="button" class="nav-logout" @click="onLogout">Выйти</button>
          </li>
        </template>
      </ul>
    </nav>
    <main>
      <slot />
    </main>
  </div>
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body.vd-public {
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  background: #f5f5f7;
  color: #1d1d1f;
  min-height: 100vh;
}

.public-shell nav {
  background: rgba(255,255,255,0.85);
  backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}
.public-shell nav ul {
  display: flex;
  gap: 0;
  list-style: none;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
.public-shell nav a {
  display: block;
  padding: 16px 20px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  text-decoration: none;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.public-navigation > li { flex-shrink: 0; }
.public-navigation a { white-space: nowrap; }
@media (max-width: 720px) {
  .public-navigation { overflow-x: auto; padding: 0 8px; }
  .public-navigation a, .public-navigation .nav-logout { padding: 14px 10px; }
}
.public-navigation .public-brand { font-weight: 700; opacity: 1; }
.public-shell nav a:hover { opacity: 1; }
.public-shell nav a.active { opacity: 1; color: #0071e3; }
/* Блок авторизации прижимаем к правому краю */
.public-shell nav li.nav-right { margin-left: auto; }
.public-shell nav .nav-logout {
  display: block;
  padding: 16px 20px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  color: #1d1d1f;
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.public-shell nav .nav-logout:hover { opacity: 1; }

.public-shell main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px;
}

.public-shell h1 { font-size: 32px; font-weight: 700; letter-spacing: -0.5px; }
.public-shell .subtitle { margin-top: 6px; font-size: 15px; color: #6e6e73; margin-bottom: 36px; max-width: 640px; }

.public-shell form.birth {
  background: #fff;
  border-radius: 18px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.public-shell .row { display: flex; gap: 16px; flex-wrap: wrap; }
.public-shell .field { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 140px; }
.public-shell .field label { font-size: 13px; font-weight: 500; color: #6e6e73; }
.public-shell .field input {
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
.public-shell .field input:focus { box-shadow: 0 0 0 3px rgba(0,113,227,0.25); }

.public-shell button.primary {
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
.public-shell button.primary:hover { background: #0077ed; }
.public-shell button.primary:disabled { opacity: 0.5; cursor: not-allowed; }

.public-shell #result, .public-shell .result { margin-top: 32px; display: flex; flex-direction: column; gap: 24px; }
.public-shell .result h2 {
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}
.public-shell .result .card {
  background: #fff;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.public-shell .error { padding: 14px 18px; background: #ffe3e3; color: #c92a2a; border-radius: 10px; }
.public-shell .loading { padding: 14px 0; color: #6e6e73; }
</style>
