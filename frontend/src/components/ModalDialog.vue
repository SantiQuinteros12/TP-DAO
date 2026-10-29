<script setup>
/**
 * Diálogo modal accesible (se cierra con Esc o clic en el fondo).
 * Encabezado fijo, cuerpo con desplazamiento y, si el contenido trae un
 * `.form-actions`, éste se muestra como pie fijo (ver styles.css).
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { X } from 'lucide-vue-next'

defineProps({
  titulo: { type: String, required: true },
  ancho: { type: String, default: '520px' }
})
const emit = defineEmits(['cerrar'])

const alPresionar = (e) => e.key === 'Escape' && emit('cerrar')
onMounted(() => window.addEventListener('keydown', alPresionar))
onBeforeUnmount(() => window.removeEventListener('keydown', alPresionar))
</script>

<template>
  <Teleport to="body">
    <div class="fondo" @mousedown.self="emit('cerrar')">
      <div class="dialogo" role="dialog" aria-modal="true" :aria-label="titulo" :style="{ maxWidth: ancho }">
        <header>
          <h2>{{ titulo }}</h2>
          <button class="cerrar" type="button" aria-label="Cerrar" @click="emit('cerrar')"><X :size="18" /></button>
        </header>
        <div class="dialogo-cuerpo">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.fondo {
  position: fixed; inset: 0; z-index: 50;
  display: grid; place-items: center; padding: var(--space-4);
  background: var(--overlay);
  -webkit-backdrop-filter: blur(3px); backdrop-filter: blur(3px);
  animation: fondo-entra 160ms var(--ease);
}
.dialogo {
  display: flex; flex-direction: column;
  width: 100%; max-height: calc(100vh - 32px); overflow: hidden;
  background: var(--surface); color: var(--ink);
  border-radius: 16px; border: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  animation: dialogo-entra 180ms var(--ease);
}
header {
  display: flex; justify-content: space-between; align-items: center; gap: var(--space-3);
  padding: var(--space-4) var(--space-4) var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border);
}
header h2 { font-size: var(--text-lg); }
.cerrar {
  display: grid; place-items: center; flex: none; width: 36px; height: 36px;
  border: 0; border-radius: var(--radius-md); background: none; color: var(--muted); cursor: pointer;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease);
}
.cerrar:hover { background: var(--surface-2); color: var(--ink); }
.cerrar:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--focus); }
.dialogo-cuerpo { overflow-y: auto; padding: var(--space-5) var(--space-6); overscroll-behavior: contain; }

@media (max-width: 520px) {
  .fondo { place-items: end center; padding: 0; }
  .dialogo { max-height: 92vh; border-radius: 16px 16px 0 0; }
  header { padding-left: var(--space-4); }
  .dialogo-cuerpo { padding: var(--space-4); }
}

@keyframes fondo-entra { from { opacity: 0; } }
@keyframes dialogo-entra { from { opacity: 0; transform: translateY(8px) scale(0.98); } }
</style>
