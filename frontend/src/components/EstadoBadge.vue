<script setup>
/**
 * Insignia de estado. El color nunca va solo: siempre lleva ícono y texto.
 * Un color por tipo de estado en toda la aplicación:
 *   verde = disponible/completado · azul = en curso/en tránsito ·
 *   violeta = reservado · ámbar = pendiente · rojo = vencido/dañado/pérdida ·
 *   gris = cancelado.
 */
import { computed } from 'vue'
import {
  AlertTriangle, ArrowRightLeft, Ban, Bookmark, CircleCheck, CircleDot, Clock, OctagonAlert
} from 'lucide-vue-next'
import { etiqueta } from '../composables/formato'

const props = defineProps({ estado: { type: String, default: '' } })

const TONOS = {
  good: { estados: ['DISPONIBLE', 'ACTIVA', 'HABILITADO', 'RECIBIDO', 'DEVUELTO', 'CUMPLIDA', 'BUENA'], icono: CircleCheck },
  info: { estados: ['ACTIVO', 'EN_PRESTAMO', 'DESPACHADO', 'EN_TRANSITO'], icono: ArrowRightLeft },
  reserved: { estados: ['RESERVADO', 'LISTO_PARA_RETIRO'], icono: Bookmark },
  warning: { estados: ['PENDIENTE', 'PENDIENTE_ENVIO', 'CREADO', 'EMPAQUETADO', 'DETERIORADA'], icono: Clock },
  serious: { estados: ['CON_INCIDENCIA'], icono: AlertTriangle },
  critical: { estados: ['VENCIDO', 'VENCIDA', 'DANADO', 'DANADA', 'EXTRAVIADO', 'BAJA', 'INHABILITADO'], icono: OctagonAlert },
  neutral: { estados: ['CANCELADO', 'CANCELADA'], icono: Ban }
}

const tono = computed(() => {
  const encontrado = Object.entries(TONOS).find(([, t]) => t.estados.includes(props.estado))
  return encontrado ? encontrado[0] : 'neutral'
})
const icono = computed(() => (TONOS[tono.value].estados.includes(props.estado) ? TONOS[tono.value].icono : CircleDot))
</script>

<template>
  <span class="badge" :class="tono">
    <component :is="icono" class="icono" :size="13" :stroke-width="2.4" aria-hidden="true" />{{ etiqueta(estado) }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 2px 10px 2px 8px; border-radius: var(--radius-pill);
  font-size: var(--text-sm); font-weight: 600; line-height: 20px; white-space: nowrap;
  border: 1px solid color-mix(in srgb, currentColor 16%, transparent);
}
.icono { flex: none; }
.good { background: var(--good-bg); color: var(--good-ink); }
.info { background: var(--info-bg); color: var(--info-ink); }
.reserved { background: var(--reserved-bg); color: var(--reserved-ink); }
.warning { background: var(--warning-bg); color: var(--warning-ink); }
.serious { background: var(--serious-bg); color: var(--serious-ink); }
.critical { background: var(--critical-bg); color: var(--critical-ink); }
.neutral { background: var(--neutral-bg); color: var(--neutral-ink); }
</style>
