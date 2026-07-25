<script setup lang="ts">
// Оболочка личного кабинета: сайдбар + шапка + слот контента.
// Перенос из prototype/v2.html, визуальные детали шапки и логотипа —
// из макета prototype/concepte.png.
//
// Старая раскладка default.vue не тронута: все стили кабинета живут в
// assets/css/tokens.css и заскоуплены под корневой класс .vd-app,
// а фон страницы включает класс .vd-scope на <body> (см. useHead ниже).

const route = useRoute()
const { header } = usePageHeader()
const { isDark, toggleTheme } = useTheme()
const { isPro, setAudience } = useAudience()
const auth = useAuth()

// Пункты сайдбара. Первые три — рабочие маршруты, остальные пока задизейблены
// с меткой «скоро», как в прототипе.
const navItems = [
  { label: 'Обо мне', icon: 'user', to: '/me' },
  { label: 'Сегодня', icon: 'sun', to: '/today' },
  { label: 'Подобрать дату', icon: 'calendar', to: '/pick-date' },
  { label: 'Совместимость', icon: 'heart', soon: true },
  { label: 'Практики', icon: 'lotus', soon: true },
  { label: 'Справочник', icon: 'book', soon: true },
  { label: 'Настройки', icon: 'settings', soon: true },
] as const

// --- мобильное меню ---
const menuOpen = ref(false)
function toggleMenu(force?: boolean) {
  menuOpen.value = force === undefined ? !menuOpen.value : force
}

// Смена маршрута закрывает меню — в прототипе это делал setTab().
watch(() => route.fullPath, () => toggleMenu(false))

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') toggleMenu(false)
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

// Буква в аватаре — из email, если профиль уже загружен.
const avatarLetter = computed(() => (auth.email.value || 'В').trim().charAt(0).toUpperCase())

// Класс на <body>: включает фон и типографику кабинета и снимается сам,
// когда пользователь уходит на страницу со старой раскладкой.
useHead({ bodyAttrs: { class: 'vd-scope' } })
</script>

