// Route middleware: пускает дальше только авторизованных.
// Гостя уводим на /login, запомнив, куда он шёл (?redirect=…).
export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated.value) return
  return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
})
