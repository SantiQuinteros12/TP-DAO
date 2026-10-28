<script setup>
/**
 * Gestión de reservas: cola FIFO por libro y sede. Cuando un ejemplar se
 * libera, el backend lo asigna automáticamente a la reserva más antigua.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { catalogoApi, reservasApi, sedesApi, sociosApi } from '../services/api'
import { ejecutar, useToast } from '../composables/useToast'
import { etiqueta, fecha } from '../composables/formato'

const toast = useToast()
const reservas = ref([])
const sedes = ref([])
const filtros = reactive({ estado: '', sede_id: '' })
const ESTADOS = ['PENDIENTE', 'DISPONIBLE', 'CUMPLIDA', 'CANCELADA', 'VENCIDA']

const nueva = ref(null)
const socios = ref([])
const libros = ref([])

async function cargar() {
  reservas.value = (await ejecutar(() => reservasApi.listar(filtros))) ?? []
}
watch(filtros, cargar)

async function abrirNueva() {
  nueva.value = { socio_id: '', isbn: '', sede_id: '' }
  const [s, l] = await Promise.all([
    ejecutar(() => sociosApi.listar({ habilitado: true })),
    ejecutar(() => catalogoApi.listarLibros())
  ])
  socios.value = s ?? []
  libros.value = l ?? []
}

async function crear() {
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
      <div>
        <h1>Reservas</h1>
        <p>Se atienden por orden de llegada. Una reserva disponible debe retirarse dentro de los 3 días.</p>
      </div>
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

    <ModalDialog v-if="nueva" titulo="Nueva reserva" @cerrar="nueva = null">
      <form class="form" @submit.prevent="crear">
        <label class="field">
          <span>Socio *</span>
          <select v-model="nueva.socio_id" required>
            <option value="" disabled>Elegí un socio habilitado…</option>
            <option v-for="s in socios" :key="s.id" :value="s.id">{{ s.nombre_completo }} — DNI {{ s.documento }}</option>
          </select>
        </label>
        <label class="field">
          <span>Libro *</span>
          <select v-model="nueva.isbn" required>
            <option value="" disabled>Elegí un libro…</option>
            <option v-for="l in libros" :key="l.isbn" :value="l.isbn">{{ l.titulo }} — {{ l.autor }}</option>
          </select>
        </label>
        <label class="field">
          <span>Sede de retiro *</span>
          <select v-model="nueva.sede_id" required>
            <option value="" disabled>Elegí una sede…</option>
            <option v-for="s in sedes.filter((x) => x.activa)" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
          <small class="hint">La sede debe poseer ejemplares del libro. Si no, solicitá un préstamo interbibliotecario.</small>
        </label>
        <div class="form-actions">
          <button type="button" class="btn" @click="nueva = null">Cancelar</button>
          <button class="btn btn-primary">Reservar</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>
