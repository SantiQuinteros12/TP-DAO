<script setup>
/**
 * Columnas agrupadas (una o más series por categoría) sobre un único eje Y
 * que arranca en cero. Grilla recesiva, leyenda para 2+ series, tooltip por
 * categoría con todas las series y área de hover más grande que la marca.
 */
import { computed, ref } from 'vue'

const props = defineProps({
  // [{ etiqueta, valores: { clave: número } }]
  categorias: { type: Array, required: true },
  // [{ clave, nombre }] — orden fijo = color fijo (slot 1, 2, …)
  series: { type: Array, required: true },
  unidad: { type: String, default: '' },
  alto: { type: Number, default: 220 }
})

const ANCHO = 600
const M = { arriba: 12, derecha: 8, abajo: 26, izquierda: 34 }
const interior = computed(() => ({ w: ANCHO - M.izquierda - M.derecha, h: props.alto - M.arriba - M.abajo }))

/** Tope "lindo" del eje y sus marcas (4 divisiones). */
const escala = computed(() => {
  const max = Math.max(1, ...props.categorias.flatMap((c) => props.series.map((s) => c.valores[s.clave] ?? 0)))
  const paso = (() => {
    const crudo = max / 4
    const base = 10 ** Math.floor(Math.log10(crudo))
    return [1, 2, 2.5, 5, 10].map((m) => m * base).find((p) => p >= crudo)
  })()
  const tope = Math.max(paso * 4, paso)
  return { tope, marcas: Array.from({ length: 5 }, (_, i) => i * paso).filter((v) => v <= tope) }
})

const y = (v) => M.arriba + interior.value.h * (1 - v / escala.value.tope)
const banda = computed(() => interior.value.w / Math.max(props.categorias.length, 1))
const anchoBarra = computed(() => Math.min(28, (banda.value * 0.7) / props.series.length))

function barras(ci) {
  const c = props.categorias[ci]
  const grupo = anchoBarra.value * props.series.length + 2 * (props.series.length - 1)
  const x0 = M.izquierda + banda.value * ci + (banda.value - grupo) / 2
  return props.series.map((s, si) => {
    const v = c.valores[s.clave] ?? 0
    const alto = Math.max(y(0) - y(v), v ? 2 : 0)
    return { clave: s.clave, x: x0 + si * (anchoBarra.value + 2), y: y(0) - alto, alto, color: `var(--series-${si + 1})` }
  })
}

/** Barra con extremo superior redondeado (4px) apoyada sobre la base. */
function camino(b) {
  const r = Math.min(4, b.alto, anchoBarra.value / 2)
  const { x, y: top, alto } = b
  const w = anchoBarra.value
  const base = top + alto
  return `M${x},${base}V${top + r}Q${x},${top} ${x + r},${top}H${x + w - r}Q${x + w},${top} ${x + w},${top + r}V${base}Z`
}

const activo = ref(null)
const tip = computed(() => {
  if (activo.value === null) return null
  const xs = barras(activo.value)
  return { x: ((xs[0].x + xs.at(-1).x + anchoBarra.value) / 2 / ANCHO) * 100, y: Math.min(...xs.map((b) => b.y)) }
})
const n = (v) => (v ?? 0).toLocaleString('es-AR')
</script>

<template>
  <div class="columnas">
    <ul v-if="series.length > 1" class="leyenda">
      <li v-for="(s, i) in series" :key="s.clave">
        <span class="muestra-color" :style="{ background: `var(--series-${i + 1})` }" />{{ s.nombre }}
      </li>
    </ul>
    <p v-if="!categorias.length" class="empty">Sin datos en el período.</p>
    <div v-else class="lienzo">
      <svg :viewBox="`0 0 ${ANCHO} ${alto}`" role="img" :aria-label="`Gráfico de columnas: ${categorias.length} categorías`">
        <g class="grilla">
          <template v-for="m in escala.marcas" :key="m">
            <line :x1="M.izquierda" :x2="ANCHO - M.derecha" :y1="y(m)" :y2="y(m)" :class="{ base: m === 0 }" />
            <text :x="M.izquierda - 6" :y="y(m) + 4" text-anchor="end">{{ n(m) }}</text>
          </template>
        </g>
        <g v-for="(c, ci) in categorias" :key="c.etiqueta">
          <rect
            class="hover"
            :class="{ on: activo === ci }"
            :x="M.izquierda + banda * ci"
            :y="M.arriba"
            :width="banda"
            :height="interior.h"
            @mouseenter="activo = ci"
            @mouseleave="activo = null"
          />
          <path v-for="b in barras(ci)" :key="b.clave" :d="camino(b)" :fill="b.color" class="barra" />
          <text class="eje-x" :x="M.izquierda + banda * ci + banda / 2" :y="alto - 8" text-anchor="middle">{{ c.etiqueta }}</text>
        </g>
      </svg>
      <div v-if="tip" class="tooltip-grafico" :style="{ left: `${tip.x}%`, top: `${(tip.y / alto) * 100}%` }">
        <strong>{{ categorias[activo].etiqueta }}</strong>
        <span v-for="(s, i) in series" :key="s.clave" class="linea">
          <span class="muestra-color" :style="{ background: `var(--series-${i + 1})` }" />{{ s.nombre }}
          <b>{{ n(categorias[activo].valores[s.clave]) }} {{ unidad }}</b>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.columnas { display: grid; gap: 10px; }
.lienzo { position: relative; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
.grilla line { stroke: var(--grid); stroke-width: 1; }
.grilla line.base { stroke: var(--axis); }
.grilla text, .eje-x { font-size: 11px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.hover { fill: transparent; pointer-events: all; }
.hover.on { fill: var(--surface-2); }
.barra { pointer-events: none; }
.leyenda { display: flex; flex-wrap: wrap; gap: 6px 14px; list-style: none; margin: 0; padding: 0; font-size: 12px; color: var(--ink-2); }
.leyenda li { display: inline-flex; align-items: center; gap: 6px; }
</style>
