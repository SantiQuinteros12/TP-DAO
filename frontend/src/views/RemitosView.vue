<script setup>
/**
 * Seguimiento de remitos. Las acciones que se ofrecen son exactamente las que
 * el backend informa como válidas para el estado actual (patrón State), por
 * lo que la UI nunca necesita replicar la máquina de estados.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EstadoBadge from '../components/EstadoBadge.vue'
import RemitoTimeline from '../components/RemitoTimeline.vue'
import { remitosApi, sedesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { ACCIONES_REMITO, etiqueta, fechaHora } from '../composables/formato'

const route = useRoute()
const router = useRouter()

const remitos = ref([])
const sedes = ref([])
const filtros = reactive({ en_curso: true, tipo: '', sede_id: '', estado: '' })
const ESTADOS = ['CREADO', 'EMPAQUETADO', 'DESPACHADO', 'EN_TRANSITO', 'CON_INCIDENCIA', 'RECIBIDO', 'EXTRAVIADO', 'CANCELADO']

const remito = ref(null)
const accion = ref(null)
const datos = reactive({})

async function cargarLista() {
  remitos.value = (await ejecutar(() => remitosApi.listar(filtros))) ?? []
}
watch(filtros, cargarLista)

async function cargarRemito(id) {
  accion.value = null
  remito.value = id ? ((await ejecutar(() => remitosApi.obtener(id))) ?? null) : null
}
watch(() => route.params.id, (id) => cargarRemito(id), { immediate: true })

const seleccionar = (r) => router.push(`/remitos/${r.id}`)

/** Campos que pide cada acción (las validaciones finales son del backend). */
const CAMPOS = {
  registrar_checkpoint: ['ubicacion', 'observacion'],
  recibir: ['condicion', 'observacion'],
  reportar_incidencia: ['tipo_incidencia', 'observacion'],
  resolver_incidencia: ['observacion'],
  declarar_extravio: ['observacion'],
  cancelar: ['observacion'],
  empaquetar: ['observacion'],
  despachar: ['observacion']
}
const campos = computed(() => CAMPOS[accion.value] ?? [])

function elegirAccion(nombre) {
  accion.value = nombre
  Object.assign(datos, {
    responsable: datos.responsable ?? '',
    ubicacion: '', observacion: '', tipo_incidencia: 'DEMORA', condicion: 'BUENA'
  })
}

async function confirmar() {
  const cuerpo = { responsable: datos.responsable }
  for (const c of campos.value) cuerpo[c] = datos[c]
  const actualizado = await ejecutar(
    () => remitosApi.operar(remito.value.id, accion.value, cuerpo),
    `${ACCIONES_REMITO[accion.value]}: registrado`
  )
  if (actualizado) {
    remito.value = actualizado
    accion.value = null
    cargarLista()
  }
}

