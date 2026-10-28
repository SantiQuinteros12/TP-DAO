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
      <h1>Recomendaciones</h1>
    </header>

    <div class="card buscador">
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
        <h2>{{ resultado.socio }}</h2>
        <template v-if="resultado.personalizado">
          <div>
            <h3>Géneros que lee</h3>
            <ul class="barras-perfil">
              <li v-for="g in resultado.perfil.generos" :key="g.genero">
                <span>{{ g.genero }}</span>
                <span class="pista"><span :style="{ width: `${(g.cantidad / resultado.perfil.generos[0].cantidad) * 100}%` }" /></span>
                <strong>{{ g.cantidad }}</strong>
              </li>
            </ul>
          </div>
          <div>
            <h3>Autores frecuentes</h3>
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
          {{ resultado.personalizado ? 'Te recomendamos' : 'Tendencias en la red' }}
        </h2>
        <p v-if="cargando" class="empty">Calculando…</p>
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
        <h2>Si te gustó…</h2>
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
.buscador { max-width: 640px; }
.contenido { display: grid; gap: 20px; grid-template-columns: minmax(240px, 300px) minmax(0, 1fr); align-items: start; }
.contenido:not(:has(.perfil)) { grid-template-columns: 1fr; }
@media (max-width: 900px) { .contenido { grid-template-columns: 1fr; } }
.perfil { display: grid; gap: 16px; position: sticky; top: 20px; }
.perfil h3 { margin-bottom: 8px; }
.barras-perfil { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; font-size: 12.5px; }
.barras-perfil li { display: grid; grid-template-columns: 80px 1fr 24px; gap: 8px; align-items: center; }
.pista { height: 8px; border-radius: 999px; background: var(--grid); overflow: hidden; }
.pista span { display: block; height: 100%; background: var(--series-1); border-radius: 999px; }
.barras-perfil strong { text-align: right; font-variant-numeric: tabular-nums; }
.leidos { margin: 8px 0 0; padding-left: 18px; color: var(--ink-2); }
details summary { cursor: pointer; color: var(--muted); }
.principal { display: grid; gap: 12px; min-width: 0; }
.seccion { font-size: 16px; }
.grilla { display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.buscar-libro { flex: 1 1 260px; max-width: 420px; }
</style>
