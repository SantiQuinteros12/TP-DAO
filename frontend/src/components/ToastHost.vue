<script setup>
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-vue-next'
import { useToast } from '../composables/useToast'

const { toasts, cerrar } = useToast()

const ICONOS = { ok: CheckCircle2, error: XCircle, warning: AlertTriangle, info: Info }
</script>

<template>
  <div class="toasts" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast"
        :class="t.tipo"
        role="status"
        @click="cerrar(t.id)"
      >
        <component :is="ICONOS[t.tipo] ?? Info" class="icono" :size="20" aria-hidden="true" />
        <span class="mensaje">{{ t.mensaje }}</span>
        <X class="cerrar" :size="16" aria-hidden="true" />
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed; right: var(--space-4); bottom: var(--space-4); z-index: 100;
  display: grid; gap: var(--space-2); width: min(400px, calc(100vw - 32px));
}
.toast {
  --tono: var(--info); --tono-ink: var(--info-ink);
  display: flex; gap: var(--space-3); align-items: flex-start;
  padding: var(--space-3) var(--space-4); border-radius: var(--radius);
  background: var(--surface); color: var(--ink); cursor: pointer;
  border: 1px solid var(--border); border-left: 4px solid var(--tono);
  box-shadow: var(--shadow-lg); font-size: 14px; line-height: 1.45;
}
.toast.ok { --tono: var(--good); --tono-ink: var(--good-ink); }
.toast.error { --tono: var(--critical); --tono-ink: var(--critical-ink); }
.toast.warning { --tono: var(--warning); --tono-ink: var(--warning-ink); }
.icono { flex: none; color: var(--tono-ink); margin-top: 1px; }
.mensaje { flex: 1; font-weight: 500; }
.cerrar { flex: none; color: var(--muted); margin-top: 2px; opacity: 0.7; }
.toast:hover .cerrar { opacity: 1; }

.toast-enter-active, .toast-leave-active { transition: opacity 180ms var(--ease), transform 180ms var(--ease); }
.toast-enter-from { opacity: 0; transform: translateY(8px); }
.toast-leave-to { opacity: 0; transform: translateX(16px); }

@media (max-width: 520px) {
  .toasts { right: 16px; left: 16px; width: auto; }
}
</style>
