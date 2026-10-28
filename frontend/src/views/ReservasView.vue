<script setup>
/**
 * Gestión de reservas: cola FIFO por libro y sede. Cuando un ejemplar se
 * libera, el backend lo asigna automáticamente a la reserva más antigua.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import CampoForm from '../components/CampoForm.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import TypeAhead from '../components/TypeAhead.vue'
import { buscar, catalogoApi, reservasApi, sedesApi } from '../services/api'
import { ejecutar, useToast } from '../composables/useToast'
import { etiqueta, fecha } from '../composables/formato'

const toast = useToast()
const reservas = ref([])
const sedes = ref([])
const filtros = reactive({ estado: '', sede_id: '' })
const ESTADOS = ['PENDIENTE', 'DISPONIBLE', 'CUMPLIDA', 'CANCELADA', 'VENCIDA']

const nueva = ref(null)
const socioElegido = ref(null)
const sedesDelLibro = ref([])

async function cargar() {
  reservas.value = (await ejecutar(() => reservasApi.listar(filtros))) ?? []
}
watch(filtros, cargar)

function abrirNueva() {
  nueva.value = { socio_id: null, isbn: null, sede_id: '' }
  socioElegido.value = null
  sedesDelLibro.value = []
}

/** Sólo se puede reservar en sedes que poseen ejemplares del libro. */
async function elegirLibro(libro) {
  nueva.value.sede_id = ''
  sedesDelLibro.value = libro
    ? ((await ejecutar(() => catalogoApi.disponibilidad({ isbn: libro.isbn }))) ?? []).filter((d) => d.sede_activa)
    : []
}

const faltante = computed(() => {
  const n = nueva.value
  if (!n) return ''
  if (!n.socio_id) return 'Elegí el socio'
  if (socioElegido.value && !socioElegido.value.habilitado) return 'El socio está inhabilitado'
  if (!n.isbn) return 'Elegí el libro'
  if (!sedesDelLibro.value.length) return 'Ninguna sede activa tiene este libro'
  if (!n.sede_id) return 'Elegí la sede de retiro'
  return ''
})

async function crear() {
  if (faltante.value) return
  const r = await ejecutar(() => reservasApi.crear(nueva.value))
  if (r) {
    toast.exito(
      r.estado === 'DISPONIBLE'
        ? 'Había un ejemplar disponible: la reserva ya está lista para retirar'
        : 'Reserva registrada en la cola de espera'
    )
    nueva.value = null
    cargar()
  }
}

async function accion(fn, mensaje) {
  if (await ejecutar(fn, mensaje)) cargar()
}

async function procesarVencimientos() {
  const r = await ejecutar(() => reservasApi.procesarVencimientos())
  if (r) {
    toast.exito(`${r.reservas_vencidas} reserva(s) vencida(s) procesadas`)
    cargar()
  }
}

onMounted(async () => {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
  cargar()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <h1>Reservas</h1>
      <div class="btn-group">
        <button class="btn" @click="procesarVencimientos">Procesar vencimientos</button>
        <button class="btn btn-primary" @click="abrirNueva">+ Nueva reserva</button>
      </div>
    </header>

    <div class="card">
      <div class="toolbar" style="margin-bottom: 12px">
        <select v-model="filtros.estado">
          <option value="">Todos los estados</option>
          <option v-for="e in ESTADOS" :key="e" :value="e">{{ etiqueta(e) }}</option>
        </select>
        <select v-model="filtros.sede_id">
          <option value="">Todas las sedes</option>
          <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Socio</th><th>Libro</th><th>Sede de retiro</th><th>Reservada</th><th>Ejemplar asignado</th><th>Estado</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="r in reservas" :key="r.id">
              <td class="muted">{{ r.id }}</td>
              <td>{{ r.socio }}</td>
              <td>{{ r.titulo }}</td>
              <td>{{ r.sede }}</td>
              <td class="small">{{ fecha(r.fecha_reserva) }}</td>
              <td class="small">
                <span v-if="r.codigo_inventario" class="mono">{{ r.codigo_inventario }}</span>
                <div v-if="r.fecha_limite_retiro" class="muted">Retirar hasta {{ fecha(r.fecha_limite_retiro) }}</div>
              </td>
              <td><EstadoBadge :estado="r.estado" /></td>
              <td class="actions">
                <div class="btn-group" style="justify-content: flex-end">
                  <button v-if="r.estado === 'DISPONIBLE'" class="btn btn-sm btn-primary" @click="accion(() => reservasApi.concretar(r.id), 'Reserva concretada: préstamo registrado')">Concretar préstamo</button>
                  <button v-if="['PENDIENTE', 'DISPONIBLE'].includes(r.estado)" class="btn btn-sm btn-danger" @click="accion(() => reservasApi.cancelar(r.id), 'Reserva cancelada')">Cancelar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!reservas.length" class="empty">No hay reservas.</p>
      </div>
    </div>

    <ModalDialog v-if="nueva" titulo="Nueva reserva" ancho="560px" @cerrar="nueva = null">
      <form class="form" novalidate @submit.prevent="crear">
        <CampoForm etiqueta="Socio" requerido>
          <TypeAhead
            v-model="nueva.socio_id"
            :buscar="buscar.socios"
            :texto-de="(s) => s.nombre_completo"
            :detalle-de="(s) => `DNI ${s.documento}${s.habilitado ? '' : ' · inhabilitado'}`"
            placeholder="Buscá por apellido, nombre o DNI…"
            @elegir="(s) => (socioElegido = s)"
          />
        </CampoForm>
        <div v-if="socioElegido && !socioElegido.habilitado" class="alert error" role="alert">
          <strong>{{ socioElegido.nombre_completo }} está inhabilitado</strong> y no puede reservar
          ({{ socioElegido.motivo_inhabilitacion }}).
        </div>
        <CampoForm etiqueta="Libro" requerido>
          <TypeAhead
            v-model="nueva.isbn"
            :buscar="buscar.libros"
            :texto-de="(l) => l.titulo"
            :detalle-de="(l) => `${l.autor} · ISBN ${l.isbn}`"
            :clave-de="(l) => l.isbn"
            placeholder="Buscá por título, autor o ISBN…"
            @elegir="elegirLibro"
          />
        </CampoForm>
        <CampoForm etiqueta="Sede de retiro" requerido>
          <select v-model="nueva.sede_id" :disabled="!sedesDelLibro.length">
            <option value="" disabled>{{ nueva.isbn ? 'Elegí una sede…' : 'Primero elegí el libro' }}</option>
            <option v-for="d in sedesDelLibro" :key="d.sede_id" :value="d.sede_id">
              {{ d.sede }} · {{ d.disponibles }} disp.{{ d.reservas_en_espera ? ` · ${d.reservas_en_espera} en espera` : '' }}
            </option>
          </select>
        </CampoForm>
        <div class="form-actions">
          <span v-if="faltante" class="small muted" style="margin-right: auto; align-self: center">{{ faltante }}</span>
          <button type="button" class="btn" @click="nueva = null">Cancelar</button>
          <button class="btn btn-primary" :disabled="!!faltante">Reservar</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>
