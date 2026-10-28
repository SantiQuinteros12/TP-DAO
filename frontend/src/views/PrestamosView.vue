<script setup>
/**
 * Operación de préstamos: solicitud local / interbibliotecaria, entrega,
 * devolución (con evaluación del estado físico) y cancelación.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CampoForm from '../components/CampoForm.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import TypeAhead from '../components/TypeAhead.vue'
import { buscar, catalogoApi, prestamosApi, sedesApi, sociosApi } from '../services/api'
import { ejecutar, useToast } from '../composables/useToast'
import { etiqueta, fecha, moneda } from '../composables/formato'

const route = useRoute()
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
const elegibilidad = ref(null)
const verificando = ref(false)
const disponibilidadLibro = ref([])
const ejemplaresOrigen = ref([])

function abrirSolicitud(precarga = {}) {
  solicitud.value = {
    socio_id: precarga.socio?.id ?? null,
    socio: precarga.socio ?? null,
    isbn: precarga.libro?.isbn ?? null,
    libro: precarga.libro ?? null,
    sede_origen_id: '',
    ejemplar_id: '',
    sede_destino_id: ''
  }
  elegibilidad.value = null
  disponibilidadLibro.value = []
  ejemplaresOrigen.value = []
  if (precarga.socio) verificarSocio(precarga.socio)
  if (precarga.libro) cargarDisponibilidad(precarga.libro.isbn)
}

/** Validación anticipada: apenas se elige el socio se informa si puede pedir. */
async function verificarSocio(socio) {
  elegibilidad.value = null
  if (!socio) return
  verificando.value = true
  elegibilidad.value = (await ejecutar(() => prestamosApi.elegibilidad(socio.id))) ?? null
  verificando.value = false
}

async function cargarDisponibilidad(isbn) {
  Object.assign(solicitud.value, { sede_origen_id: '', ejemplar_id: '' })
  ejemplaresOrigen.value = []
  disponibilidadLibro.value = isbn ? ((await ejecutar(() => catalogoApi.disponibilidad({ isbn }))) ?? []) : []
}

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

const sinStock = computed(() =>
  !!solicitud.value?.isbn && !disponibilidadLibro.value.some((d) => d.disponibles && d.sede_activa))
const socioBloqueado = computed(() => !!elegibilidad.value && !elegibilidad.value.puede_solicitar)

/** Primer dato que falta: se muestra junto al botón en lugar de esperar al envío. */
const faltante = computed(() => {
  const s = solicitud.value
  if (!s) return ''
  if (!s.socio_id) return 'Elegí el socio'
  if (verificando.value) return 'Verificando al socio…'
  if (socioBloqueado.value) return 'El socio no puede solicitar préstamos'
  if (!s.isbn) return 'Elegí el libro'
  if (sinStock.value) return 'No hay ejemplares disponibles'
  if (!s.sede_origen_id) return 'Elegí la sede origen'
  if (!s.sede_destino_id) return 'Elegí la sede de retiro'
  if (!s.ejemplar_id) return 'No hay ejemplar disponible en esa sede'
  return ''
})

