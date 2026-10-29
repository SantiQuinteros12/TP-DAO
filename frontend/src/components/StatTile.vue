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
  position: relative; display: grid; gap: var(--space-1); align-content: start;
  padding: var(--space-4) var(--space-5); min-width: 0; overflow: hidden;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.tile::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent);
}
.etiqueta {
  font-size: var(--text-xs); font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.valor {
  font-size: 30px; font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  color: var(--ink); font-variant-numeric: tabular-nums;
}
.detalle { font-size: var(--text-sm); color: var(--muted); }
</style>
