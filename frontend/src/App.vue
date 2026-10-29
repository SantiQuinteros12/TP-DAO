<script setup>
import { ref } from 'vue'
import {
  BookOpen, Bookmark, Building2, LayoutDashboard, Library, Menu, Sparkles, Truck, Users, X
} from 'lucide-vue-next'
import ToastHost from './components/ToastHost.vue'

const menuAbierto = ref(false)

const secciones = [
  { to: '/', texto: 'Reportes', icono: LayoutDashboard },
  { to: '/prestamos', texto: 'Préstamos', icono: BookOpen },
  { to: '/remitos', texto: 'Remitos', icono: Truck },
  { to: '/reservas', texto: 'Reservas', icono: Bookmark },
  { to: '/catalogo', texto: 'Catálogo', icono: Library },
  { to: '/recomendaciones', texto: 'Recomendaciones', icono: Sparkles },
  { to: '/socios', texto: 'Socios', icono: Users },
  { to: '/sedes', texto: 'Sedes', icono: Building2 }
]
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <button class="hamburguesa" :aria-label="menuAbierto ? 'Cerrar menú' : 'Abrir menú'" @click="menuAbierto = !menuAbierto">
        <component :is="menuAbierto ? X : Menu" :size="22" />
      </button>
      <span class="marca-compacta"><span class="logo"><Library :size="16" /></span> Red de Bibliotecas</span>
    </header>

    <div v-if="menuAbierto" class="velo" aria-hidden="true" @click="menuAbierto = false" />

    <aside class="sidebar" :class="{ abierto: menuAbierto }">
      <div class="marca">
        <span class="logo"><Library :size="20" /></span>
        <div>
          <strong>Red de Bibliotecas</strong>
          <small>Gestión interbibliotecaria</small>
        </div>
      </div>
      <nav aria-label="Secciones">
        <RouterLink
          v-for="s in secciones"
          :key="s.to"
          :to="s.to"
          class="nav-link"
          :class="{ exacto: s.to === '/' }"
          @click="menuAbierto = false"
        >
          <component :is="s.icono" :size="18" :stroke-width="2" aria-hidden="true" />
          <span>{{ s.texto }}</span>
        </RouterLink>
      </nav>
      <footer>DAO · UTN FRC · 2026</footer>
    </aside>

    <main class="contenido">
      <RouterView />
    </main>

    <ToastHost />
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: grid; grid-template-columns: var(--sidebar-w) minmax(0, 1fr); }

.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  display: flex; flex-direction: column; gap: var(--space-6);
  padding: var(--space-5) var(--space-3);
  background: var(--surface); border-right: 1px solid var(--border);
}
.marca { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-1) var(--space-2); }
.logo {
  display: grid; place-items: center; flex: none; width: 38px; height: 38px; border-radius: 10px;
  background: var(--accent); color: var(--accent-ink);
}
.marca strong { display: block; font-size: var(--text-md); font-weight: 700; letter-spacing: -0.01em; line-height: 1.25; }
.marca small { display: block; color: var(--muted); font-size: var(--text-xs); }

nav { display: grid; gap: 2px; }
.nav-link {
  position: relative; display: flex; gap: var(--space-3); align-items: center;
  min-height: 40px; padding: 0 var(--space-3); border-radius: var(--radius-md);
  color: var(--ink-2); text-decoration: none; font-size: 14.5px; font-weight: 550;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease);
}
.nav-link svg { flex: none; color: var(--muted); transition: color var(--dur) var(--ease); }
.nav-link:hover { background: var(--surface-2); color: var(--ink); }
.nav-link:hover svg { color: var(--ink-2); }
.nav-link:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--focus); }
.nav-link.router-link-active:not(.exacto),
.nav-link.exacto.router-link-exact-active { background: var(--accent-soft); color: var(--accent); font-weight: 650; }
.nav-link.router-link-active:not(.exacto) svg,
.nav-link.exacto.router-link-exact-active svg { color: var(--accent); }
.nav-link.router-link-active:not(.exacto)::before,
.nav-link.exacto.router-link-exact-active::before {
  content: ''; position: absolute; left: calc(-1 * var(--space-3)); top: 8px; bottom: 8px;
  width: 3px; border-radius: 0 3px 3px 0; background: var(--accent);
}

.sidebar footer { margin-top: auto; padding: 0 var(--space-3); font-size: var(--text-xs); color: var(--muted); }

.contenido {
  width: 100%; max-width: var(--content-max); margin: 0 auto;
  padding: var(--space-8) var(--space-8) var(--space-10);
}

.topbar, .velo { display: none; }

@media (max-width: 860px) {
  .shell { grid-template-columns: 1fr; }
  .topbar {
    display: flex; align-items: center; gap: var(--space-3); min-height: 56px; padding: 0 var(--space-4);
    background: var(--surface); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 20;
  }
  .hamburguesa {
    display: grid; place-items: center; width: 40px; height: 40px; margin-left: -8px;
    border: 0; border-radius: var(--radius-md); background: none; color: var(--ink); cursor: pointer;
  }
  .hamburguesa:hover { background: var(--surface-2); }
  .marca-compacta { display: flex; align-items: center; gap: var(--space-2); font-weight: 700; }
  .marca-compacta .logo { width: 28px; height: 28px; border-radius: 8px; }
  .velo {
    display: block; position: fixed; inset: 0; z-index: 25;
    background: var(--overlay); animation: aparecer var(--dur) var(--ease);
  }
  .sidebar {
    position: fixed; z-index: 30; left: 0; top: 0; width: min(280px, 85vw);
    transform: translateX(-100%); transition: transform 200ms var(--ease);
  }
  .sidebar.abierto { transform: none; box-shadow: var(--shadow-lg); }
  .contenido { padding: var(--space-5) var(--space-4) var(--space-8); }
}

@keyframes aparecer { from { opacity: 0; } }
</style>
