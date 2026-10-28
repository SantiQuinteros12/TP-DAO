<script setup>
/**
 * Administración de socios: alta, modificación, habilitación/inhabilitación
 * y consulta de notificaciones y préstamos de cada socio.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { prestamosApi, sociosApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { fecha, fechaHora, moneda } from '../composables/formato'

const socios = ref([])
const filtros = reactive({ q: '', habilitado: '' })
const editando = ref(null)
const form = reactive({})
const inhabilitando = ref(null)
const motivo = ref('')
const seleccionado = ref(null)
const detalle = reactive({ notificaciones: [], prestamos: [] })

async function cargar() {
  socios.value = (await ejecutar(() => sociosApi.listar(filtros))) ?? []
}

let espera
watch(filtros, () => {
  clearTimeout(espera)
  espera = setTimeout(cargar, 250)
})

function abrir(socio = {}) {
  Object.assign(form, { nombre: '', apellido: '', documento: '', email: '', telefono: '' }, socio)
  editando.value = socio
}

async function guardar() {
  const { nombre, apellido, documento, email, telefono } = form
  const datos = { nombre, apellido, documento, email, telefono }
  const ok = editando.value.id
    ? await ejecutar(() => sociosApi.actualizar(editando.value.id, datos), 'Socio actualizado')
    : await ejecutar(() => sociosApi.crear(datos), 'Socio registrado')
  if (ok) {
    editando.value = null
    cargar()
  }
}

async function confirmarInhabilitacion() {
  const ok = await ejecutar(() => sociosApi.inhabilitar(inhabilitando.value.id, motivo.value), 'Socio inhabilitado')
  if (ok) {
    inhabilitando.value = null
    motivo.value = ''
    cargar()
  }
}

async function habilitar(socio) {
  if (await ejecutar(() => sociosApi.habilitar(socio.id), 'Socio habilitado')) cargar()
}

async function verDetalle(socio) {
  seleccionado.value = socio
  const [notificaciones, prestamos] = await Promise.all([
    ejecutar(() => sociosApi.notificaciones(socio.id)),
    ejecutar(() => prestamosApi.listar({ socio_id: socio.id }))
  ])
  detalle.notificaciones = notificaciones ?? []
  detalle.prestamos = prestamos ?? []
}

onMounted(cargar)
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Socios</h1>
        <p>Los socios inhabilitados no pueden solicitar préstamos ni reservas.</p>
      </div>
      <button class="btn btn-primary" @click="abrir()">+ Nuevo socio</button>
    </header>

    <div class="split">
      <div class="card">
        <div class="toolbar" style="margin-bottom: 12px">
          <div class="grow"><input v-model="filtros.q" placeholder="Buscar por nombre, apellido o DNI…" /></div>
          <select v-model="filtros.habilitado">
            <option value="">Todos</option>
            <option value="true">Habilitados</option>
            <option value="false">Inhabilitados</option>
          </select>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Socio</th><th>DNI</th><th>Alta</th><th>Estado</th><th /></tr></thead>
            <tbody>
              <tr
                v-for="s in socios"
                :key="s.id"
                class="clickable"
                :class="{ selected: seleccionado?.id === s.id }"
                @click="verDetalle(s)"
              >
                <td><strong>{{ s.nombre_completo }}</strong><br /><span class="small muted">{{ s.email }}</span></td>
                <td class="mono">{{ s.documento }}</td>
                <td class="small">{{ fecha(s.fecha_alta) }}</td>
                <td>
                  <EstadoBadge :estado="s.habilitado ? 'HABILITADO' : 'INHABILITADO'" />
                  <div v-if="!s.habilitado" class="small muted">{{ s.motivo_inhabilitacion }}</div>
                </td>
                <td class="actions" @click.stop>
                  <div class="btn-group" style="justify-content: flex-end">
                    <button class="btn btn-sm" @click="abrir(s)">Editar</button>
                    <button v-if="s.habilitado" class="btn btn-sm btn-danger" @click="inhabilitando = s">Inhabilitar</button>
                    <button v-else class="btn btn-sm" @click="habilitar(s)">Habilitar</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!socios.length" class="empty">Sin resultados.</p>
        </div>
      </div>

      <div class="card">
        <template v-if="seleccionado">
          <div class="card-header">
            <div>
              <h2>{{ seleccionado.nombre_completo }}</h2>
              <p>DNI {{ seleccionado.documento }} · {{ seleccionado.telefono }}</p>
            </div>
          </div>
          <h3>Préstamos ({{ detalle.prestamos.length }})</h3>
          <div class="table-wrap" style="margin-bottom: 16px">
            <table>
              <tbody>
                <tr v-for="p in detalle.prestamos.slice(0, 8)" :key="p.id">
                  <td>{{ p.titulo }}<br /><span class="small muted">{{ p.sede_destino }} · vence {{ fecha(p.fecha_vencimiento) }}</span></td>
                  <td><EstadoBadge :estado="p.vencido ? 'VENCIDO' : p.estado" /></td>
                  <td class="num small">{{ p.multa_estimada ? moneda(p.multa_estimada) : '' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="!detalle.prestamos.length" class="empty">Sin préstamos.</p>
          </div>
          <h3>Notificaciones</h3>
          <ul class="notificaciones">
            <li v-for="n in detalle.notificaciones.slice(0, 10)" :key="n.id">
              <span>{{ n.mensaje }}</span>
              <time class="small muted">{{ fechaHora(n.fecha_hora) }}</time>
            </li>
          </ul>
          <p v-if="!detalle.notificaciones.length" class="empty">Sin notificaciones.</p>
        </template>
        <p v-else class="empty">Seleccioná un socio para ver sus préstamos y notificaciones.</p>
      </div>
    </div>

    <ModalDialog v-if="editando" :titulo="editando.id ? 'Editar socio' : 'Nuevo socio'" @cerrar="editando = null">
      <form class="form" @submit.prevent="guardar">
        <div class="form-row">
          <label class="field"><span>Nombre *</span><input v-model="form.nombre" required /></label>
          <label class="field"><span>Apellido *</span><input v-model="form.apellido" required /></label>
        </div>
        <label class="field"><span>Documento *</span><input v-model="form.documento" required placeholder="30111222" /><small class="hint">7 u 8 dígitos. No puede repetirse.</small></label>
        <div class="form-row">
          <label class="field"><span>Email</span><input v-model="form.email" type="email" /></label>
          <label class="field"><span>Teléfono</span><input v-model="form.telefono" /></label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn" @click="editando = null">Cancelar</button>
          <button class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog v-if="inhabilitando" titulo="Inhabilitar socio" @cerrar="inhabilitando = null">
      <form class="form" @submit.prevent="confirmarInhabilitacion">
        <p>¿Inhabilitar a <strong>{{ inhabilitando.nombre_completo }}</strong>? No podrá iniciar nuevos préstamos ni reservas.</p>
        <label class="field"><span>Motivo *</span><input v-model="motivo" required minlength="3" /></label>
        <div class="form-actions">
          <button type="button" class="btn" @click="inhabilitando = null">Cancelar</button>
          <button class="btn btn-primary">Inhabilitar</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>

<style scoped>
.notificaciones { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px; }
.notificaciones li { display: grid; gap: 2px; padding: 8px 10px; border-radius: 8px; background: var(--surface-2); font-size: 13px; }
</style>
