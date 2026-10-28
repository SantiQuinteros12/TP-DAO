<script setup>
/**
 * Barras apiladas al 100% (una por fila) con leyenda siempre visible y
 * separación de 2px entre segmentos. Paleta categórica en orden fijo.
 */
defineProps({
  // [{ etiqueta, total, partes: { clave: valor } }]
  filas: { type: Array, required: true },
  // [{ clave, nombre }] — define el orden y el color (slot 1..4)
  series: { type: Array, required: true }
})

const ancho = (valor, total) => (total ? `${(valor / total) * 100}%` : '0%')
</script>

<template>
  <div>
    <ul class="leyenda">
      <li v-for="(s, i) in series" :key="s.clave">
        <span class="muestra" :style="{ background: `var(--series-${i + 1})` }" />{{ s.nombre }}
      </li>
    </ul>
    <div class="filas">
      <div v-for="f in filas" :key="f.etiqueta" class="fila">
        <span class="etiqueta">{{ f.etiqueta }}</span>
        <div class="pila">
          <template v-for="(s, i) in series" :key="s.clave">
            <div
              v-if="f.partes[s.clave]"
              class="segmento"
              :style="{ width: ancho(f.partes[s.clave], f.total), background: `var(--series-${i + 1})` }"
              :title="`${f.etiqueta} · ${s.nombre}: ${f.partes[s.clave]} de ${f.total}`"
            />
          </template>
          <div v-if="!f.total" class="vacio small muted">Sin ejemplares</div>
        </div>
        <span class="total small">{{ f.total }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.leyenda { display: flex; flex-wrap: wrap; gap: 6px 14px; list-style: none; margin: 0 0 12px; padding: 0; font-size: 12px; color: var(--ink-2); }
.leyenda li { display: inline-flex; align-items: center; gap: 6px; }
.muestra { width: 10px; height: 10px; border-radius: 3px; }
.filas { display: grid; gap: 10px; }
.fila { display: grid; grid-template-columns: minmax(110px, 30%) 1fr 32px; gap: 10px; align-items: center; }
.etiqueta { font-size: 12.5px; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pila { display: flex; gap: 2px; height: 18px; min-width: 0; }
.segmento { height: 100%; min-width: 3px; }
.segmento:first-child { border-radius: 4px 0 0 4px; }
.segmento:last-of-type { border-radius: 0 4px 4px 0; }
.segmento:only-of-type { border-radius: 4px; }
.segmento:hover { filter: brightness(1.12); }
.vacio { align-self: center; }
.total { text-align: right; font-variant-numeric: tabular-nums; }
</style>
