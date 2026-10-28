<script setup>
import { useToast } from '../composables/useToast'

const { toasts, cerrar } = useToast()
</script>

<template>
  <div class="toasts" aria-live="polite">
    <div
      v-for="t in toasts"
      :key="t.id"
      class="toast"
      :class="t.tipo"
      role="status"
      @click="cerrar(t.id)"
    >
      <span aria-hidden="true">{{ t.tipo === 'error' ? '⛔' : '✓' }}</span>
      <span>{{ t.mensaje }}</span>
    </div>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed; right: 16px; bottom: 16px; z-index: 100;
  display: grid; gap: 8px; max-width: min(420px, calc(100vw - 32px));
}
.toast {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 11px 14px; border-radius: 10px; cursor: pointer;
  background: var(--surface); border: 1px solid var(--border);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.14); font-size: 13.5px;
}
.toast.ok span:first-child { color: var(--good-ink); font-weight: 700; }
.toast.error { background: var(--critical-bg); color: var(--critical-ink); }
</style>
