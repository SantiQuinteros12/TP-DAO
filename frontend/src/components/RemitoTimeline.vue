<script setup>
/**
 * Línea de tiempo con el historial de estados del remito (trazabilidad).
 */
import EstadoBadge from './EstadoBadge.vue'
import { etiqueta, fechaHora } from '../composables/formato'

defineProps({ historial: { type: Array, required: true } })

const metadatos = (m) =>
  [
    m.ubicacion && `📍 ${m.ubicacion}`,
    m.responsable && `👤 ${m.responsable}`,
    m.condicion && `Estado físico: ${etiqueta(m.condicion)}`
  ]
    .filter(Boolean)
    .join(' · ')
</script>

<template>
  <ol class="timeline">
    <li v-for="(m, i) in historial" :key="i" :class="{ incidencia: m.tipo_incidencia, ultimo: i === historial.length - 1 }">
      <span class="punto" aria-hidden="true" />
      <div class="cuerpo">
        <div class="linea">
          <EstadoBadge :estado="m.estado" />
          <time class="small muted">{{ fechaHora(m.fecha_hora) }}</time>
        </div>
        <p v-if="m.tipo_incidencia" class="detalle">
          <strong>Incidencia: {{ etiqueta(m.tipo_incidencia) }}</strong>
        </p>
        <p v-if="m.observacion" class="detalle">{{ m.observacion }}</p>
        <p v-if="metadatos(m)" class="detalle small muted">{{ metadatos(m) }}</p>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.timeline { list-style: none; margin: 0; padding: 0; }
li { position: relative; display: grid; grid-template-columns: 22px 1fr; gap: 8px; padding-bottom: 14px; }
li::before {
  content: ''; position: absolute; left: 6px; top: 16px; bottom: -2px;
  width: 2px; background: var(--grid);
}
li.ultimo::before { display: none; }
.punto {
  width: 14px; height: 14px; margin-top: 4px; border-radius: 50%;
  background: var(--accent); box-shadow: 0 0 0 3px var(--surface);
}
li.incidencia .punto { background: var(--serious); }
.linea { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.detalle { margin: 4px 0 0; font-size: 13px; }
.detalle:empty { display: none; }
</style>
