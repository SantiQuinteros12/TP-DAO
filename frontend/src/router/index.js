import { createRouter, createWebHistory } from 'vue-router'

// Carga diferida: cada vista se descarga al navegar a ella.
const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { titulo: 'Reportes' } },
  { path: '/sedes', name: 'sedes', component: () => import('../views/SedesView.vue'), meta: { titulo: 'Sedes' } },
  { path: '/socios', name: 'socios', component: () => import('../views/SociosView.vue'), meta: { titulo: 'Socios' } },
  { path: '/catalogo', name: 'catalogo', component: () => import('../views/CatalogoView.vue'), meta: { titulo: 'Catálogo' } },
  { path: '/prestamos', name: 'prestamos', component: () => import('../views/PrestamosView.vue'), meta: { titulo: 'Préstamos' } },
  { path: '/reservas', name: 'reservas', component: () => import('../views/ReservasView.vue'), meta: { titulo: 'Reservas' } },
  { path: '/recomendaciones', name: 'recomendaciones', component: () => import('../views/RecomendacionesView.vue'), meta: { titulo: 'Recomendaciones' } },
  { path: '/remitos/:id?', name: 'remitos', component: () => import('../views/RemitosView.vue'), meta: { titulo: 'Remitos' } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.afterEach((to) => {
  document.title = `${to.meta.titulo} · Red de Bibliotecas`
})

export default router
