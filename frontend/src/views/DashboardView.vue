<script setup>
/**
 * Dashboard de reportes de gestión:
 *  1. Préstamos activos y material en tránsito por sede
 *  2. Préstamos vencidos y multas acumuladas
 *  3. Libros más solicitados para préstamos inter-sedes
 *  4. Disponibilidad de catálogo por sede
 *  5. Tasa de envíos exitosos e incidencias / tiempo promedio de tránsito
 *  6. Tendencias del período: evolución mensual, composición (tortas) y
 *     comparación contra el período anterior
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import BarChart from '../components/BarChart.vue'
import ColumnChart from '../components/ColumnChart.vue'
import DeltaTile from '../components/DeltaTile.vue'
import DonutChart from '../components/DonutChart.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import StackedBar from '../components/StackedBar.vue'
import StatTile from '../components/StatTile.vue'
import { CalendarDays, CalendarRange } from 'lucide-vue-next'
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
const tendencias = ref(null)

async function cargarPeriodo() {
  const [s, l, t] = await Promise.all([
    ejecutar(() => reportesApi.masSolicitados({ ...periodo, limite: 8 })),
    ejecutar(() => reportesApi.logistica(periodo)),
    ejecutar(() => reportesApi.tendencias(periodo))
  ])
  solicitados.value = s
  logistica.value = l
  tendencias.value = t
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

// --- 6. tendencias ---------------------------------------------------------
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const nombreMes = (m) => `${MESES[Number(m.slice(5, 7)) - 1]} ${m.slice(2, 4)}`
const t = computed(() => tendencias.value ?? {})

const porMes = computed(() =>
  (t.value.prestamos_por_mes ?? []).map((m) => ({
    etiqueta: nombreMes(m.mes),
    valores: { locales: m.locales, interbib: m.interbibliotecarios }
  }))
)
const SERIES_MES = [
  { clave: 'locales', nombre: 'Locales' },
  { clave: 'interbib', nombre: 'Interbibliotecarios' }
]
const porSede = computed(() =>
  (t.value.actividad_por_sede ?? []).map((s) => ({
    etiqueta: s.sede.replace(/^(Sede|Biblioteca) /, ''),
    valores: { solicitados: s.solicitados, provistos: s.provistos }
  }))
)
const SERIES_SEDE = [
  { clave: 'solicitados', nombre: 'Préstamos retirados en la sede' },
  { clave: 'provistos', nombre: 'Ejemplares prestados a otras sedes' }
]
const torta = (lista) => (lista ?? []).map((d) => ({ etiqueta: etiqueta(d.clave), valor: d.cantidad }))
const tortaTipos = computed(() => {
  const a = t.value.comparativa?.actual
  return a
    ? [
        { etiqueta: 'Locales', valor: a.prestamos - a.interbibliotecarios },
        { etiqueta: 'Interbibliotecarios', valor: a.interbibliotecarios }
      ]
    : []
})
const barrasGenero = computed(() =>
  (t.value.prestamos_por_genero ?? []).map((g) => ({ etiqueta: g.genero, valor: g.prestamos })))
const barrasSocios = computed(() =>
  (t.value.socios_mas_activos ?? []).map((s) => ({ etiqueta: s.socio, valor: s.prestamos })))
const tortaDisponibilidad = computed(() => {
  const suma = (c) => disponibilidad.value.reduce((s, d) => s + (d[c] ?? 0), 0)
  return [
    { etiqueta: 'Disponibles', valor: suma('disponibles') },
    { etiqueta: 'Prestados', valor: suma('prestados') },
    { etiqueta: 'Reservados', valor: suma('reservados') },
    { etiqueta: 'En tránsito', valor: suma('en_transito') },
    { etiqueta: 'Dañados', valor: suma('danados') }
  ]
})
const tortaIncidencias = computed(() =>
  (logistica.value?.incidencias_por_tipo ?? []).map((i) => ({ etiqueta: etiqueta(i.tipo), valor: i.cantidad })))
const cmp = computed(() => t.value.comparativa ?? null)

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
        <p>Actividad de préstamos, disponibilidad del catálogo y logística de la red.</p>
      </div>
      <span class="fecha-corte"><CalendarDays :size="16" aria-hidden="true" /> Datos al {{ fecha(isoDia(hoy)) }}</span>
    </header>

    <!-- KPIs -->
    <div v-if="resumen" class="kpis">
      <StatTile etiqueta="Préstamos activos" :valor="numero(resumen.prestamos_activos)" :detalle="`${numero(resumen.reservas_activas)} reservas activas`" />
      <StatTile etiqueta="Préstamos vencidos" :valor="numero(vencidos?.detalle.length ?? 0)" :detalle="`${moneda(vencidos?.total_estimado)} en multas estimadas`" />
      <StatTile etiqueta="Material en tránsito" :valor="numero(activos?.en_transito.length ?? 0)" :detalle="`${numero(activos?.totales.por_despachar ?? 0)} remitos por despachar`" />
      <StatTile etiqueta="Ejemplares en la red" :valor="numero(resumen.ejemplares)" :detalle="`${resumen.titulos} títulos · ${resumen.sedes_activas} sedes activas`" />
    </div>

    <!-- Filtro de período (aplica a 3, 5 y 6) -->
    <div class="card periodo">
      <span class="periodo-titulo"><CalendarRange :size="18" aria-hidden="true" /> Período</span>
      <div class="segmentado" role="group" aria-label="Rangos rápidos">
        <button v-for="r in RANGOS" :key="r.dias" type="button" class="segmento" :class="{ activo: periodo.desde === hace(r.dias) && periodo.hasta === isoDia(hoy) }" @click="elegirRango(r.dias)">{{ r.texto }}</button>
      </div>
      <div class="fechas">
        <label class="fecha-campo"><span>Desde</span><input v-model="periodo.desde" type="date" /></label>
        <label class="fecha-campo"><span>Hasta</span><input v-model="periodo.hasta" type="date" /></label>
      </div>
    </div>

    <!-- 6. Tendencias -->
    <div class="card">
      <div class="card-header">
        <h2 class="seccion"><span class="nro" aria-hidden="true">6</span>Tendencias del período</h2>
        <span v-if="cmp" class="small muted">vs. {{ fecha(cmp.anterior_desde) }} – {{ fecha(cmp.anterior_hasta) }}</span>
      </div>
      <div v-if="cmp" class="kpis">
        <DeltaTile etiqueta="Préstamos solicitados" :actual="cmp.actual.prestamos" :anterior="cmp.anterior.prestamos" />
        <DeltaTile etiqueta="Interbibliotecarios" :actual="cmp.actual.interbibliotecarios" :anterior="cmp.anterior.interbibliotecarios" />
        <DeltaTile etiqueta="Devoluciones" :actual="cmp.actual.devoluciones" :anterior="cmp.anterior.devoluciones" />
        <DeltaTile etiqueta="Reservas" :actual="cmp.actual.reservas" :anterior="cmp.anterior.reservas" />
        <DeltaTile etiqueta="Remitos emitidos" :actual="cmp.actual.remitos" :anterior="cmp.anterior.remitos" />
        <DeltaTile etiqueta="Multas cobradas" :actual="cmp.actual.multas" :anterior="cmp.anterior.multas" :formato="moneda" invertido />
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Préstamos por mes</h2></div>
        <ColumnChart :categorias="porMes" :series="SERIES_MES" unidad="préstamos" />
      </div>
      <div class="card">
        <div class="card-header"><h2>Actividad por sede</h2></div>
        <ColumnChart :categorias="porSede" :series="SERIES_SEDE" unidad="préstamos" />
      </div>
    </div>

    <div class="tortas">
      <div class="card">
        <div class="card-header"><h2>Local vs. interbibliotecario</h2></div>
        <DonutChart :datos="tortaTipos" unidad="préstamos" />
      </div>
      <div class="card">
        <div class="card-header"><h2>Estado de los préstamos</h2></div>
        <DonutChart :datos="torta(t.estados_prestamos)" unidad="préstamos" />
      </div>
      <div class="card">
        <div class="card-header"><h2>Estado físico en devoluciones</h2></div>
        <DonutChart :datos="torta(t.condicion_devoluciones)" unidad="devoluciones" />
      </div>
      <div class="card">
        <div class="card-header"><h2>Remitos por tipo</h2></div>
        <DonutChart :datos="torta(t.remitos_por_tipo)" unidad="remitos" />
      </div>
      <div class="card">
        <div class="card-header"><h2>Ejemplares de la red por estado</h2></div>
        <DonutChart :datos="tortaDisponibilidad" unidad="ejemplares" />
      </div>
      <div class="card">
        <div class="card-header"><h2>Incidencias logísticas por tipo</h2></div>
        <DonutChart :datos="tortaIncidencias" unidad="incidencias" />
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header"><h2>Préstamos por género</h2></div>
        <BarChart v-if="barrasGenero.length" :datos="barrasGenero" unidad="préstamos" />
        <p v-else class="empty">Sin préstamos en el período.</p>
      </div>
      <div class="card">
        <div class="card-header"><h2>Socios más activos</h2></div>
        <BarChart v-if="barrasSocios.length" :datos="barrasSocios" unidad="préstamos" />
        <p v-else class="empty">Sin préstamos en el período.</p>
      </div>
    </div>

    <!-- 1. Préstamos activos y tránsito -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2 class="seccion"><span class="nro" aria-hidden="true">1</span>Préstamos activos y material en tránsito por sede</h2>
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
        <h3 class="subtitulo separado">Material actualmente en tránsito</h3>
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
          <h2 class="seccion"><span class="nro" aria-hidden="true">2</span>Préstamos vencidos y multas acumuladas</h2>
        </div>
        <strong v-if="vencidos" class="total-multas">{{ moneda(vencidos.total_estimado) }}</strong>
      </div>
      <div class="grid-2">
        <div>
          <h3 class="subtitulo">Detalle de vencidos</h3>
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
            <p v-if="!vencidos?.detalle.length" class="empty">No hay préstamos vencidos.</p>
          </div>
        </div>
        <div>
          <h3 class="subtitulo">Por sede</h3>
          <div class="table-wrap con-margen">
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
          <h3 class="subtitulo">Multas registradas en devoluciones (top socios)</h3>
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

    <div class="grid-2">
      <!-- 3. Más solicitados -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="seccion"><span class="nro" aria-hidden="true">3</span>Libros más solicitados entre sedes</h2>
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
            <h2 class="seccion"><span class="nro" aria-hidden="true">4</span>Disponibilidad de catálogo por sede</h2>
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
          <h2 class="seccion"><span class="nro" aria-hidden="true">5</span>Envíos logísticos: éxito, incidencias y tiempos de tránsito</h2>
        </div>
      </div>
      <div class="kpis">
        <StatTile etiqueta="Tasa de envíos exitosos" :valor="pct(ind.tasa_exito)" :detalle="`${ind.recibidos_sin_incidencias ?? 0} de ${(ind.recibidos ?? 0) + (ind.extraviados ?? 0)} finalizados`" />
        <StatTile etiqueta="Tasa de incidencias" :valor="pct(ind.tasa_incidencias)" :detalle="`sobre ${ind.despachados ?? 0} despachados`" />
        <StatTile etiqueta="Tiempo promedio de tránsito" :valor="horas(ind.horas_promedio_transito)" :detalle="`${ind.en_curso ?? 0} en curso · ${ind.extraviados ?? 0} extraviados`" />
        <StatTile etiqueta="Remitos emitidos" :valor="numero(ind.remitos_emitidos)" :detalle="`${ind.cancelados ?? 0} cancelados`" />
      </div>
      <div class="grid-2 separado">
        <div>
          <h3 class="subtitulo">Movimiento por ruta</h3>
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
          <h3 class="subtitulo">Envíos y recepciones por sede</h3>
          <div class="table-wrap con-margen">
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
          <h3 class="subtitulo">Incidencias por tipo</h3>
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
.fecha-corte {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
  border-radius: var(--radius-pill); background: var(--surface); border: 1px solid var(--border);
  font-size: var(--text-sm); color: var(--ink-2);
}
.fecha-corte svg { color: var(--muted); }

.kpis { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
.tortas { display: grid; gap: var(--space-5); grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); }
@media (max-width: 480px) { .tortas { grid-template-columns: 1fr; } }

/* Barra de período: fija al desplazarse */
.periodo {
  display: flex; flex-wrap: wrap; gap: var(--space-3) var(--space-4); align-items: center;
  padding: var(--space-3) var(--space-4);
  position: sticky; top: var(--space-3); z-index: 4;
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
}
@media (max-width: 860px) { .periodo { top: 64px; } }
.periodo-titulo { display: inline-flex; align-items: center; gap: var(--space-2); font-weight: 650; }
.periodo-titulo svg { color: var(--accent); }
.segmentado {
  display: inline-flex; padding: 3px; gap: 2px; border-radius: var(--radius-md);
  background: var(--surface-2); border: 1px solid var(--border); flex-wrap: wrap;
}
.segmento {
  min-height: 30px; padding: 0 var(--space-3); border: 0; border-radius: var(--radius-sm);
  background: transparent; color: var(--ink-2); font: inherit; font-size: var(--text-sm); font-weight: 550;
  cursor: pointer; white-space: nowrap;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.segmento:hover { color: var(--ink); }
.segmento.activo { background: var(--surface); color: var(--accent); box-shadow: var(--shadow); font-weight: 650; }
.segmento:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--focus); }
.fechas { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-left: auto; }
.fecha-campo { display: inline-flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); color: var(--muted); }
.fecha-campo input { width: auto; min-height: 34px; padding: 4px 10px; font-size: var(--text-sm); }
@media (max-width: 640px) {
  .fechas { margin-left: 0; width: 100%; }
  .fecha-campo { flex: 1 1 140px; }
  .fecha-campo input { flex: 1; }
}

/* Encabezados de sección numerados */
.seccion { display: flex; align-items: center; gap: var(--space-3); }
.nro {
  display: inline-grid; place-items: center; flex: none; width: 26px; height: 26px; border-radius: 8px;
  background: var(--accent-soft); color: var(--accent); font-size: var(--text-sm); font-weight: 700;
}
.subtitulo {
  margin-bottom: var(--space-2); font-size: var(--text-xs); font-weight: 650; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.separado { margin-top: var(--space-5); }
.con-margen { margin-bottom: var(--space-5); }

.total-multas {
  font-size: var(--text-2xl); font-weight: 700; letter-spacing: -0.02em; color: var(--critical-ink);
  font-variant-numeric: tabular-nums;
}

.tabla-datos { margin-top: var(--space-4); }
.tabla-datos summary {
  display: inline-flex; align-items: center; gap: 6px; cursor: pointer; margin-bottom: var(--space-2);
  color: var(--accent); font-weight: 550; list-style-position: inside;
}
.tabla-datos summary:hover { color: var(--accent-hover); }
.tabla-datos table { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
</style>