async function confirmarSolicitud() {
  if (faltante.value) return
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
const motivoInvalido = computed(() => motivo.value.trim().length < 3)

function abrirDevolucion(p) {
  Object.assign(devolucion, { condicion: 'BUENA', observaciones: '' })
  devolviendo.value = p
}

function abrirCancelacion(p) {
  motivo.value = ''
  cancelando.value = p
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
  if (motivoInvalido.value) return
  if (await ejecutar(() => prestamosApi.cancelar(cancelando.value.id, motivo.value.trim()), 'Préstamo cancelado')) {
    cancelando.value = null
    cargar()
  }
}

async function verRemito(p) {
  const detalle = await ejecutar(() => prestamosApi.obtener(p.id))
  const ultimo = detalle?.remitos?.at(-1)
  if (ultimo) router.push({ path: `/remitos/${ultimo.id}`, query: { volver: '/prestamos' } })
}

onMounted(async () => {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
  cargar()
  // Precarga desde Recomendaciones: /prestamos?socio_id=..&isbn=..
  const { socio_id: socioId, isbn } = route.query
  if (socioId || isbn) {
    const [socio, libros] = await Promise.all([
      socioId ? ejecutar(() => sociosApi.obtener(socioId)) : null,
      isbn ? ejecutar(() => catalogoApi.listarLibros(isbn)) : null
    ])
    abrirSolicitud({ socio, libro: libros?.find((l) => l.isbn === isbn) })
    router.replace({ query: {} })
  }
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <h1>Préstamos</h1>
      <button class="btn btn-primary" @click="abrirSolicitud()">+ Nueva solicitud</button>
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
                  <button v-if="['PENDIENTE_ENVIO', 'LISTO_PARA_RETIRO'].includes(p.estado)" class="btn btn-sm btn-danger" @click="abrirCancelacion(p)">Cancelar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!prestamos.length" class="empty">No hay préstamos para los filtros elegidos.</p>
      </div>
    </div>

    <!-- Nueva solicitud -->
    <ModalDialog v-if="solicitud" titulo="Nueva solicitud de préstamo" ancho="620px" @cerrar="solicitud = null">
      <form class="form" novalidate @submit.prevent="confirmarSolicitud">
        <CampoForm etiqueta="Socio" requerido>
          <TypeAhead
            v-model="solicitud.socio_id"
            :seleccionado="solicitud.socio"
            :buscar="buscar.socios"
            :texto-de="(s) => s.nombre_completo"
            :detalle-de="(s) => `DNI ${s.documento}${s.habilitado ? '' : ' · inhabilitado'}`"
            placeholder="Buscá por apellido, nombre o DNI…"
            @elegir="verificarSocio"
          />
        </CampoForm>

        <!-- Resultado de la validación anticipada del socio -->
        <p v-if="verificando" class="alert">Verificando requisitos del socio…</p>
        <div v-else-if="socioBloqueado" class="alert error" role="alert">
          <strong>{{ elegibilidad.socio }} no puede solicitar un préstamo:</strong>
          <ul><li v-for="m in elegibilidad.impedimentos" :key="m">{{ m }}</li></ul>
        </div>
        <p v-else-if="elegibilidad" class="alert ok">
          ✓ Habilitado · {{ elegibilidad.prestamos_abiertos }} de {{ elegibilidad.maximo_prestamos }} préstamos abiertos
        </p>

        <fieldset class="resto" :disabled="!elegibilidad || socioBloqueado">
          <CampoForm etiqueta="Libro" requerido>
            <TypeAhead
              v-model="solicitud.isbn"
              :seleccionado="solicitud.libro"
              :buscar="buscar.libros"
              :texto-de="(l) => l.titulo"
              :detalle-de="(l) => `${l.autor} · ISBN ${l.isbn}`"
              :clave-de="(l) => l.isbn"
              :deshabilitado="!elegibilidad || socioBloqueado"
              placeholder="Buscá por título, autor o ISBN…"
              @elegir="(l) => cargarDisponibilidad(l?.isbn)"
            />
          </CampoForm>
          <p v-if="sinStock && disponibilidadLibro.length" class="alert warning">
            No hay ejemplares disponibles de este libro en la red.
            <RouterLink to="/reservas">Registrar una reserva</RouterLink>
          </p>
          <p v-else-if="sinStock" class="alert warning">Este libro no tiene ejemplares cargados.</p>
          <div class="form-row">
            <CampoForm etiqueta="Sede origen" requerido>
              <select v-model="solicitud.sede_origen_id" :disabled="!solicitud.isbn || sinStock">
                <option value="" disabled>Sede propietaria…</option>
                <option v-for="d in disponibilidadLibro" :key="d.sede_id" :value="d.sede_id" :disabled="!d.disponibles || !d.sede_activa">
                  {{ d.sede }} ({{ d.sede_activa ? `${d.disponibles} disp.` : 'baja' }})
                </option>
              </select>
            </CampoForm>
            <CampoForm etiqueta="Sede de retiro" requerido>
              <select v-model="solicitud.sede_destino_id">
                <option value="" disabled>¿Dónde retira el socio?</option>
                <option v-for="s in sedesActivas" :key="s.id" :value="s.id">{{ s.nombre }}</option>
              </select>
            </CampoForm>
          </div>
          <label v-if="ejemplaresOrigen.length > 1" class="field">
            <span>Ejemplar</span>
            <select v-model="solicitud.ejemplar_id">
              <option v-for="e in ejemplaresOrigen" :key="e.id" :value="e.id">{{ e.codigo_inventario }} ({{ etiqueta(e.condicion) }})</option>
            </select>
          </label>
        </fieldset>

        <p v-if="tipoSolicitud === 'LOCAL'" class="alert">Préstamo <strong>local</strong>: se entrega en el momento, con 14 días de plazo.</p>
        <p v-if="tipoSolicitud === 'INTERBIBLIOTECARIO'" class="alert">
          Préstamo <strong>interbibliotecario</strong>: se generará un remito de envío. El plazo de 21 días corre desde que el socio lo retira.
        </p>
        <div class="form-actions">
          <span v-if="faltante" class="small muted faltante">{{ faltante }}</span>
          <button type="button" class="btn" @click="solicitud = null">Cancelar</button>
          <button class="btn btn-primary" :disabled="!!faltante">Registrar préstamo</button>
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
          <span>Estado físico del material <b class="req">*</b></span>
          <label v-for="c in ['BUENA', 'DETERIORADA', 'DANADA']" :key="c" class="opcion">
            <input v-model="devolucion.condicion" type="radio" :value="c" style="width: auto" />
            {{ etiqueta(c) }}
            <small class="muted">{{ { BUENA: 'sin recargo', DETERIORADA: '+ $2.000', DANADA: '+ $15.000, queda fuera de circulación' }[c] }}</small>
          </label>
        </fieldset>
        <label class="field"><span>Observaciones</span><textarea v-model="devolucion.observaciones" rows="2" maxlength="300" /></label>
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
      <form class="form" novalidate @submit.prevent="confirmarCancelacion">
        <p>Préstamo #{{ cancelando.id }} — {{ cancelando.titulo }} para {{ cancelando.socio }}.</p>
        <CampoForm etiqueta="Motivo" requerido :error="motivo && motivoInvalido ? 'Mínimo 3 caracteres' : ''">
          <input v-model="motivo" maxlength="200" />
        </CampoForm>
        <div class="form-actions">
          <button type="button" class="btn" @click="cancelando = null">Volver</button>
          <button class="btn btn-primary" :disabled="motivoInvalido">Cancelar préstamo</button>
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
.resto { display: grid; gap: 12px; border: 0; padding: 0; margin: 0; min-width: 0; }
.resto:disabled { opacity: 0.55; }
.faltante { margin-right: auto; align-self: center; }
</style>
