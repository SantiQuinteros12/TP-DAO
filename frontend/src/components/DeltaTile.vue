<script setup>
/**
 * Métrica comparativa: valor del período actual frente al anterior, con
 * variación porcentual (flecha + texto, nunca sólo color).
 */
import { computed } from 'vue'

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
  return `${v > 0 ? '▲' : '▼'} ${Math.abs(v).toLocaleString('es-AR', { maximumFractionDigits: 0 })}%`
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
      <span class="delta" :class="tono">{{ texto }}</span>
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
  display: grid; gap: 4px; padding: 14px 16px; min-width: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.etiqueta { font-size: 12.5px; color: var(--ink-2); }
.fila { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.valor { font-size: 24px; font-weight: 650; line-height: 1.2; font-variant-numeric: tabular-nums; }
.delta { font-size: 12px; font-weight: 600; padding: 1px 7px; border-radius: 999px; }
.sube-bien { background: var(--good-bg); color: var(--good-ink); }
.sube-mal { background: var(--critical-bg); color: var(--critical-ink); }
.neutro { background: var(--neutral-bg); color: var(--neutral-ink); }
.comparacion { display: grid; gap: 2px; margin-top: 2px; }
.barra { display: block; height: 5px; border-radius: 0 3px 3px 0; min-width: 2px; }
.barra.actual { background: var(--series-1); }
.barra.anterior { background: var(--axis); }
.detalle { font-size: 12px; color: var(--muted); }
</style>
