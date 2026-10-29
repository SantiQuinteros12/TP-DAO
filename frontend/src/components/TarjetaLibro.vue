<script setup>
/**
 * Tarjeta de un libro recomendado: afinidad, motivos y disponibilidad.
 */
import { BookOpen, Bookmark, Check, CircleCheck, Clock, Library } from 'lucide-vue-next'

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
      <span class="chip"><BookOpen :size="12" aria-hidden="true" /> {{ libro.prestamos_total }} préstamos</span>
    </div>

    <ul class="motivos">
      <li v-for="m in libro.motivos.filter((x) => !x.startsWith('Disponible'))" :key="m"><Check :size="14" aria-hidden="true" /> {{ m }}</li>
    </ul>

    <footer>
      <p v-if="libro.disponibles" class="estado ok">
        <CircleCheck :size="15" aria-hidden="true" /> Disponible en {{ libro.sedes_disponibles.join(', ') }}
      </p>
      <p v-else class="estado sin">
        <Clock :size="15" aria-hidden="true" /> Sin ejemplares libres ahora
      </p>
      <div class="btn-group">
        <RouterLink
          v-if="socioId && libro.disponibles"
          class="btn btn-sm btn-primary"
          :to="{ path: '/prestamos', query: { socio_id: socioId, isbn: libro.isbn } }"
        >
          <BookOpen aria-hidden="true" /> Pedir préstamo
        </RouterLink>
        <RouterLink v-else-if="socioId" class="btn btn-sm" to="/reservas"><Bookmark aria-hidden="true" /> Reservar</RouterLink>
        <button type="button" class="btn btn-sm btn-ghost" @click="$emit('similares', libro)"><Library aria-hidden="true" /> Similares</button>
      </div>
    </footer>
  </article>
</template>

<style scoped>
.tarjeta {
  display: grid; gap: var(--space-3); align-content: start; padding: var(--space-4);
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease), transform var(--dur) var(--ease);
}
.tarjeta:hover { border-color: var(--accent-soft-2); box-shadow: var(--shadow-lg); transform: translateY(-2px); }
header { display: flex; gap: var(--space-3); align-items: flex-start; }
.posicion {
  flex: none; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%;
  background: var(--accent); color: var(--accent-ink); font-weight: 700; font-size: var(--text-sm);
}
.titulos { display: grid; gap: 2px; min-width: 0; }
h3 { font-size: 15.5px; line-height: 1.3; }
.afinidad { display: grid; grid-template-columns: auto 1fr auto; gap: var(--space-2); align-items: center; }
.medidor { height: 6px; border-radius: var(--radius-pill); background: var(--grid); overflow: hidden; }
.medidor span { display: block; height: 100%; background: var(--series-1); border-radius: var(--radius-pill); transition: width 300ms var(--ease); }
.afinidad strong { color: var(--accent); font-variant-numeric: tabular-nums; }
.chips .chip { gap: 4px; }
.motivos { margin: 0; padding: 0; list-style: none; display: grid; gap: 4px; font-size: var(--text-sm); color: var(--ink-2); }
.motivos li { display: flex; align-items: flex-start; gap: 6px; }
.motivos svg { flex: none; margin-top: 2px; color: var(--good-ink); }
footer { display: grid; gap: var(--space-3); margin-top: auto; padding-top: var(--space-3); border-top: 1px solid var(--border); }
.estado { display: flex; align-items: flex-start; gap: 6px; margin: 0; font-size: var(--text-sm); font-weight: 550; }
.estado svg { flex: none; margin-top: 2px; }
.estado.ok { color: var(--good-ink); }
.estado.sin { color: var(--warning-ink); }
.btn { text-decoration: none; }
</style>
