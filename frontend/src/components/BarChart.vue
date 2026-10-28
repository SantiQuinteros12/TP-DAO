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
.barras { display: grid; gap: 8px; }
.fila { display: grid; grid-template-columns: minmax(110px, 38%) 1fr; gap: 10px; align-items: center; }
.etiqueta { font-size: 12.5px; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pista { display: flex; align-items: center; gap: 6px; min-width: 0; border-left: 1px solid var(--axis); }
.barra {
  height: 18px; min-width: 2px; background: var(--series-1);
  border-radius: 0 4px 4px 0;
}
.fila:hover .barra { filter: brightness(1.1); }
.valor { font-size: 12px; font-variant-numeric: tabular-nums; color: var(--ink); }
</style>
