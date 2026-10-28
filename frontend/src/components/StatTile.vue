<script setup>
defineProps({
  etiqueta: { type: String, required: true },
  valor: { type: [String, Number], required: true },
  detalle: { type: String, default: '' }
})
</script>

<template>
  <div class="tile">
    <span class="etiqueta">{{ etiqueta }}</span>
    <span class="valor">{{ valor }}</span>
    <span v-if="detalle" class="detalle">{{ detalle }}</span>
  </div>
</template>

<style scoped>
.tile {
  display: grid; gap: 2px; padding: 14px 16px; min-width: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.etiqueta { font-size: 12.5px; color: var(--ink-2); }
.valor { font-size: 26px; font-weight: 600; line-height: 1.2; }
.detalle { font-size: 12px; color: var(--muted); }
</style>
