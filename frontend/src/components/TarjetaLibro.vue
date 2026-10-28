<script setup>
/**
 * Tarjeta de un libro recomendado: afinidad, motivos y disponibilidad.
 */
defineProps({
  libro: { type: Object, required: true },
  posicion: { type: Number, required: true },
  // Si hay socio, se ofrece pedirlo prestado directamente
  socioId: { type: [Number, String], default: null }
})
defineEmits(['similares'])
</script>

<template>
  <article class="tarjeta">
    <header>
      <span class="posicion">{{ posicion }}</span>
      <div class="titulos">
        <h3>{{ libro.titulo }}</h3>
        <span class="small muted">{{ libro.autor }}<template v-if="libro.anio_publicacion"> · {{ libro.anio_publicacion }}</template></span>
      </div>
    </header>

    <div class="afinidad" :title="`Afinidad ${libro.puntaje} de 100`">
      <span class="small muted">Afinidad</span>
      <span class="medidor"><span :style="{ width: `${libro.puntaje}%` }" /></span>
      <strong class="small">{{ libro.puntaje }}%</strong>
    </div>

    <div class="chips">
      <span v-if="libro.genero" class="chip">{{ libro.genero }}</span>
      <span class="chip">{{ libro.prestamos_total }} préstamos</span>
    </div>

    <ul class="motivos">
      <li v-for="m in libro.motivos.filter((x) => !x.startsWith('Disponible'))" :key="m">{{ m }}</li>
    </ul>

    <footer>
      <p v-if="libro.disponibles" class="estado ok">
        <span aria-hidden="true">●</span> Disponible en {{ libro.sedes_disponibles.join(', ') }}
      </p>
      <p v-else class="estado sin">
        <span aria-hidden="true">▲</span> Sin ejemplares libres ahora
      </p>
      <div class="btn-group">
        <RouterLink
          v-if="socioId && libro.disponibles"
          class="btn btn-sm btn-primary"
          :to="{ path: '/prestamos', query: { socio_id: socioId, isbn: libro.isbn } }"
        >
          Pedir préstamo
        </RouterLink>
        <RouterLink v-else-if="socioId" class="btn btn-sm" to="/reservas">Reservar</RouterLink>
        <button type="button" class="btn btn-sm" @click="$emit('similares', libro)">Similares</button>
      </div>
    </footer>
  </article>
</template>

<style scoped>
.tarjeta {
  display: grid; gap: 10px; align-content: start; padding: 14px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow);
}
header { display: flex; gap: 10px; align-items: flex-start; }
.posicion {
  flex: none; display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%;
  background: var(--accent-soft); color: var(--info-ink); font-weight: 650; font-size: 13px;
}
.titulos { display: grid; gap: 2px; min-width: 0; }
h3 { font-size: 14.5px; }
.afinidad { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; }
.medidor { height: 6px; border-radius: 999px; background: var(--grid); overflow: hidden; }
.medidor span { display: block; height: 100%; background: var(--series-1); border-radius: 999px; }
.motivos { margin: 0; padding: 0; list-style: none; display: grid; gap: 3px; font-size: 12.5px; color: var(--ink-2); }
.motivos li::before { content: '✓ '; color: var(--good-ink); font-weight: 600; }
footer { display: grid; gap: 8px; margin-top: auto; padding-top: 8px; border-top: 1px solid var(--grid); }
.estado { margin: 0; font-size: 12.5px; }
.estado.ok { color: var(--good-ink); }
.estado.sin { color: var(--warning-ink); }
.btn { text-decoration: none; }
</style>
