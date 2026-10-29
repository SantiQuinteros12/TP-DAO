<script setup>
/**
 * Recomendaciones de lectura.
 *  - Para un socio: según sus géneros y autores, lo que leyeron socios con
 *    gustos parecidos, la popularidad reciente y la disponibilidad.
 *  - Sin socio: lo más pedido en la red.
 *  - "Si te gustó…": libros similares a uno elegido.
 */
import { onMounted, ref } from 'vue'
import TarjetaLibro from '../components/TarjetaLibro.vue'
import TypeAhead from '../components/TypeAhead.vue'
import { buscar, recomendacionesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { BookHeart, LoaderCircle, Sparkles, TrendingUp, UserRound } from 'lucide-vue-next'

const socioId = ref(null)
const resultado = ref(null)
const cargando = ref(false)

const libroBase = ref(null)
const libroIsbn = ref(null)
const similares = ref(null)

async function cargar(socio = null) {
  cargando.value = true
  resultado.value = (await ejecutar(() => recomendacionesApi.paraSocio(socio?.id, 9))) ?? null
  cargando.value = false
}

async function verSimilares(libro) {
  libroBase.value = libro
  similares.value = libro ? ((await ejecutar(() => recomendacionesApi.similares(libro.isbn))) ?? null) : null
  if (libro) document.getElementById('similares')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => cargar())
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Recomendaciones</h1>
        <p>Sugerencias de lectura según el historial de cada socio, sus autores y géneros preferidos.</p>
      </div>
    </header>

    <div class="card buscador">
      <span class="buscador-icono" aria-hidden="true"><UserRound :size="20" /></span>
      <label class="field">
        <span>Recomendar para el socio</span>
        <TypeAhead
          v-model="socioId"
          :buscar="buscar.socios"
          :texto-de="(s) => s.nombre_completo"
          :detalle-de="(s) => `DNI ${s.documento}`"
          placeholder="Buscá un socio por apellido, nombre o DNI… (vacío = tendencias de la red)"
          @elegir="cargar"
        />
      </label>
    </div>

    <div v-if="resultado" class="contenido">
      <!-- Perfil del lector -->
      <aside v-if="resultado.socio" class="card perfil">
        <div class="perfil-titulo">
          <span class="buscador-icono" aria-hidden="true"><UserRound :size="18" /></span>
          <h2>{{ resultado.socio }}</h2>
        </div>
        <template v-if="resultado.personalizado">
          <div>
            <h3 class="subtitulo">Géneros que lee</h3>
            <ul class="barras-perfil">
              <li v-for="g in resultado.perfil.generos" :key="g.genero">
                <span>{{ g.genero }}</span>
                <span class="pista"><span :style="{ width: `${(g.cantidad / resultado.perfil.generos[0].cantidad) * 100}%` }" /></span>
                <strong>{{ g.cantidad }}</strong>
              </li>
            </ul>
          </div>
          <div>
            <h3 class="subtitulo">Autores frecuentes</h3>
            <div class="chips">
              <span v-for="a in resultado.perfil.autores" :key="a.autor" class="chip">{{ a.autor }} <strong>{{ a.cantidad }}</strong></span>
            </div>
          </div>
          <details>
            <summary class="small">Libros leídos ({{ resultado.perfil.libros_leidos.length }})</summary>
            <ul class="leidos small">
              <li v-for="t in resultado.perfil.libros_leidos" :key="t">{{ t }}</li>
            </ul>
          </details>
        </template>
        <p v-else class="alert">Todavía no pidió libros: se muestran las tendencias de la red.</p>
      </aside>

      <div class="principal">
        <h2 class="seccion">
          <component :is="resultado.personalizado ? Sparkles : TrendingUp" :size="20" aria-hidden="true" />
          {{ resultado.personalizado ? 'Te recomendamos' : 'Tendencias en la red' }}
        </h2>
        <p v-if="cargando" class="calculando"><LoaderCircle class="girando" :size="18" aria-hidden="true" /> Calculando…</p>
        <div v-else class="grilla">
          <TarjetaLibro
            v-for="(l, i) in resultado.recomendaciones"
            :key="l.isbn"
            :libro="l"
            :posicion="i + 1"
            :socio-id="socioId"
            @similares="verSimilares"
          />
        </div>
        <p v-if="!cargando && !resultado.recomendaciones.length" class="empty">No hay libros nuevos para recomendar.</p>
      </div>
    </div>

    <!-- Si te gustó… -->
    <div id="similares" class="card">
      <div class="card-header">
        <h2 class="seccion"><BookHeart :size="20" aria-hidden="true" /> Si te gustó…</h2>
        <div class="buscar-libro">
          <TypeAhead
            v-model="libroIsbn"
            :seleccionado="libroBase"
            :buscar="buscar.libros"
            :texto-de="(l) => l.titulo"
            :detalle-de="(l) => l.autor"
            :clave-de="(l) => l.isbn"
            placeholder="Elegí un libro…"
            @elegir="verSimilares"
          />
        </div>
      </div>
      <div v-if="similares" class="grilla">
        <TarjetaLibro
          v-for="(l, i) in similares.recomendaciones"
          :key="l.isbn"
          :libro="l"
          :posicion="i + 1"
          :socio-id="socioId"
          @similares="verSimilares"
        />
      </div>
      <p v-else class="empty">Elegí un libro para ver títulos parecidos y lo que leyeron sus lectores.</p>
    </div>
  </section>
</template>

<style scoped>
.buscador { display: flex; align-items: flex-end; gap: var(--space-3); max-width: 680px; }
.buscador .field { flex: 1; }
.buscador-icono {
  display: grid; place-items: center; flex: none; width: 40px; height: 40px; border-radius: 10px;
  background: var(--accent-soft); color: var(--accent);
}
.contenido { display: grid; gap: var(--space-5); grid-template-columns: minmax(240px, 300px) minmax(0, 1fr); align-items: start; }
.contenido:not(:has(.perfil)) { grid-template-columns: 1fr; }
@media (max-width: 900px) { .contenido { grid-template-columns: 1fr; } }

/* Perfil del lector */
.perfil { display: grid; gap: var(--space-5); position: sticky; top: var(--space-5); }
.perfil-titulo { display: flex; align-items: center; gap: var(--space-3); }
.perfil-titulo .buscador-icono { width: 36px; height: 36px; }
.subtitulo {
  margin-bottom: var(--space-2); font-size: var(--text-xs); font-weight: 650; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.barras-perfil { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); font-size: var(--text-sm); }
.barras-perfil li { display: grid; grid-template-columns: 90px 1fr 28px; gap: var(--space-2); align-items: center; color: var(--ink-2); }
.pista { height: 8px; border-radius: var(--radius-pill); background: var(--grid); overflow: hidden; }
.pista span { display: block; height: 100%; background: var(--series-1); border-radius: var(--radius-pill); transition: width 300ms var(--ease); }
.barras-perfil strong { text-align: right; color: var(--ink); font-variant-numeric: tabular-nums; }
.leidos { margin: var(--space-2) 0 0; padding-left: 18px; color: var(--ink-2); display: grid; gap: 2px; }
details summary { cursor: pointer; color: var(--accent); font-weight: 550; }
details summary:hover { color: var(--accent-hover); }

/* Recomendaciones */
.principal { display: grid; gap: var(--space-4); min-width: 0; }
.seccion { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xl); }
.seccion svg { color: var(--accent); }
.calculando { display: flex; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-8); color: var(--muted); }
.girando { animation: girar 0.8s linear infinite; }
.grilla { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }
.buscar-libro { flex: 1 1 260px; max-width: 420px; }
#similares .grilla { margin-top: var(--space-2); }

@keyframes girar { to { transform: rotate(360deg); } }
@media (max-width: 520px) { .buscador .buscador-icono { display: none; } }
</style>
