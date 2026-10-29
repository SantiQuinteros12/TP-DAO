<script setup>
/**
 * Métrica comparativa: valor del período actual frente al anterior, con
 * variación porcentual (flecha + texto, nunca sólo color).
 */
import { computed } from 'vue'
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-vue-next'

const props = defineProps({
  etiqueta: { type: String, required: true },
  actual: { type: Number, required: true },
  anterior: { type: Number, required: true },
  formato: { type: Function, default: (v) => v.toLocaleString('es-AR') },
  // true si que la métrica suba es malo (p. ej. multas)
  invertido: { type: Boolean, default: false }
})

const variacion = computed(() => {
  if (!props.anterior) return props.actual ? null : 0
  return ((props.actual - props.anterior) / props.anterior) * 100
})
const tono = computed(() => {
  const v = variacion.value
  if (v === null || Math.abs(v) < 0.5) return 'neutro'
  return (v > 0) !== props.invertido ? 'sube-bien' : 'sube-mal'
})
const texto = computed(() => {
  const v = variacion.value
  if (v === null) return 'nuevo'
  if (Math.abs(v) < 0.5) return 'sin cambios'
  return `${Math.abs(v).toLocaleString('es-AR', { maximumFractionDigits: 0 })}%`
})
const flecha = computed(() => {
  const v = variacion.value
  if (v === null || Math.abs(v) < 0.5) return null
  return v > 0 ? ArrowUpRight : ArrowDownRight
})
const proporcion = computed(() => {
  const max = Math.max(props.actual, props.anterior, 1)
  return { actual: (props.actual / max) * 100, anterior: (props.anterior / max) * 100 }
})
</script>

<template>
  <div class="tile">
    <span class="etiqueta">{{ etiqueta }}</span>
    <div class="fila">
      <span class="valor">{{ formato(actual) }}</span>
      <span class="delta" :class="tono" :aria-label="flecha ? `${variacion > 0 ? 'Sube' : 'Baja'} ${texto}` : texto">
        <component :is="flecha ?? Minus" :size="14" :stroke-width="2.5" aria-hidden="true" />{{ texto }}
      </span>
    </div>
    <div class="comparacion" :title="`Actual: ${formato(actual)} · Anterior: ${formato(anterior)}`">
      <span class="barra actual" :style="{ width: `${proporcion.actual}%` }" />
      <span class="barra anterior" :style="{ width: `${proporcion.anterior}%` }" />
    </div>
    <span class="detalle">Período anterior: {{ formato(anterior) }}</span>
  </div>
</template>

<style scoped>
.tile {
  display: grid; gap: 6px; align-content: start; padding: var(--space-4) var(--space-5); min-width: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.etiqueta {
  font-size: var(--text-xs); font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.fila { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); flex-wrap: wrap; }
.valor { font-size: 28px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.delta {
  display: inline-flex; align-items: center; gap: 2px;
  font-size: var(--text-sm); font-weight: 650; padding: 2px 8px 2px 6px; border-radius: var(--radius-pill);
  font-variant-numeric: tabular-nums;
}
.sube-bien { background: var(--good-bg); color: var(--good-ink); }
.sube-mal { background: var(--critical-bg); color: var(--critical-ink); }
.neutro { background: var(--neutral-bg); color: var(--neutral-ink); }
.comparacion { display: grid; gap: 3px; margin-top: 2px; }
.barra { display: block; height: 6px; border-radius: 0 3px 3px 0; min-width: 2px; transition: width 300ms var(--ease); }
.barra.actual { background: var(--series-1); }
.barra.anterior { background: var(--axis); }
.detalle { font-size: var(--text-sm); color: var(--muted); }
</style>
