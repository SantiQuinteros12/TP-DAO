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
import { Building2, Clock, Mail, MapPin, Pencil, Phone, Plus, Power, RotateCcw } from 'lucide-vue-next'

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
      <div>
        <h1>Sedes de la red</h1>
        <p>Bibliotecas que integran la red: ubicación, contacto y horario de atención.</p>
      </div>
      <button class="btn btn-primary" @click="abrir()"><Plus aria-hidden="true" /> Nueva sede</button>
    </header>

    <div class="card">
      <div class="card-header">
        <h2>{{ visibles.length }} sedes</h2>
        <label class="interruptor">
          <input v-model="mostrarBajas" type="checkbox" /> Mostrar dadas de baja
        </label>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Nombre</th><th>Dirección</th><th>Contacto</th><th>Horario</th><th>Estado</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="s in visibles" :key="s.id" :class="{ dada_de_baja: !s.activa }">
              <td>
                <div class="sede">
                  <span class="icono-sede" aria-hidden="true"><Building2 :size="18" /></span>
                  <span class="nombre">{{ s.nombre }}</span>
                </div>
              </td>
              <td class="con-icono"><MapPin :size="14" aria-hidden="true" /><span>{{ s.direccion_texto }}</span></td>
              <td class="contacto">
                <span v-if="s.telefono"><Phone :size="14" aria-hidden="true" /> {{ s.telefono }}</span>
                <span v-if="s.email" class="muted"><Mail :size="14" aria-hidden="true" /> {{ s.email }}</span>
              </td>
              <td class="con-icono horario-celda"><Clock :size="14" aria-hidden="true" /><span>{{ s.horario_texto }}</span></td>
              <td><EstadoBadge :estado="s.activa ? 'ACTIVA' : 'BAJA'" /></td>
              <td class="actions">
                <div class="btn-group derecha">
                  <button class="btn btn-sm btn-ghost" @click="abrir(s)"><Pencil aria-hidden="true" /> Editar</button>
                  <button class="btn btn-sm" :class="{ 'btn-danger': s.activa }" @click="cambiarEstado(s)">
                    <component :is="s.activa ? Power : RotateCcw" aria-hidden="true" /> {{ s.activa ? 'Dar de baja' : 'Reactivar' }}
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

        <div class="field bloque">
          <span class="bloque-titulo"><Clock :size="15" aria-hidden="true" /> Horario de atención</span>
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
.interruptor {
  display: inline-flex; align-items: center; gap: var(--space-2); min-height: 36px; padding: 0 var(--space-3);
  border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--surface);
  font-size: 14px; font-weight: 550; color: var(--ink-2); cursor: pointer; user-select: none;
  transition: background var(--dur) var(--ease), border-color var(--dur) var(--ease);
}
.interruptor:hover { background: var(--surface-2); }
.interruptor:has(input:checked) { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.sede { display: flex; align-items: center; gap: var(--space-3); min-width: 170px; }
.icono-sede {
  display: grid; place-items: center; flex: none; width: 36px; height: 36px; border-radius: 10px;
  background: var(--accent-soft); color: var(--accent);
}
.nombre { font-weight: 600; color: var(--ink); }
tr.dada_de_baja .icono-sede { background: var(--surface-2); color: var(--muted); }
tr.dada_de_baja .nombre { color: var(--muted); }

.con-icono { font-size: var(--text-sm); color: var(--ink-2); }
.con-icono svg { float: left; margin: 3px 6px 0 0; color: var(--muted); }
.con-icono span { display: block; overflow: hidden; }
.contacto { font-size: var(--text-sm); color: var(--ink-2); white-space: nowrap; }
.contacto span { display: flex; align-items: center; gap: 6px; }
.contacto svg { color: var(--muted); flex: none; }
.horario-celda { max-width: 260px; }
.derecha { justify-content: flex-end; flex-wrap: nowrap; }

.bloque { padding: var(--space-4); border: 1px solid var(--border); border-radius: var(--radius); gap: var(--space-3); }
.bloque-titulo { display: inline-flex; align-items: center; gap: 6px; }
.bloque-titulo svg { color: var(--accent); }
</style>
