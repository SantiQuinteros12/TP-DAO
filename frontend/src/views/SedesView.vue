<script setup>
/**
 * ABMC de Sedes: alta, modificación, baja/reactivación y listado.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import CampoForm from '../components/CampoForm.vue'
import DireccionEditor from '../components/DireccionEditor.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import HorarioEditor from '../components/HorarioEditor.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { sedesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { r, useValidacion } from '../composables/validacion'
import { copiarFranjas, errorHorario } from '../composables/horario'

const sedes = ref([])
const provincias = ref([])
const mostrarBajas = ref(true)
const editando = ref(null) // null = cerrado, {} = nueva, {id..} = edición

const DIRECCION_VACIA = { calle: '', numero: '', piso_depto: '', barrio: '', ciudad: 'Córdoba', provincia: 'Córdoba', codigo_postal: '' }
const form = reactive({ nombre: '', telefono: '', email: '', horario: [] })
const direccion = reactive({ ...DIRECCION_VACIA })

const vSede = useValidacion(form, {
  nombre: [r.requerido('El nombre'), r.minimo(3), r.maximo(80)],
  telefono: [r.telefono()],
  email: [r.email()],
  horario: [(h) => errorHorario(h)]
})
const vDireccion = useValidacion(direccion, {
  calle: [r.requerido('La calle'), r.conLetras(), r.maximo(80)],
  numero: [r.requerido('La altura'), r.altura()],
  piso_depto: [r.maximo(20)],
  barrio: [r.maximo(60)],
  ciudad: [r.requerido('La ciudad'), r.nombre()],
  provincia: [r.requerido('La provincia')],
  codigo_postal: [r.codigoPostal()]
})

const visibles = computed(() => sedes.value.filter((s) => mostrarBajas.value || s.activa))

async function cargar() {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
}

function abrir(sede = {}) {
  Object.assign(form, {
    nombre: sede.nombre ?? '',
    telefono: sede.telefono ?? '',
    email: sede.email ?? '',
    horario: copiarFranjas(sede.horario ?? [{ dias: [0, 1, 2, 3, 4], desde: '08:00', hasta: '20:00' }])
  })
  Object.assign(direccion, DIRECCION_VACIA, sede.direccion ?? {})
  vSede.reiniciar()
  vDireccion.reiniciar()
  editando.value = sede
}

async function guardar() {
  const okSede = vSede.validar()
  if (!vDireccion.validar() || !okSede) return
  const datos = { ...form, direccion: { ...direccion } }
  const ok = editando.value.id
    ? await ejecutar(() => sedesApi.actualizar(editando.value.id, datos), 'Sede actualizada')
    : await ejecutar(() => sedesApi.crear(datos), 'Sede creada')
  if (ok) {
    editando.value = null
    cargar()
  }
}

async function cambiarEstado(sede) {
  const ok = sede.activa
    ? await ejecutar(() => sedesApi.darDeBaja(sede.id), `Sede "${sede.nombre}" dada de baja`)
    : await ejecutar(() => sedesApi.reactivar(sede.id), `Sede "${sede.nombre}" reactivada`)
  if (ok) cargar()
}

onMounted(async () => {
  provincias.value = (await ejecutar(() => sedesApi.provincias())) ?? []
  cargar()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <h1>Sedes de la red</h1>
      <button class="btn btn-primary" @click="abrir()">+ Nueva sede</button>
    </header>

    <div class="card">
      <div class="card-header">
        <h2>{{ visibles.length }} sedes</h2>
        <label class="toolbar small">
          <input v-model="mostrarBajas" type="checkbox" style="width: auto" /> Mostrar dadas de baja
        </label>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Nombre</th><th>Dirección</th><th>Contacto</th><th>Horario</th><th>Estado</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="s in visibles" :key="s.id">
              <td><strong>{{ s.nombre }}</strong></td>
              <td class="small">{{ s.direccion_texto }}</td>
              <td class="small">{{ s.telefono }}<br /><span class="muted">{{ s.email }}</span></td>
              <td class="small horario-celda">{{ s.horario_texto }}</td>
              <td><EstadoBadge :estado="s.activa ? 'ACTIVA' : 'BAJA'" /></td>
              <td class="actions">
                <div class="btn-group" style="justify-content: flex-end">
                  <button class="btn btn-sm" @click="abrir(s)">Editar</button>
                  <button class="btn btn-sm" :class="{ 'btn-danger': s.activa }" @click="cambiarEstado(s)">
                    {{ s.activa ? 'Dar de baja' : 'Reactivar' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!visibles.length" class="empty">No hay sedes registradas.</p>
      </div>
    </div>

    <ModalDialog v-if="editando" :titulo="editando.id ? 'Editar sede' : 'Nueva sede'" ancho="640px" @cerrar="editando = null">
      <form class="form" novalidate @submit.prevent="guardar">
        <CampoForm etiqueta="Nombre" requerido :error="vSede.error('nombre')" @tocar="vSede.tocar('nombre')">
          <input v-model="form.nombre" maxlength="80" placeholder="Sede Centro" />
        </CampoForm>

        <DireccionEditor v-model="direccion" :provincias="provincias" :validacion="vDireccion" />

        <div class="form-row">
          <CampoForm etiqueta="Teléfono" :error="vSede.error('telefono')" @tocar="vSede.tocar('telefono')">
            <input v-model="form.telefono" v-filtro="'telefono'" type="tel" inputmode="tel" maxlength="20" placeholder="0351-4331100" />
          </CampoForm>
          <CampoForm etiqueta="Email" :error="vSede.error('email')" @tocar="vSede.tocar('email')">
            <input v-model="form.email" type="email" maxlength="120" placeholder="sede@bibliored.org" />
          </CampoForm>
        </div>

        <div class="field">
          <span>Horario de atención</span>
          <HorarioEditor v-model="form.horario" />
        </div>

        <div class="form-actions">
          <button type="button" class="btn" @click="editando = null">Cancelar</button>
          <button class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>

<style scoped>
.horario-celda { max-width: 240px; }
</style>
