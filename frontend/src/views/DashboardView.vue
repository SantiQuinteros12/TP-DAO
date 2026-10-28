<script setup>
/**
 * Dashboard de reportes de gestión:
 *  1. Préstamos activos y material en tránsito por sede
 *  2. Préstamos vencidos y multas acumuladas
 *  3. Libros más solicitados para préstamos inter-sedes
 *  4. Disponibilidad de catálogo por sede
 *  5. Tasa de envíos exitosos e incidencias / tiempo promedio de tránsito
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import BarChart from '../components/BarChart.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import StackedBar from '../components/StackedBar.vue'
import StatTile from '../components/StatTile.vue'
import { reportesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { etiqueta, fecha, moneda, numero } from '../composables/formato'

const hoy = new Date()
const isoDia = (d) => d.toISOString().slice(0, 10)
const hace = (dias) => isoDia(new Date(hoy.getTime() - dias * 86400000))
const RANGOS = [
  { dias: 30, texto: 'Últimos 30 días' },
  { dias: 90, texto: 'Últimos 90 días' },
  { dias: 365, texto: 'Último año' }
]
const periodo = reactive({ desde: hace(90), hasta: isoDia(hoy) })

const resumen = ref(null)
const activos = ref(null)
const vencidos = ref(null)
const solicitados = ref(null)
const disponibilidad = ref([])
const logistica = ref(null)

async function cargarPeriodo() {
  const [s, l] = await Promise.all([
    ejecutar(() => reportesApi.masSolicitados({ ...periodo, limite: 8 })),
    ejecutar(() => reportesApi.logistica(periodo))
  ])
  solicitados.value = s
  logistica.value = l
}
watch(periodo, cargarPeriodo)

onMounted(async () => {
  const [r, a, v, d] = await Promise.all([
    ejecutar(() => reportesApi.resumen()),
    ejecutar(() => reportesApi.prestamosActivos()),
    ejecutar(() => reportesApi.vencidos()),
    ejecutar(() => reportesApi.disponibilidadSedes())
  ])
  resumen.value = r
  activos.value = a
  vencidos.value = v
  disponibilidad.value = d ?? []
  cargarPeriodo()
})

const elegirRango = (dias) => Object.assign(periodo, { desde: hace(dias), hasta: isoDia(hoy) })

const barrasSolicitados = computed(() =>
  (solicitados.value?.ranking ?? []).map((l) => ({
    etiqueta: l.titulo,
    valor: l.solicitudes,
    detalle: `pedido desde ${l.sedes_solicitantes} sede(s)`
  }))
)

const SERIES_DISP = [
  { clave: 'disponibles', nombre: 'Disponibles' },
  { clave: 'prestados', nombre: 'Prestados' },
  { clave: 'circulando', nombre: 'Reservados / en tránsito' },
  { clave: 'danados', nombre: 'Dañados' }
]
const filasDisp = computed(() =>
  disponibilidad.value.map((s) => ({
    etiqueta: s.sede + (s.activa ? '' : ' (baja)'),
    total: s.total_ejemplares,
    partes: {
      disponibles: s.disponibles,
      prestados: s.prestados,
      circulando: s.reservados + s.en_transito,
      danados: s.danados
    }
  }))
)

const ind = computed(() => logistica.value?.indicadores ?? {})
const pct = (v) => (v === null || v === undefined ? '—' : `${numero(v, 1)}%`)
const horas = (h) => {
  if (h === null || h === undefined) return '—'
  return h >= 48 ? `${numero(h / 24, 1)} días` : `${numero(h, 1)} h`
}
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Reportes de gestión</h1>
        <p>Estado operativo de la red de bibliotecas al {{ fecha(isoDia(hoy)) }}.</p>
      </div>
    </header>

    <!-- KPIs -->
    <div v-if="resumen" class="kpis">
      <StatTile etiqueta="Préstamos activos" :valor="numero(resumen.prestamos_activos)" :detalle="`${numero(resumen.reservas_activas)} reservas activas`" />
      <StatTile etiqueta="Préstamos vencidos" :valor="numero(vencidos?.detalle.length ?? 0)" :detalle="`${moneda(vencidos?.total_estimado)} en multas estimadas`" />
      <StatTile etiqueta="Material en tránsito" :valor="numero(activos?.en_transito.length ?? 0)" :detalle="`${numero(activos?.totales.por_despachar ?? 0)} remitos por despachar`" />
      <StatTile etiqueta="Ejemplares en la red" :valor="numero(resumen.ejemplares)" :detalle="`${resumen.titulos} títulos · ${resumen.sedes_activas} sedes activas`" />
    </div>

    <!-- 1. Préstamos activos y tránsito -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2>1 · Préstamos activos y material en tránsito por sede</h2>
          <p>Activos según sede de retiro; remitos salientes/entrantes despachados y aún no recibidos.</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sede</th><th class="num">Activos locales</th><th class="num">Activos interbib.</th>
              <th class="num">Pend. de entrega</th><th class="num">Por despachar</th>
              <th class="num">Salientes en viaje</th><th class="num">Entrantes en viaje</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in activos?.por_sede ?? []" :key="s.sede_id">
              <td>{{ s.sede }} <span v-if="!s.activa" class="small muted">(baja)</span></td>
              <td class="num">{{ s.activos_locales }}</td>
              <td class="num">{{ s.activos_interbib }}</td>
              <td class="num">{{ s.pendientes_de_entrega }}</td>
              <td class="num">{{ s.por_despachar }}</td>
              <td class="num">{{ s.salientes_en_transito }}</td>
              <td class="num">{{ s.entrantes_en_transito }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template v-if="activos?.en_transito.length">
        <h3 style="margin: 16px 0 8px">Material actualmente en tránsito</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Remito</th><th>Libro</th><th>Ruta</th><th>Estado</th><th class="num">Tiempo en viaje</th></tr></thead>
            <tbody>
              <tr v-for="r in activos.en_transito" :key="r.id">
                <td><RouterLink :to="`/remitos/${r.id}`" class="mono">R-{{ String(r.id).padStart(6, '0') }}</RouterLink></td>
                <td>{{ r.titulo }} <span class="small muted mono">{{ r.codigo_inventario }}</span></td>
                <td class="small">{{ r.sede_origen }} → {{ r.sede_destino }}</td>
                <td><EstadoBadge :estado="r.estado" /></td>
                <td class="num">{{ horas(r.horas_en_transito) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- 2. Vencidos y multas -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2>2 · Préstamos vencidos y multas acumuladas</h2>
          <p>Multa estimada al día de hoy según la política de cada tipo (lineal para locales, escalonada para interbibliotecarios).</p>
        </div>
        <strong v-if="vencidos" class="total-multas">{{ moneda(vencidos.total_estimado) }}</strong>
      </div>
      <div class="grid-2">
        <div>
          <h3 style="margin-bottom: 8px">Detalle de vencidos</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Socio</th><th>Libro</th><th>Sede</th><th class="num">Atraso</th><th class="num">Multa est.</th></tr></thead>
              <tbody>
                <tr v-for="p in vencidos?.detalle ?? []" :key="p.id">
                  <td>{{ p.socio }}</td>
                  <td>{{ p.titulo }}</td>
                  <td class="small">{{ p.sede_destino }}</td>
                  <td class="num">{{ p.dias_atraso }} d</td>
                  <td class="num">{{ moneda(p.multa_estimada) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="!vencidos?.detalle.length" class="empty">No hay préstamos vencidos. 🎉</p>
          </div>
        </div>
        <div>
          <h3 style="margin-bottom: 8px">Por sede</h3>
          <div class="table-wrap" style="margin-bottom: 16px">
            <table>
              <thead><tr><th>Sede</th><th class="num">Vencidos</th><th class="num">Máx. atraso</th><th class="num">Multa est.</th></tr></thead>
              <tbody>
                <tr v-for="s in vencidos?.por_sede ?? []" :key="s.sede">
                  <td>{{ s.sede }}</td>
                  <td class="num">{{ s.cantidad }}</td>
                  <td class="num">{{ s.max_dias_atraso }} d</td>
                  <td class="num">{{ moneda(s.multa_estimada) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <h3 style="margin-bottom: 8px">Multas registradas en devoluciones (top socios)</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Socio</th><th class="num">Préstamos</th><th class="num">Total</th></tr></thead>
              <tbody>
                <tr v-for="m in vencidos?.multas_registradas ?? []" :key="m.socio_id">
                  <td>{{ m.socio }}</td>
                  <td class="num">{{ m.prestamos_con_multa }}</td>
                  <td class="num">{{ moneda(m.total_multas) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Filtro de período (aplica a 3 y 5) -->
    <div class="card periodo">
      <strong>Período</strong>
      <div class="btn-group">
        <button v-for="r in RANGOS" :key="r.dias" class="btn btn-sm" :class="{ 'btn-primary': periodo.desde === hace(r.dias) && periodo.hasta === isoDia(hoy) }" @click="elegirRango(r.dias)">{{ r.texto }}</button>
      </div>
      <label class="toolbar small">Desde <input v-model="periodo.desde" type="date" /></label>
      <label class="toolbar small">Hasta <input v-model="periodo.hasta" type="date" /></label>
      <span class="small muted">Aplica a los reportes 3 y 5.</span>
    </div>

    <div class="grid-2">
      <!-- 3. Más solicitados -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2>3 · Libros más solicitados entre sedes</h2>
            <p>Solicitudes de préstamo interbibliotecario por título.</p>
          </div>
        </div>
        <BarChart v-if="barrasSolicitados.length" :datos="barrasSolicitados" unidad="solicitudes" />
        <p v-else class="empty">Sin préstamos interbibliotecarios en el período.</p>
        <details v-if="solicitados?.ranking.length" class="tabla-datos">
          <summary class="small">Ver tabla</summary>
          <table>
            <thead><tr><th>Libro</th><th class="num">Solicitudes</th><th class="num">Sedes que lo pidieron</th><th class="num">Sedes proveedoras</th></tr></thead>
            <tbody>
              <tr v-for="l in solicitados.ranking" :key="l.isbn">
                <td>{{ l.titulo }}</td>
                <td class="num">{{ l.solicitudes }}</td>
                <td class="num">{{ l.sedes_solicitantes }}</td>
                <td class="num">{{ l.sedes_proveedoras }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </div>

      <!-- 4. Disponibilidad por sede -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2>4 · Disponibilidad de catálogo por sede</h2>
            <p>Ejemplares propios de cada sede según su estado.</p>
          </div>
        </div>
        <StackedBar :filas="filasDisp" :series="SERIES_DISP" />
        <details class="tabla-datos">
          <summary class="small">Ver tabla</summary>
          <table>
            <thead><tr><th>Sede</th><th class="num">Títulos</th><th class="num">Ejemplares</th><th class="num">% disp.</th><th class="num">Fuera de sede</th></tr></thead>
            <tbody>
              <tr v-for="s in disponibilidad" :key="s.sede_id">
                <td>{{ s.sede }}</td>
                <td class="num">{{ s.titulos }}</td>
                <td class="num">{{ s.total_ejemplares }}</td>
                <td class="num">{{ pct(s.porcentaje_disponible) }}</td>
                <td class="num">{{ s.fuera_de_sede }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </div>
    </div>

    <!-- 5. Logística -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2>5 · Envíos logísticos: éxito, incidencias y tiempos de tránsito</h2>
          <p>Éxito = recibido sin incidencias sobre remitos finalizados (recibidos + extraviados). Tránsito = despacho → recepción.</p>
        </div>
      </div>
      <div class="kpis">
        <StatTile etiqueta="Tasa de envíos exitosos" :valor="pct(ind.tasa_exito)" :detalle="`${ind.recibidos_sin_incidencias ?? 0} de ${(ind.recibidos ?? 0) + (ind.extraviados ?? 0)} finalizados`" />
        <StatTile etiqueta="Tasa de incidencias" :valor="pct(ind.tasa_incidencias)" :detalle="`sobre ${ind.despachados ?? 0} despachados`" />
        <StatTile etiqueta="Tiempo promedio de tránsito" :valor="horas(ind.horas_promedio_transito)" :detalle="`${ind.en_curso ?? 0} en curso · ${ind.extraviados ?? 0} extraviados`" />
        <StatTile etiqueta="Remitos emitidos" :valor="numero(ind.remitos_emitidos)" :detalle="`${ind.cancelados ?? 0} cancelados`" />
      </div>
      <div class="grid-2" style="margin-top: 16px">
        <div>
          <h3 style="margin-bottom: 8px">Movimiento por ruta</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Origen → destino</th><th class="num">Envíos</th><th class="num">Recibidos</th><th class="num">Con incid.</th><th class="num">Prom.</th><th class="num">Mín / máx</th></tr></thead>
              <tbody>
                <tr v-for="r in logistica?.rutas ?? []" :key="r.sede_origen + r.sede_destino">
                  <td class="small">{{ r.sede_origen }} → {{ r.sede_destino }}</td>
                  <td class="num">{{ r.envios }}</td>
                  <td class="num">{{ r.recibidos }}</td>
                  <td class="num">{{ r.con_incidencias }}</td>
                  <td class="num">{{ horas(r.horas_promedio) }}</td>
                  <td class="num small">{{ horas(r.horas_min) }} / {{ horas(r.horas_max) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3 style="margin-bottom: 8px">Envíos y recepciones por sede</h3>
          <div class="table-wrap" style="margin-bottom: 16px">
            <table>
              <thead><tr><th>Sede</th><th class="num">Enviados</th><th class="num">Recibidos</th></tr></thead>
              <tbody>
                <tr v-for="s in logistica?.por_sede ?? []" :key="s.sede">
                  <td>{{ s.sede }}</td>
                  <td class="num">{{ s.enviados }}</td>
                  <td class="num">{{ s.recibidos }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <h3 style="margin-bottom: 8px">Incidencias por tipo</h3>
          <div class="table-wrap">
            <table>
              <tbody>
                <tr v-for="i in logistica?.incidencias_por_tipo ?? []" :key="i.tipo">
                  <td>{{ etiqueta(i.tipo) }}</td>
                  <td class="num">{{ i.cantidad }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="!logistica?.incidencias_por_tipo.length" class="empty">Sin incidencias en el período.</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.kpis { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
.periodo { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; padding: 12px 18px; }
.total-multas { font-size: 22px; font-weight: 600; }
.tabla-datos { margin-top: 14px; }
.tabla-datos summary { cursor: pointer; color: var(--muted); margin-bottom: 8px; }
</style>
