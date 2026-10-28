<script setup>
/**
 * Operación de préstamos: solicitud local / interbibliotecaria, entrega,
 * devolución (con evaluación del estado físico) y cancelación.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { catalogoApi, prestamosApi, sedesApi, sociosApi } from '../services/api'
import { ejecutar, useToast } from '../composables/useToast'
import { etiqueta, fecha, moneda } from '../composables/formato'

const router = useRouter()
const toast = useToast()
const prestamos = ref([])
const sedes = ref([])
const filtros = reactive({ estado: '', tipo: '', sede_id: '', vencidos: false })
const ESTADOS = ['PENDIENTE_ENVIO', 'LISTO_PARA_RETIRO', 'ACTIVO', 'DEVUELTO', 'CANCELADO']

async function cargar() {
  prestamos.value = (await ejecutar(() => prestamosApi.listar(filtros))) ?? []
}
watch(filtros, cargar)

const sedesActivas = computed(() => sedes.value.filter((s) => s.activa))

// --- nueva solicitud -----------------------------------------------------
const solicitud = ref(null)
const socios = ref([])
const libros = ref([])
const disponibilidadLibro = ref([])
const ejemplaresOrigen = ref([])

async function abrirSolicitud() {
  solicitud.value = { socio_id: '', isbn: '', sede_origen_id: '', ejemplar_id: '', sede_destino_id: '' }
  const [s, l] = await Promise.all([
    ejecutar(() => sociosApi.listar({ habilitado: true })),
    ejecutar(() => catalogoApi.listarLibros())
  ])
  socios.value = s ?? []
  libros.value = l ?? []
}

watch(() => solicitud.value?.isbn, async (isbn) => {
  if (!isbn) return
  Object.assign(solicitud.value, { sede_origen_id: '', ejemplar_id: '' })
  disponibilidadLibro.value = (await ejecutar(() => catalogoApi.disponibilidad({ isbn }))) ?? []
})

watch(() => solicitud.value?.sede_origen_id, async (sedeId) => {
  if (!sedeId) return
  const s = solicitud.value
  ejemplaresOrigen.value = ((await ejecutar(() =>
    catalogoApi.listarEjemplares({ isbn: s.isbn, sede_id: sedeId, estado: 'DISPONIBLE' }))) ?? [])
    .filter((e) => e.sede_actual_id === e.sede_id)
  s.ejemplar_id = ejemplaresOrigen.value[0]?.id ?? ''
  if (!s.sede_destino_id) s.sede_destino_id = sedeId
})

const tipoSolicitud = computed(() => {
  const s = solicitud.value
  if (!s?.sede_origen_id || !s?.sede_destino_id) return null
  return Number(s.sede_origen_id) === Number(s.sede_destino_id) ? 'LOCAL' : 'INTERBIBLIOTECARIO'
})

async function confirmarSolicitud() {
  const { socio_id, ejemplar_id, sede_origen_id, sede_destino_id } = solicitud.value
  const prestamo = await ejecutar(
    () => prestamosApi.solicitar({ socio_id, ejemplar_id, sede_origen_id, sede_destino_id }),
    tipoSolicitud.value === 'LOCAL'
      ? 'Préstamo local registrado: el ejemplar fue entregado'
      : 'Préstamo interbibliotecario registrado: se generó el remito de envío'
  )
  if (prestamo) {
    solicitud.value = null
    cargar()
  }
}

// --- acciones sobre préstamos --------------------------------------------
const devolviendo = ref(null)
const devolucion = reactive({ condicion: 'BUENA', observaciones: '' })
const cancelando = ref(null)
const motivo = ref('')

function abrirDevolucion(p) {
  Object.assign(devolucion, { condicion: 'BUENA', observaciones: '' })
  devolviendo.value = p
}

async function entregar(p) {
  if (await ejecutar(() => prestamosApi.entregar(p.id), `Ejemplar entregado a ${p.socio}`)) cargar()
}

async function confirmarDevolucion() {
  const p = devolviendo.value
  const r = await ejecutar(() => prestamosApi.devolver(p.id, devolucion.condicion, devolucion.observaciones))
  if (r) {
    const multa = r.multa ? ` · Multa: ${moneda(r.multa)}` : ''
    const retorno = r.tipo === 'INTERBIBLIOTECARIO' ? ' · Se generó el remito de retorno' : ''
    toast.exito(`Devolución registrada${multa}${retorno}`)
    devolviendo.value = null
    cargar()
  }
}

async function confirmarCancelacion() {
  if (await ejecutar(() => prestamosApi.cancelar(cancelando.value.id, motivo.value), 'Préstamo cancelado')) {
    cancelando.value = null
    motivo.value = ''
    cargar()
  }
}

async function verRemito(p) {
  const detalle = await ejecutar(() => prestamosApi.obtener(p.id))
  const ultimo = detalle?.remitos?.at(-1)
  if (ultimo) router.push(`/remitos/${ultimo.id}`)
}

onMounted(async () => {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
  cargar()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Préstamos</h1>
        <p>Locales (misma sede) o interbibliotecarios (el ejemplar viaja con un remito).</p>
      </div>
      <button class="btn btn-primary" @click="abrirSolicitud">+ Nueva solicitud</button>
    </header>

    <div class="card">
      <div class="toolbar" style="margin-bottom: 12px">
        <select v-model="filtros.estado">
          <option value="">Todos los estados</option>
          <option v-for="e in ESTADOS" :key="e" :value="e">{{ etiqueta(e) }}</option>
        </select>
        <select v-model="filtros.tipo">
          <option value="">Local e interbibliotecario</option>
          <option value="LOCAL">Local</option>
          <option value="INTERBIBLIOTECARIO">Interbibliotecario</option>
        </select>
        <select v-model="filtros.sede_id">
          <option value="">Todas las sedes</option>
          <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <label class="toolbar small"><input v-model="filtros.vencidos" type="checkbox" style="width: auto" /> Sólo vencidos</label>
        <span class="small muted" style="margin-left: auto">{{ prestamos.length }} préstamos</span>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Socio</th><th>Libro</th><th>Tipo</th><th>Origen → Destino</th>
              <th>Vencimiento</th><th>Estado</th><th class="num">Multa</th><th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in prestamos" :key="p.id">
              <td class="muted">{{ p.id }}</td>
              <td>{{ p.socio }}</td>
              <td>{{ p.titulo }}<br /><span class="small muted mono">{{ p.codigo_inventario }}</span></td>
              <td class="small">{{ etiqueta(p.tipo) }}</td>
              <td class="small">
                <template v-if="p.tipo === 'LOCAL'">{{ p.sede_origen }}</template>
                <template v-else>{{ p.sede_origen }} → {{ p.sede_destino }}</template>
              </td>
              <td class="small">
                {{ fecha(p.fecha_vencimiento) }}
                <div v-if="p.vencido" class="small" style="color: var(--critical-ink)">{{ p.dias_atraso }} días de atraso</div>
              </td>
              <td><EstadoBadge :estado="p.vencido ? 'VENCIDO' : p.estado" /></td>
              <td class="num">{{ p.multa_estimada ? moneda(p.multa_estimada) : '—' }}</td>
              <td class="actions">
                <div class="btn-group" style="justify-content: flex-end">
                  <button v-if="p.estado === 'LISTO_PARA_RETIRO'" class="btn btn-sm btn-primary" @click="entregar(p)">Entregar</button>
                  <button v-if="p.estado === 'ACTIVO'" class="btn btn-sm" @click="abrirDevolucion(p)">Devolución</button>
                  <button v-if="p.tipo === 'INTERBIBLIOTECARIO'" class="btn btn-sm" @click="verRemito(p)">Remito</button>
                  <button v-if="['PENDIENTE_ENVIO', 'LISTO_PARA_RETIRO'].includes(p.estado)" class="btn btn-sm btn-danger" @click="cancelando = p">Cancelar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!prestamos.length" class="empty">No hay préstamos para los filtros elegidos.</p>
      </div>
    </div>

    <!-- Nueva solicitud -->
    <ModalDialog v-if="solicitud" titulo="Nueva solicitud de préstamo" ancho="600px" @cerrar="solicitud = null">
      <form class="form" @submit.prevent="confirmarSolicitud">
        <label class="field">
          <span>Socio *</span>
          <select v-model="solicitud.socio_id" required>
            <option value="" disabled>Elegí un socio habilitado…</option>
            <option v-for="s in socios" :key="s.id" :value="s.id">{{ s.nombre_completo }} — DNI {{ s.documento }}</option>
          </select>
        </label>
        <label class="field">
          <span>Libro *</span>
          <select v-model="solicitud.isbn" required>
            <option value="" disabled>Elegí un libro…</option>
            <option v-for="l in libros" :key="l.isbn" :value="l.isbn">{{ l.titulo }} — {{ l.autor }}</option>
          </select>
        </label>
        <div class="form-row">
          <label class="field">
            <span>Sede origen *</span>
            <select v-model="solicitud.sede_origen_id" required :disabled="!solicitud.isbn">
              <option value="" disabled>Sede propietaria…</option>
              <option v-for="d in disponibilidadLibro" :key="d.sede_id" :value="d.sede_id" :disabled="!d.disponibles || !d.sede_activa">
                {{ d.sede }} ({{ d.sede_activa ? `${d.disponibles} disp.` : 'baja' }})
              </option>
            </select>
          </label>
          <label class="field">
            <span>Sede destino (retiro) *</span>
            <select v-model="solicitud.sede_destino_id" required>
              <option value="" disabled>¿Dónde retira el socio?</option>
              <option v-for="s in sedesActivas" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </label>
        </div>
        <label v-if="ejemplaresOrigen.length" class="field">
          <span>Ejemplar</span>
          <select v-model="solicitud.ejemplar_id" required>
            <option v-for="e in ejemplaresOrigen" :key="e.id" :value="e.id">{{ e.codigo_inventario }} ({{ etiqueta(e.condicion) }})</option>
          </select>
        </label>
        <p v-if="solicitud.isbn && disponibilidadLibro.length && !disponibilidadLibro.some((d) => d.disponibles)" class="alert warning">
          No hay ejemplares disponibles de este libro en la red. Podés registrar una reserva.
        </p>
        <p v-if="tipoSolicitud === 'LOCAL'" class="alert">Préstamo <strong>local</strong>: se entrega en el momento, con 14 días de plazo.</p>
        <p v-if="tipoSolicitud === 'INTERBIBLIOTECARIO'" class="alert">
          Préstamo <strong>interbibliotecario</strong>: se generará un remito de envío. El plazo de 21 días corre desde que el socio lo retira.
        </p>
        <div class="form-actions">
          <button type="button" class="btn" @click="solicitud = null">Cancelar</button>
          <button class="btn btn-primary" :disabled="!solicitud.ejemplar_id">Registrar préstamo</button>
        </div>
      </form>
    </ModalDialog>

    <!-- Devolución -->
    <ModalDialog v-if="devolviendo" titulo="Registrar devolución" @cerrar="devolviendo = null">
      <form class="form" @submit.prevent="confirmarDevolucion">
        <p>
          <strong>{{ devolviendo.titulo }}</strong> ({{ devolviendo.codigo_inventario }})<br />
          <span class="muted">{{ devolviendo.socio }} · venció el {{ fecha(devolviendo.fecha_vencimiento) }}</span>
        </p>
        <p v-if="devolviendo.vencido" class="alert warning">
          {{ devolviendo.dias_atraso }} días de atraso · multa por atraso estimada {{ moneda(devolviendo.multa_estimada) }}
          (política {{ devolviendo.politica_multa }}).
        </p>
        <fieldset class="field condiciones">
          <span>Estado físico del material *</span>
          <label v-for="c in ['BUENA', 'DETERIORADA', 'DANADA']" :key="c" class="opcion">
            <input v-model="devolucion.condicion" type="radio" :value="c" style="width: auto" />
            {{ etiqueta(c) }}
            <small class="muted">{{ { BUENA: 'sin recargo', DETERIORADA: '+ $2.000', DANADA: '+ $15.000, queda fuera de circulación' }[c] }}</small>
          </label>
        </fieldset>
        <label class="field"><span>Observaciones</span><textarea v-model="devolucion.observaciones" rows="2" /></label>
        <p v-if="devolviendo.tipo === 'INTERBIBLIOTECARIO'" class="alert">
          Se generará un remito de retorno hacia {{ devolviendo.sede_origen }}.
        </p>
        <div class="form-actions">
          <button type="button" class="btn" @click="devolviendo = null">Cancelar</button>
          <button class="btn btn-primary">Registrar devolución</button>
        </div>
      </form>
    </ModalDialog>

    <!-- Cancelación -->
    <ModalDialog v-if="cancelando" titulo="Cancelar préstamo" @cerrar="cancelando = null">
      <form class="form" @submit.prevent="confirmarCancelacion">
        <p>Préstamo #{{ cancelando.id }} — {{ cancelando.titulo }} para {{ cancelando.socio }}.</p>
        <label class="field"><span>Motivo *</span><input v-model="motivo" required minlength="3" /></label>
        <div class="form-actions">
          <button type="button" class="btn" @click="cancelando = null">Volver</button>
          <button class="btn btn-primary">Cancelar préstamo</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>

<style scoped>
.condiciones { border: 0; padding: 0; margin: 0; }
.opcion {
  display: flex; gap: 8px; align-items: center; padding: 8px 10px;
  border: 1px solid var(--grid); border-radius: 8px; cursor: pointer;
}
.opcion small { margin-left: auto; }
</style>