<template>
  <div class="vd-app" :class="{ 'is-pro': isPro, 'is-menu': menuOpen }">
    <!-- затемнение под открытым мобильным меню -->
    <div class="scrim" @click="toggleMenu(false)" />

    <div class="app">
      <!-- ==================== САЙДБАР ==================== -->
      <aside class="side">
        <NuxtLink to="/me" class="logo" aria-label="Jyotish — на главную">
          <!-- лотос из макета: один лепесток, повёрнутый вокруг основания -->
          <svg
            class="logo__mark"
            viewBox="0 0 40 40"
            fill="none"
            stroke="currentColor"
            stroke-width="1.25"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <g>
              <path d="M20 8c2.7 3.8 4 7.1 4 10 0 2.9-1.3 5.5-4 7.9-2.7-2.4-4-5-4-7.9 0-2.9 1.3-6.2 4-10z" />
              <path
                d="M20 8c2.7 3.8 4 7.1 4 10 0 2.9-1.3 5.5-4 7.9-2.7-2.4-4-5-4-7.9 0-2.9 1.3-6.2 4-10z"
                transform="rotate(38 20 26)"
              />
              <path
                d="M20 8c2.7 3.8 4 7.1 4 10 0 2.9-1.3 5.5-4 7.9-2.7-2.4-4-5-4-7.9 0-2.9 1.3-6.2 4-10z"
                transform="rotate(-38 20 26)"
              />
              <path
                d="M20 8c2.7 3.8 4 7.1 4 10 0 2.9-1.3 5.5-4 7.9-2.7-2.4-4-5-4-7.9 0-2.9 1.3-6.2 4-10z"
                transform="rotate(74 20 26)"
              />
              <path
                d="M20 8c2.7 3.8 4 7.1 4 10 0 2.9-1.3 5.5-4 7.9-2.7-2.4-4-5-4-7.9 0-2.9 1.3-6.2 4-10z"
                transform="rotate(-74 20 26)"
              />
            </g>
            <path d="M8 31h24" stroke-linecap="round" opacity=".45" />
          </svg>
          <div>
            <div class="logo__name">Jyotish</div>
            <div class="logo__sub">ведическая астрология</div>
          </div>
        </NuxtLink>

        <nav class="nav" aria-label="Разделы">
          <template v-for="item in navItems" :key="item.label">
            <NuxtLink
              v-if="item.to"
              class="nav__item"
              :class="{ 'is-on': route.path === item.to }"
              :to="item.to"
              :aria-current="route.path === item.to ? 'page' : undefined"
            >
              <UiIcon :name="item.icon" />
              {{ item.label }}
            </NuxtLink>
            <button v-else type="button" class="nav__item" disabled>
              <UiIcon :name="item.icon" />
              {{ item.label }}
              <span class="nav__soon">скоро</span>
            </button>
          </template>
        </nav>

        <!-- на узких экранах переключатель режима переезжает сюда из шапки -->
        <div class="seg seg--side" role="group" aria-label="Режим отображения">
          <button
            type="button"
            :class="{ 'is-on': !isPro }"
            :aria-pressed="!isPro"
            @click="setAudience('simple')"
          >
            Пользователь
          </button>
          <button
            type="button"
            :class="{ 'is-on': isPro }"
            :aria-pressed="isPro"
            @click="setAudience('pro')"
          >
            Астролог
          </button>
        </div>

        <div class="side__spacer" />

        <div class="promo">
          <div class="promo__head">
            <UiIcon name="crown" />
            Премиум доступ
          </div>
          <p class="promo__text">
            Расширенные отчёты, сохранённые карты и полный справочник накшатр.
          </p>
          <!-- TODO: маршрут тарифов появится вместе с биллингом -->
          <button type="button" class="btn">Узнать больше</button>
        </div>

        <div class="help">
          <UiIcon name="headset" />
          <div>
            <b>Нужна помощь?</b>
            <a href="mailto:support@jyotish.app">Напишите нам</a>
          </div>
        </div>
      </aside>

      <!-- ==================== КОНТЕНТ ==================== -->
      <div class="main">
        <header class="topbar" :class="{ 'topbar--wrap': !!header.dateNav }">
          <button
            type="button"
            class="iconbtn burger"
            aria-label="Меню"
            :aria-expanded="menuOpen"
            @click="toggleMenu()"
          >
            <UiIcon name="burger" :width="1.7" />
          </button>

          <NuxtLink v-if="header.back" class="iconbtn" :to="header.back" aria-label="Назад">
            <UiIcon name="arrow-left" />
          </NuxtLink>

          <div class="topbar__id">
            <h1 class="topbar__title">{{ header.title }}</h1>
            <div v-if="header.subtitle || header.subtitleLink" class="topbar__sub">
              {{ header.subtitle }}
              <NuxtLink v-if="header.subtitleLink?.to" :to="header.subtitleLink.to">
                {{ header.subtitleLink.text }}
              </NuxtLink>
            </div>
          </div>

          <div class="topbar__spacer" />

          <!-- навигатор даты по центру: страница задаёт его через usePageHeader -->
          <div v-if="header.dateNav" class="topbar__center">
            <UiDateNav
              :label="header.dateNav.label"
              @prev="header.dateNav.onPrev?.()"
              @next="header.dateNav.onNext?.()"
              @pick="header.dateNav.onPick?.()"
            />
          </div>

          <div class="topbar__spacer" />

          <div class="topbar__right">
            <UiPlace v-if="header.place" :city="header.place.city" :time="header.place.time" />

            <div class="seg seg--top" role="group" aria-label="Режим отображения">
              <button
                type="button"
                :class="{ 'is-on': !isPro }"
                :aria-pressed="!isPro"
                @click="setAudience('simple')"
              >
                Пользователь
              </button>
              <button
                type="button"
                :class="{ 'is-on': isPro }"
                :aria-pressed="isPro"
                @click="setAudience('pro')"
              >
                Астролог
              </button>
            </div>

            <button
              type="button"
              class="iconbtn"
              aria-label="Сменить тему"
              :aria-pressed="isDark"
              @click="toggleTheme()"
            >
              <UiIcon :name="isDark ? 'sun' : 'moon'" :width="1.5" />
            </button>

            <button type="button" class="iconbtn" aria-label="Уведомления">
              <UiIcon name="bell" />
              <span class="iconbtn__dot" aria-hidden="true" />
            </button>

            <button type="button" class="avatarbtn" aria-label="Профиль">
              <span class="avatar" aria-hidden="true">{{ avatarLetter }}</span>
              <UiIcon name="chevron-down" />
            </button>
          </div>
        </header>

        <div class="content">
          <slot />
        </div>
      </div>
    </div>
  </div>
</template>
