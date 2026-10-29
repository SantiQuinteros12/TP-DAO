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
import { Bell, BookOpen, Mail, MousePointerClick, Pencil, Phone, Plus, Search, UserCheck, UserX } from 'lucide-vue-next'

/** Iniciales para el avatar ("Apellido, Nombre" -> "AN"). */
const iniciales = (nombre = '') => nombre.split(/[\s,]+/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase()

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
      <div>
        <h1>Socios</h1>
        <p>Padrón de lectores, su estado de habilitación, préstamos y avisos recibidos.</p>
      </div>
      <button class="btn btn-primary" @click="abrir()"><Plus aria-hidden="true" /> Nuevo socio</button>
    </header>

    <div class="split">
      <div class="card">
        <div class="toolbar filtros">
          <div class="grow buscador">
            <Search class="lupa" :size="16" aria-hidden="true" />
            <input v-model="filtros.q" placeholder="Buscar por nombre, apellido o DNI…" />
          </div>
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
                <td>
                  <div class="persona">
                    <span class="avatar" :class="{ inhabilitado: !s.habilitado }" aria-hidden="true">{{ iniciales(s.nombre_completo) }}</span>
                    <span class="datos">
                      <span class="nombre">{{ s.nombre_completo }}</span>
                      <span class="email">{{ s.email || 'Sin email' }}</span>
                    </span>
                  </div>
                </td>
                <td class="mono dni">{{ s.documento }}</td>
                <td class="fecha-celda">{{ fecha(s.fecha_alta) }}</td>
                <td>
                  <div class="estado-socio">
                    <EstadoBadge :estado="s.habilitado ? 'HABILITADO' : 'INHABILITADO'" />
                    <button v-if="!s.habilitado" class="link" type="button" @click.stop="viendoMotivo = s">Ver motivo</button>
                  </div>
                </td>
                <td class="actions" @click.stop>
                  <div class="btn-group derecha">
                    <button class="btn btn-sm btn-ghost solo-icono" title="Editar socio" aria-label="Editar socio" @click="abrir(s)"><Pencil aria-hidden="true" /></button>
                    <button v-if="s.habilitado" class="btn btn-sm btn-danger" @click="abrirInhabilitacion(s)"><UserX aria-hidden="true" /> Inhabilitar</button>
                    <button v-else class="btn btn-sm" @click="habilitar(s)"><UserCheck aria-hidden="true" /> Habilitar</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!socios.length" class="empty">No hay socios que coincidan con la búsqueda.</p>
        </div>
      </div>

      <div class="card detalle">
        <template v-if="seleccionado">
          <div class="ficha">
            <span class="avatar grande" :class="{ inhabilitado: !seleccionado.habilitado }" aria-hidden="true">{{ iniciales(seleccionado.nombre_completo) }}</span>
            <div class="ficha-datos">
              <h2>{{ seleccionado.nombre_completo }}</h2>
              <ul class="contacto">
                <li><span class="mono">DNI {{ seleccionado.documento }}</span></li>
                <li v-if="seleccionado.telefono"><Phone :size="14" aria-hidden="true" /> {{ seleccionado.telefono }}</li>
                <li v-if="seleccionado.email"><Mail :size="14" aria-hidden="true" /> {{ seleccionado.email }}</li>
              </ul>
            </div>
            <EstadoBadge :estado="seleccionado.habilitado ? 'HABILITADO' : 'INHABILITADO'" />
          </div>
          <h3 class="subtitulo"><BookOpen :size="15" aria-hidden="true" /> Préstamos <span class="cuenta">{{ detalle.prestamos.length }}</span></h3>
          <div class="table-wrap con-margen">
            <table>
              <tbody>
                <tr v-for="p in detalle.prestamos.slice(0, 8)" :key="p.id">
                  <td><span class="titulo-prestamo">{{ p.titulo }}</span><span class="small muted">{{ p.sede_destino }} · vence {{ fecha(p.fecha_vencimiento) }}</span></td>
                  <td><EstadoBadge :estado="p.vencido ? 'VENCIDO' : p.estado" /></td>
                  <td class="num small">{{ p.multa_estimada ? moneda(p.multa_estimada) : '' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="!detalle.prestamos.length" class="empty">Todavía no pidió préstamos.</p>
          </div>
          <h3 class="subtitulo"><Bell :size="15" aria-hidden="true" /> Notificaciones <span class="cuenta">{{ detalle.notificaciones.length }}</span></h3>
          <ul class="notificaciones">
            <li v-for="n in detalle.notificaciones.slice(0, 10)" :key="n.id">
              <Bell class="icono-aviso" :size="15" aria-hidden="true" />
              <span>{{ n.mensaje }}</span>
              <time class="small muted">{{ fechaHora(n.fecha_hora) }}</time>
            </li>
          </ul>
          <p v-if="!detalle.notificaciones.length" class="empty">Sin notificaciones.</p>
        </template>
        <div v-else class="sin-seleccion">
          <MousePointerClick :size="28" aria-hidden="true" />
          <p>Seleccioná un socio de la lista para ver sus préstamos y notificaciones.</p>
        </div>
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
          <button class="btn btn-danger btn-danger-solid">Inhabilitar</button>
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
.filtros { margin-bottom: var(--space-4); }
.buscador { position: relative; }
.buscador .lupa { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.buscador input { padding-left: 36px; }

/* Avatar con iniciales */
.avatar {
  display: grid; place-items: center; flex: none; width: 36px; height: 36px; border-radius: 50%;
  background: var(--accent-soft); color: var(--accent); font-size: var(--text-sm); font-weight: 700; letter-spacing: 0.02em;
}
.avatar.inhabilitado { background: var(--critical-bg); color: var(--critical-ink); }
.avatar.grande { width: 52px; height: 52px; font-size: var(--text-lg); }

/* Lista */
.persona { display: flex; align-items: center; gap: var(--space-3); min-width: 160px; }
.datos { display: grid; min-width: 0; }
.nombre { font-weight: 600; color: var(--ink); }
.email { font-size: var(--text-sm); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dni { color: var(--ink-2); white-space: nowrap; }
.fecha-celda { font-size: var(--text-sm); color: var(--ink-2); white-space: nowrap; font-variant-numeric: tabular-nums; }
.estado-socio { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.derecha { justify-content: flex-end; flex-wrap: nowrap; gap: var(--space-1); }
.solo-icono { width: 32px; padding: 0; }

/* Ficha del socio */
.detalle { position: sticky; top: var(--space-5); display: grid; gap: var(--space-4); align-content: start; }
.ficha {
  display: flex; align-items: flex-start; gap: var(--space-4);
  padding-bottom: var(--space-4); border-bottom: 1px solid var(--border);
}
.ficha-datos { flex: 1; min-width: 0; display: grid; gap: 6px; }
.contacto { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-4); margin: 0; padding: 0; list-style: none; font-size: var(--text-sm); color: var(--ink-2); }
.contacto li { display: inline-flex; align-items: center; gap: 5px; overflow-wrap: anywhere; }
.contacto svg { color: var(--muted); flex: none; }

.subtitulo {
  display: flex; align-items: center; gap: 6px;
  font-size: var(--text-xs); font-weight: 650; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em;
}
.cuenta {
  padding: 0 7px; border-radius: var(--radius-pill); background: var(--surface-2);
  color: var(--ink-2); font-size: var(--text-xs); letter-spacing: 0; font-variant-numeric: tabular-nums;
}
.con-margen { margin-bottom: var(--space-2); }
.titulo-prestamo { display: block; font-weight: 550; }

.notificaciones { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
.notificaciones li {
  display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 2px var(--space-3);
  padding: var(--space-3); border-radius: var(--radius-md);
  background: var(--surface-2); border: 1px solid var(--border); font-size: 14px;
}
.icono-aviso { grid-row: span 2; margin-top: 2px; color: var(--accent); }
.notificaciones time { color: var(--muted); font-size: var(--text-xs); }

.sin-seleccion {
  display: grid; justify-items: center; gap: var(--space-3); padding: var(--space-10) var(--space-5);
  text-align: center; color: var(--muted);
}
.sin-seleccion svg { color: var(--accent); opacity: 0.7; }

/* Modal de motivo */
.motivo p { margin: 0 0 var(--space-3); }
.motivo blockquote {
  margin: 0 0 var(--space-4); padding: var(--space-3) var(--space-4); border-left: 3px solid var(--critical);
  background: var(--critical-bg); color: var(--critical-ink); border-radius: 0 var(--radius-md) var(--radius-md) 0;
  font-size: 15px;
}

@media (max-width: 980px) { .detalle { position: static; } }
</style>