onMounted(async () => {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
  cargarLista()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Remitos y seguimiento</h1>
        <p>Empaquetado, despacho, tránsito y recepción de ejemplares entre sedes, con historial completo.</p>
      </div>
    </header>

    <div class="split">
      <div class="card">
        <div class="toolbar" style="margin-bottom: 12px">
          <label class="toolbar small"><input v-model="filtros.en_curso" type="checkbox" style="width: auto" /> Sólo en curso</label>
          <select v-model="filtros.estado">
            <option value="">Todos los estados</option>
            <option v-for="e in ESTADOS" :key="e" :value="e">{{ etiqueta(e) }}</option>
          </select>
          <select v-model="filtros.tipo">
            <option value="">Todos los tipos</option>
            <option v-for="t in ['ENVIO', 'RETORNO', 'TRASLADO']" :key="t" :value="t">{{ etiqueta(t) }}</option>
          </select>
          <select v-model="filtros.sede_id">
            <option value="">Todas las sedes</option>
            <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Remito</th><th>Ejemplar</th><th>Ruta</th><th>Estado</th><th>Últ. movimiento</th></tr></thead>
            <tbody>
              <tr
                v-for="r in remitos"
                :key="r.id"
                class="clickable"
                :class="{ selected: remito?.id === r.id }"
                @click="seleccionar(r)"
              >
                <td>
                  <span class="mono">R-{{ String(r.id).padStart(6, '0') }}</span><br />
                  <span class="small muted">{{ etiqueta(r.tipo) }}</span>
                </td>
                <td>{{ r.titulo }}<br /><span class="small muted mono">{{ r.codigo_inventario }}</span></td>
                <td class="small">{{ r.sede_origen }}<br />→ {{ r.sede_destino }}</td>
                <td>
                  <EstadoBadge :estado="r.estado" />
                  <div v-if="r.incidencias" class="small" style="color: var(--serious-ink)">⚠ {{ r.incidencias }} incidencia(s)</div>
                </td>
                <td class="small">{{ fechaHora(r.ultima_actualizacion) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!remitos.length" class="empty">No hay remitos para los filtros elegidos.</p>
        </div>
      </div>

      <div class="card detalle">
        <template v-if="remito">
          <div class="card-header">
            <div>
              <h2>{{ remito.numero }} · {{ etiqueta(remito.tipo) }}</h2>
              <p>{{ remito.titulo }} ({{ remito.codigo_inventario }})</p>
            </div>
            <EstadoBadge :estado="remito.estado" />
          </div>

          <div class="ruta">
            <div><span class="small muted">Origen</span><strong>{{ remito.sede_origen }}</strong></div>
            <span class="flecha" aria-hidden="true">→</span>
            <div><span class="small muted">Destino</span><strong>{{ remito.sede_destino }}</strong></div>
          </div>
          <p v-if="remito.prestamo_id" class="small muted">Asociado al préstamo #{{ remito.prestamo_id }}</p>

          <div v-if="remito.acciones_disponibles.length" class="acciones">
            <h3>Acciones disponibles</h3>
            <div class="btn-group">
              <button
                v-for="a in remito.acciones_disponibles"
                :key="a"
                class="btn btn-sm"
                :class="{ 'btn-primary': accion === a, 'btn-danger': ['cancelar', 'declarar_extravio'].includes(a) && accion !== a }"
                @click="elegirAccion(a)"
              >
                {{ ACCIONES_REMITO[a] }}
              </button>
            </div>

            <form v-if="accion" class="form panel" @submit.prevent="confirmar">
              <label class="field"><span>Responsable</span><input v-model="datos.responsable" placeholder="Nombre de quien registra" /></label>
              <label v-if="campos.includes('ubicacion')" class="field"><span>Ubicación *</span><input v-model="datos.ubicacion" required placeholder="Ej.: Centro de distribución" /></label>
              <label v-if="campos.includes('tipo_incidencia')" class="field">
                <span>Tipo de incidencia *</span>
                <select v-model="datos.tipo_incidencia">
                  <option v-for="t in ['DEMORA', 'DANO', 'EXTRAVIO', 'OTRO']" :key="t" :value="t">{{ etiqueta(t) }}</option>
                </select>
              </label>
              <label v-if="campos.includes('condicion')" class="field">
                <span>Estado físico al recibir *</span>
                <select v-model="datos.condicion">
                  <option v-for="c in ['BUENA', 'DETERIORADA', 'DANADA']" :key="c" :value="c">{{ etiqueta(c) }}</option>
                </select>
              </label>
              <label class="field">
                <span>Observación {{ ['reportar_incidencia', 'cancelar'].includes(accion) ? '*' : '' }}</span>
                <textarea v-model="datos.observacion" rows="2" :required="['reportar_incidencia', 'cancelar'].includes(accion)" />
              </label>
              <div class="form-actions">
                <button type="button" class="btn" @click="accion = null">Cancelar</button>
                <button class="btn btn-primary">Confirmar: {{ ACCIONES_REMITO[accion] }}</button>
              </div>
            </form>
          </div>
          <p v-else class="alert">Remito finalizado: no admite más operaciones.</p>

          <h3 style="margin: 18px 0 10px">Trazabilidad</h3>
          <RemitoTimeline :historial="[...remito.historial].reverse()" />
        </template>
        <p v-else class="empty">Seleccioná un remito para ver su recorrido y operarlo.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.detalle { position: sticky; top: 20px; }
.ruta {
  display: flex; align-items: center; gap: 14px; padding: 12px 14px;
  border-radius: 8px; background: var(--surface-2); margin-bottom: 8px;
}
.ruta div { display: grid; }
.flecha { font-size: 20px; color: var(--muted); }
.acciones { display: grid; gap: 10px; margin-top: 14px; }
.panel { padding: 14px; border: 1px solid var(--grid); border-radius: 8px; }
@media (max-width: 980px) { .detalle { position: static; } }
</style>
