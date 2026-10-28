<script setup>
/**
 * Administración de socios: alta, modificación, habilitación/inhabilitación
 * y consulta de notificaciones y préstamos de cada socio.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import CampoForm from '../components/CampoForm.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { prestamosApi, sociosApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { fecha, fechaHora, moneda } from '../composables/formato'
import { r, useValidacion } from '../composables/validacion'

const socios = ref([])
const filtros = reactive({ q: '', habilitado: '' })
const editando = ref(null)
const form = reactive({ nombre: '', apellido: '', documento: '', email: '', telefono: '' })
const inhabilitando = ref(null)
const motivo = reactive({ texto: '' })
const viendoMotivo = ref(null)

const v = useValidacion(form, {
  nombre: [r.requerido('El nombre'), r.nombre(), r.maximo(60)],
  apellido: [r.requerido('El apellido'), r.nombre(), r.maximo(60)],
  documento: [r.requerido('El documento'), r.dni()],
  email: [r.email()],
  telefono: [r.telefono()]
})
const vMotivo = useValidacion(motivo, { texto: [r.requerido('El motivo'), r.minimo(3), r.maximo(200)] })
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
  const { nombre = '', apellido = '', documento = '', email = '', telefono = '' } = socio
  Object.assign(form, { nombre, apellido, documento, email, telefono })
  v.reiniciar()
  editando.value = socio
}

async function guardar() {
  if (!v.validar()) return
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

function abrirInhabilitacion(socio) {
  motivo.texto = ''
  vMotivo.reiniciar()
  inhabilitando.value = socio
}

async function confirmarInhabilitacion() {
  if (!vMotivo.validar()) return
  const ok = await ejecutar(() => sociosApi.inhabilitar(inhabilitando.value.id, motivo.texto.trim()), 'Socio inhabilitado')
  if (ok) {
    inhabilitando.value = null
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
      <h1>Socios</h1>
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
                  <div class="estado-socio">
                    <EstadoBadge :estado="s.habilitado ? 'HABILITADO' : 'INHABILITADO'" />
                    <button v-if="!s.habilitado" class="link" type="button" @click.stop="viendoMotivo = s">Ver motivo</button>
                  </div>
                </td>
                <td class="actions" @click.stop>
                  <div class="btn-group" style="justify-content: flex-end">
                    <button class="btn btn-sm" @click="abrir(s)">Editar</button>
                    <button v-if="s.habilitado" class="btn btn-sm btn-danger" @click="abrirInhabilitacion(s)">Inhabilitar</button>
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
      <form class="form" novalidate @submit.prevent="guardar">
        <div class="form-row">
          <CampoForm etiqueta="Nombre" requerido :error="v.error('nombre')" @tocar="v.tocar('nombre')">
            <input v-model="form.nombre" v-filtro="'nombre'" maxlength="60" autocomplete="given-name" />
          </CampoForm>
          <CampoForm etiqueta="Apellido" requerido :error="v.error('apellido')" @tocar="v.tocar('apellido')">
            <input v-model="form.apellido" v-filtro="'nombre'" maxlength="60" autocomplete="family-name" />
          </CampoForm>
        </div>
        <CampoForm etiqueta="Documento (DNI)" requerido :error="v.error('documento')" @tocar="v.tocar('documento')">
          <input v-model="form.documento" v-filtro="'dni'" inputmode="numeric" maxlength="10" placeholder="30111222" />
        </CampoForm>
        <div class="form-row">
          <CampoForm etiqueta="Email" :error="v.error('email')" @tocar="v.tocar('email')">
            <input v-model="form.email" type="email" maxlength="120" placeholder="nombre@mail.com" autocomplete="email" />
          </CampoForm>
          <CampoForm etiqueta="Teléfono" :error="v.error('telefono')" @tocar="v.tocar('telefono')">
            <input v-model="form.telefono" v-filtro="'telefono'" type="tel" inputmode="tel" maxlength="20" placeholder="351-5123456" autocomplete="tel" />
          </CampoForm>
        </div>
        <div class="form-actions">
          <button type="button" class="btn" @click="editando = null">Cancelar</button>
          <button class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog v-if="inhabilitando" titulo="Inhabilitar socio" @cerrar="inhabilitando = null">
      <form class="form" novalidate @submit.prevent="confirmarInhabilitacion">
        <p>¿Inhabilitar a <strong>{{ inhabilitando.nombre_completo }}</strong>? No podrá iniciar nuevos préstamos ni reservas.</p>
        <CampoForm etiqueta="Motivo" requerido :error="vMotivo.error('texto')" @tocar="vMotivo.tocar('texto')">
          <textarea v-model="motivo.texto" rows="3" maxlength="200" placeholder="Ej.: multas impagas" />
        </CampoForm>
        <div class="form-actions">
          <button type="button" class="btn" @click="inhabilitando = null">Cancelar</button>
          <button class="btn btn-primary">Inhabilitar</button>
        </div>
      </form>
    </ModalDialog>
    <ModalDialog v-if="viendoMotivo" titulo="Motivo de la inhabilitación" ancho="440px" @cerrar="viendoMotivo = null">
      <div class="motivo">
        <p><strong>{{ viendoMotivo.nombre_completo }}</strong> · DNI {{ viendoMotivo.documento }}</p>
        <blockquote>{{ viendoMotivo.motivo_inhabilitacion || 'Sin motivo registrado.' }}</blockquote>
        <div class="form-actions">
          <button type="button" class="btn" @click="viendoMotivo = null">Cerrar</button>
          <button type="button" class="btn btn-primary" @click="habilitar(viendoMotivo); viendoMotivo = null">Habilitar socio</button>
        </div>
      </div>
    </ModalDialog>
  </section>
</template>

<style scoped>
.notificaciones { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px; }
.estado-socio { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.motivo p { margin: 0 0 10px; }
.motivo blockquote {
  margin: 0 0 14px; padding: 10px 14px; border-left: 3px solid var(--critical);
  background: var(--critical-bg); color: var(--critical-ink); border-radius: 0 8px 8px 0;
}
.notificaciones li { display: grid; gap: 2px; padding: 8px 10px; border-radius: 8px; background: var(--surface-2); font-size: 13px; }
</style>
