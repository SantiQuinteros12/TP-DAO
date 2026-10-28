<script setup>
/**
 * ABMC de Sedes: alta, modificación, baja/reactivación y listado.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { sedesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'

const sedes = ref([])
const mostrarBajas = ref(true)
const editando = ref(null) // null = cerrado, {} = nueva, {id..} = edición
const form = reactive({ nombre: '', direccion: '', telefono: '', email: '', horario: '' })

const visibles = computed(() => sedes.value.filter((s) => mostrarBajas.value || s.activa))

async function cargar() {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
}

function abrir(sede = {}) {
  Object.assign(form, { nombre: '', direccion: '', telefono: '', email: '', horario: '' }, sede)
  editando.value = sede
}

async function guardar() {
  const datos = { ...form }
  delete datos.id
  delete datos.activa
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

onMounted(cargar)
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Sedes de la red</h1>
        <p>Una sede dada de baja no puede originar ni recibir préstamos, reservas ni envíos.</p>
      </div>
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
              <td>{{ s.direccion }}</td>
              <td class="small">{{ s.telefono }}<br /><span class="muted">{{ s.email }}</span></td>
              <td class="small">{{ s.horario }}</td>
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

    <ModalDialog v-if="editando" :titulo="editando.id ? 'Editar sede' : 'Nueva sede'" @cerrar="editando = null">
      <form class="form" @submit.prevent="guardar">
        <label class="field"><span>Nombre *</span><input v-model="form.nombre" required /></label>
        <label class="field"><span>Dirección *</span><input v-model="form.direccion" required /></label>
        <div class="form-row">
          <label class="field"><span>Teléfono</span><input v-model="form.telefono" /></label>
          <label class="field"><span>Email</span><input v-model="form.email" type="email" /></label>
        </div>
        <label class="field"><span>Horario de atención</span><input v-model="form.horario" placeholder="Lun a Vie 8 a 20" /></label>
        <div class="form-actions">
          <button type="button" class="btn" @click="editando = null">Cancelar</button>
          <button class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>
