<script setup>
/**
 * Gráfico de torta (anillo) para composición de un total. Máximo 6
 * porciones: el resto se agrupa en "Otros". Separación de 2px entre
 * porciones, total en el centro, leyenda con valor y porcentaje (la
 * identidad nunca depende sólo del color) y tooltip al pasar el mouse.
 */
import { computed, ref } from 'vue'

const props = defineProps({
  // [{ etiqueta, valor }]
  datos: { type: Array, required: true },
  unidad: { type: String, default: '' },
  maximo: { type: Number, default: 6 }
})

const R = 70
const GROSOR = 22
const CIRC = 2 * Math.PI * R

const porciones = computed(() => {
  const orden = [...props.datos].filter((d) => d.valor > 0).sort((a, b) => b.valor - a.valor)
  let lista = orden
  if (orden.length > props.maximo) {
    const resto = orden.slice(props.maximo - 1).reduce((s, d) => s + d.valor, 0)
    lista = [...orden.slice(0, props.maximo - 1), { etiqueta: 'Otros', valor: resto }]
  }
  const total = lista.reduce((s, d) => s + d.valor, 0)
  let acumulado = 0
  return lista.map((d, i) => {
    const largo = total ? (d.valor / total) * CIRC : 0
    const p = {
      ...d,
      color: `var(--series-${i + 1})`,
      pct: total ? (100 * d.valor) / total : 0,
      // 2px de separación entre porciones (si hay más de una)
      dash: `${Math.max(largo - (lista.length > 1 ? 2 : 0), 0.5)} ${CIRC}`,
      offset: -acumulado
    }
    acumulado += largo
    return p
  })
})
const total = computed(() => porciones.value.reduce((s, p) => s + p.valor, 0))

const activo = ref(null)
const tip = ref({ x: 0, y: 0 })
function mover(e, i) {
  const caja = e.currentTarget.closest('.donut').getBoundingClientRect()
  tip.value = { x: e.clientX - caja.left, y: e.clientY - caja.top }
  activo.value = i
}
const pct = (v) => `${v.toLocaleString('es-AR', { maximumFractionDigits: 1 })}%`
</script>

<template>
  <div class="donut">
    <p v-if="!total" class="empty">Sin datos en el período.</p>
    <template v-else>
      <div class="grafico">
        <svg viewBox="0 0 180 180" role="img" :aria-label="porciones.map((p) => `${p.etiqueta}: ${p.valor}`).join(', ')">
          <g transform="rotate(-90 90 90)">
            <circle cx="90" cy="90" :r="R" fill="none" stroke="var(--grid)" :stroke-width="GROSOR" />
            <circle
              v-for="(p, i) in porciones"
              :key="p.etiqueta"
              cx="90"
              cy="90"
              :r="R"
              fill="none"
              :stroke="p.color"
              :stroke-width="activo === i ? GROSOR + 6 : GROSOR"
              :stroke-dasharray="p.dash"
              :stroke-dashoffset="p.offset"
              class="porcion"
              :class="{ atenuada: activo !== null && activo !== i }"
              @mousemove="mover($event, i)"
              @mouseleave="activo = null"
            />
          </g>
          <text x="90" y="86" text-anchor="middle" class="total">{{ total.toLocaleString('es-AR') }}</text>
          <text x="90" y="106" text-anchor="middle" class="unidad">{{ unidad }}</text>
        </svg>
        <div v-if="activo !== null" class="tooltip-grafico" :style="{ left: `${tip.x}px`, top: `${tip.y}px` }">
          <strong>{{ porciones[activo].etiqueta }}</strong>
          <span class="linea">
            <span class="muestra-color" :style="{ background: porciones[activo].color }" />
            {{ porciones[activo].valor.toLocaleString('es-AR') }} {{ unidad }}<b>{{ pct(porciones[activo].pct) }}</b>
          </span>
        </div>
      </div>
      <ul class="leyenda">
        <li
          v-for="(p, i) in porciones"
          :key="p.etiqueta"
          :class="{ activa: activo === i }"
          @mouseenter="activo = i"
          @mouseleave="activo = null"
        >
          <span class="muestra-color" :style="{ background: p.color }" />
          <span class="nombre">{{ p.etiqueta }}</span>
          <span class="valor">{{ p.valor.toLocaleString('es-AR') }}</span>
          <span class="pct">{{ pct(p.pct) }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.donut { position: relative; display: grid; grid-template-columns: minmax(110px, 140px) minmax(0, 1fr); gap: var(--space-4); align-items: center; }
@media (max-width: 420px) { .donut { grid-template-columns: 1fr; justify-items: center; } }
.grafico { position: relative; width: 100%; max-width: 160px; }
.donut .empty { grid-column: 1 / -1; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
.porcion { cursor: pointer; transition: stroke-width var(--dur) var(--ease), opacity var(--dur) var(--ease); }
.porcion.atenuada { opacity: 0.45; }
.total { font-size: 26px; font-weight: 700; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; fill: var(--ink); }
.unidad { font-size: 12px; fill: var(--muted); }
.leyenda { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; min-width: 0; width: 100%; }
.leyenda li {
  display: grid; grid-template-columns: 10px minmax(0, 1fr) auto 46px; gap: 6px 8px; align-items: center;
  padding: 5px 8px; border-radius: var(--radius-sm); font-size: var(--text-sm); color: var(--ink-2);
  transition: background var(--dur) var(--ease);
}
.leyenda li.activa { background: var(--surface-2); color: var(--ink); }
.nombre { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.valor { font-variant-numeric: tabular-nums; color: var(--ink); font-weight: 600; }
.pct { font-variant-numeric: tabular-nums; text-align: right; color: var(--muted); }
</style>
