<script setup>
import { ref } from 'vue'
import ToastHost from './components/ToastHost.vue'

const menuAbierto = ref(false)

const secciones = [
  { to: '/', texto: 'Reportes', icono: '📊' },
  { to: '/prestamos', texto: 'Préstamos', icono: '📖' },
  { to: '/remitos', texto: 'Remitos', icono: '🚚' },
  { to: '/reservas', texto: 'Reservas', icono: '🔖' },
  { to: '/catalogo', texto: 'Catálogo', icono: '📚' },
  { to: '/recomendaciones', texto: 'Recomendaciones', icono: '✨' },
  { to: '/socios', texto: 'Socios', icono: '👥' },
  { to: '/sedes', texto: 'Sedes', icono: '🏛️' }
]
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <button class="hamburguesa" aria-label="Abrir menú" @click="menuAbierto = !menuAbierto">☰</button>
      <span class="marca">📚 Red de Bibliotecas</span>
    </header>

    <aside class="sidebar" :class="{ abierto: menuAbierto }">
      <div class="marca marca-lateral">
        <span class="logo">📚</span>
        <div>
          <strong>Red de Bibliotecas</strong>
        </div>
      </div>
      <nav>
        <RouterLink
          v-for="s in secciones"
          :key="s.to"
          :to="s.to"
          class="nav-link"
          :class="{ exacto: s.to === '/' }"
          @click="menuAbierto = false"
        >
          <span aria-hidden="true">{{ s.icono }}</span> {{ s.texto }}
        </RouterLink>
      </nav>
      <footer class="small muted">DAO · UTN FRC · 2026</footer>
    </aside>

    <main class="contenido">
      <RouterView />
    </main>

    <ToastHost />
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: grid; grid-template-columns: 232px minmax(0, 1fr); }
.sidebar {
  position: sticky; top: 0; height: 100vh;
  display: flex; flex-direction: column; gap: 20px;
  padding: 20px 14px; background: var(--surface); border-right: 1px solid var(--border);
}
.marca-lateral { display: flex; gap: 10px; align-items: center; padding: 0 6px; }
.marca-lateral .logo { font-size: 26px; }
.marca-lateral strong { display: block; font-size: 14px; }
.marca-lateral small { color: var(--muted); font-size: 11.5px; }
nav { display: grid; gap: 2px; }
.nav-link {
  display: flex; gap: 10px; align-items: center;
  padding: 8px 10px; border-radius: 8px;
  color: var(--ink-2); text-decoration: none; font-weight: 500;
}
.nav-link:hover { background: var(--surface-2); color: var(--ink); }
.nav-link.router-link-active:not(.exacto),
.nav-link.exacto.router-link-exact-active { background: var(--accent-soft); color: var(--ink); }
.sidebar footer { margin-top: auto; padding: 0 6px; }
.contenido { padding: 28px 32px 48px; max-width: 1400px; width: 100%; }
.topbar { display: none; }

@media (max-width: 860px) {
  .shell { grid-template-columns: 1fr; }
  .topbar {
    display: flex; align-items: center; gap: 12px; padding: 10px 16px;
    background: var(--surface); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 20;
  }
  .hamburguesa { border: 0; background: none; font-size: 20px; color: var(--ink); cursor: pointer; }
  .sidebar {
    position: fixed; z-index: 30; left: 0; width: 250px;
    transform: translateX(-100%); transition: transform 0.2s;
  }
  .sidebar.abierto { transform: none; box-shadow: 0 0 40px rgba(0, 0, 0, 0.25); }
  .contenido { padding: 20px 16px 40px; }
}
</style>
