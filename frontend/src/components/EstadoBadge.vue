<script setup>
/**
 * Insignia de estado. El color nunca va solo: siempre lleva ícono y texto.
 */
import { computed } from 'vue'
import { etiqueta } from '../composables/formato'

const props = defineProps({ estado: { type: String, default: '' } })

const TONOS = {
  good: { estados: ['DISPONIBLE', 'ACTIVA', 'HABILITADO', 'RECIBIDO', 'DEVUELTO', 'CUMPLIDA', 'BUENA'], icono: '●' },
  info: { estados: ['ACTIVO', 'EN_PRESTAMO', 'DESPACHADO', 'EN_TRANSITO', 'LISTO_PARA_RETIRO'], icono: '◆' },
  warning: { estados: ['RESERVADO', 'PENDIENTE', 'PENDIENTE_ENVIO', 'CREADO', 'EMPAQUETADO', 'DETERIORADA', 'VENCIDO'], icono: '▲' },
  serious: { estados: ['CON_INCIDENCIA', 'DANADO', 'DANADA', 'VENCIDA'], icono: '◼' },
  critical: { estados: ['EXTRAVIADO', 'BAJA', 'INHABILITADO'], icono: '✕' },
  neutral: { estados: ['CANCELADO', 'CANCELADA'], icono: '○' }
}

const tono = computed(() => {
  const encontrado = Object.entries(TONOS).find(([, t]) => t.estados.includes(props.estado))
  return encontrado ? encontrado[0] : 'neutral'
})
const icono = computed(() => TONOS[tono.value].icono)
</script>

<template>
  <span class="badge" :class="tono">
    <span aria-hidden="true" class="icono">{{ icono }}</span>{{ etiqueta(estado) }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 2px 9px; border-radius: 999px;
  font-size: 12px; font-weight: 500; white-space: nowrap;
}
.icono { font-size: 9px; }
.good { background: var(--good-bg); color: var(--good-ink); }
.info { background: var(--info-bg); color: var(--info-ink); }
.warning { background: var(--warning-bg); color: var(--warning-ink); }
.serious { background: var(--serious-bg); color: var(--serious-ink); }
.critical { background: var(--critical-bg); color: var(--critical-ink); }
.neutral { background: var(--neutral-bg); color: var(--neutral-ink); }
</style>
