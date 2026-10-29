<script setup>
/**
 * Gráfico de barras horizontales de una sola serie (sin leyenda: el título
 * de la tarjeta nombra la serie). Valor rotulado en la punta de cada barra;
 * tooltip nativo al pasar el mouse.
 */
import { computed } from 'vue'

const props = defineProps({
  // [{ etiqueta, valor, detalle? }]
  datos: { type: Array, required: true },
  unidad: { type: String, default: '' }
})

const maximo = computed(() => Math.max(1, ...props.datos.map((d) => d.valor)))
</script>

<template>
  <div class="barras" role="img" :aria-label="`Gráfico de barras con ${datos.length} elementos`">
    <div v-for="d in datos" :key="d.etiqueta" class="fila" :title="`${d.etiqueta}: ${d.valor} ${unidad}${d.detalle ? ' · ' + d.detalle : ''}`">
      <span class="etiqueta">{{ d.etiqueta }}</span>
      <div class="pista">
        <div class="barra" :style="{ width: `${(d.valor / maximo) * 100}%` }" />
        <span class="valor">{{ d.valor }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.barras { display: grid; gap: 10px; }
.fila { display: grid; grid-template-columns: minmax(110px, 38%) 1fr; gap: 12px; align-items: center; border-radius: var(--radius-sm); }
.etiqueta { font-size: var(--text-sm); color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pista { display: flex; align-items: center; gap: 6px; min-width: 0; border-left: 1px solid var(--axis); }
.barra {
  height: 20px; min-width: 2px; background: var(--series-1);
  border-radius: 0 4px 4px 0; transition: filter var(--dur) var(--ease), width 300ms var(--ease);
}
.fila:hover .barra { filter: brightness(1.12); }
.fila:hover .etiqueta { color: var(--ink); }
.valor { font-size: var(--text-sm); font-weight: 600; font-variant-numeric: tabular-nums; color: var(--ink); }
</style>
