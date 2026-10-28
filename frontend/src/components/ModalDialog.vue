<script setup>
/**
 * Diálogo modal accesible (se cierra con Esc o clic en el fondo).
 */
import { onBeforeUnmount, onMounted } from 'vue'

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
          <button class="cerrar" aria-label="Cerrar" @click="emit('cerrar')">✕</button>
        </header>
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.fondo {
  position: fixed; inset: 0; z-index: 50;
  background: rgba(0, 0, 0, 0.38);
  display: grid; place-items: center; padding: 16px;
}
.dialogo {
  width: 100%; max-height: calc(100vh - 32px); overflow: auto;
  background: var(--surface); color: var(--ink);
  border-radius: 14px; padding: 20px; border: 1px solid var(--border);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
}
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.cerrar { border: 0; background: none; font-size: 16px; color: var(--muted); cursor: pointer; }
</style>
