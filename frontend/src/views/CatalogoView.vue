<script setup>
/**
 * Catálogo: libros, ejemplares físicos (asignados a una sede) y consulta de
 * disponibilidad por libro y por sede.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import { catalogoApi, sedesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { etiqueta } from '../composables/formato'

const router = useRouter()
const tab = ref('disponibilidad')
const sedes = ref([])
const sedesActivas = computed(() => sedes.value.filter((s) => s.activa))

// --- libros ---------------------------------------------------------------
const libros = ref([])
const qLibros = ref('')
const libroEditando = ref(null)
const formLibro = reactive({})

async function cargarLibros() {
  libros.value = (await ejecutar(() => catalogoApi.listarLibros(qLibros.value))) ?? []
}

function abrirLibro(libro = {}) {
  Object.assign(formLibro, { isbn: '', titulo: '', autor: '', editorial: '', anio_publicacion: null, genero: '' }, libro)
  libroEditando.value = libro
}

async function guardarLibro() {
  const { isbn, ...datos } = formLibro
  datos.anio_publicacion = datos.anio_publicacion || null
  const ok = libroEditando.value.isbn
    ? await ejecutar(() => catalogoApi.actualizarLibro(isbn, datos), 'Libro actualizado')
    : await ejecutar(() => catalogoApi.crearLibro({ isbn, ...datos }), 'Libro agregado al catálogo')
  if (ok) {
    libroEditando.value = null
    cargarLibros()
  }
}

// --- ejemplares -----------------------------------------------------------
const ejemplares = ref([])
const filtrosEj = reactive({ q: '', sede_id: '', estado: '', isbn: '' })
const nuevoEjemplar = ref(null)
const trasladando = ref(null)
const sedeTraslado = ref('')
const ESTADOS = ['DISPONIBLE', 'RESERVADO', 'EN_PRESTAMO', 'EN_TRANSITO', 'DANADO', 'BAJA']

async function cargarEjemplares() {
  ejemplares.value = (await ejecutar(() => catalogoApi.listarEjemplares(filtrosEj))) ?? []
}

function verEjemplares(libro) {
  Object.assign(filtrosEj, { q: '', sede_id: '', estado: '', isbn: libro.isbn })
  tab.value = 'ejemplares'
}

async function crearEjemplar() {
  const { isbn, sede_id, codigo_inventario } = nuevoEjemplar.value
  const ok = await ejecutar(
    () => catalogoApi.crearEjemplar({ isbn, sede_id, codigo_inventario: codigo_inventario || null }),
    'Ejemplar registrado'
  )
  if (ok) {
    nuevoEjemplar.value = null
    cargarEjemplares()
  }
}

async function accionEjemplar(fn, mensaje) {
  if (await ejecutar(fn, mensaje)) cargarEjemplares()
}

async function confirmarTraslado() {
  const remito = await ejecutar(
    () => catalogoApi.trasladarEjemplar(trasladando.value.id, Number(sedeTraslado.value)),
    'Remito de traslado generado'
  )
  if (remito) {
    trasladando.value = null
    router.push(`/remitos/${remito.id}`)
  }
}

// --- disponibilidad -------------------------------------------------------
const disponibilidad = ref([])
const filtrosDisp = reactive({ q: '', sede_id: '' })

async function cargarDisponibilidad() {
  disponibilidad.value = (await ejecutar(() => catalogoApi.disponibilidad(filtrosDisp))) ?? []
}

/** Agrupa la matriz libro x sede por libro para mostrarla compacta. */
const disponibilidadPorLibro = computed(() => {
  const grupos = new Map()
  for (const fila of disponibilidad.value) {
    if (!grupos.has(fila.isbn)) grupos.set(fila.isbn, { ...fila, sedes: [], totalDisp: 0 })
    const g = grupos.get(fila.isbn)
    g.sedes.push(fila)
    g.totalDisp += fila.disponibles
  }
  return [...grupos.values()]
})

// --- carga ----------------------------------------------------------------
let espera
const conEspera = (fn) => () => {
  clearTimeout(espera)
  espera = setTimeout(fn, 250)
}
watch(qLibros, conEspera(cargarLibros))
watch(filtrosEj, conEspera(cargarEjemplares))
watch(filtrosDisp, conEspera(cargarDisponibilidad))

onMounted(async () => {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
  cargarLibros()
  cargarEjemplares()
  cargarDisponibilidad()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Catálogo</h1>
        <p>Libros, ejemplares físicos por sede y disponibilidad en toda la red.</p>
      </div>
      <div class="btn-group">
        <button class="btn" @click="abrirLibro()">+ Libro</button>
        <button class="btn btn-primary" @click="nuevoEjemplar = { isbn: '', sede_id: '', codigo_inventario: '' }">+ Ejemplar</button>
      </div>
    </header>

    <div class="tabs" role="tablist">
      <button class="tab" :class="{ active: tab === 'disponibilidad' }" @click="tab = 'disponibilidad'">Disponibilidad</button>
      <button class="tab" :class="{ active: tab === 'libros' }" @click="tab = 'libros'">Libros ({{ libros.length }})</button>
      <button class="tab" :class="{ active: tab === 'ejemplares' }" @click="tab = 'ejemplares'">Ejemplares</button>
    </div>

    <!-- Disponibilidad -->
    <div v-if="tab === 'disponibilidad'" class="card">
      <div class="toolbar" style="margin-bottom: 12px">
        <div class="grow"><input v-model="filtrosDisp.q" placeholder="Buscar libro por título, autor o ISBN…" /></div>
        <select v-model="filtrosDisp.sede_id">
          <option value="">Todas las sedes</option>
          <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Libro</th><th>Sede</th><th class="num">Disponibles</th><th class="num">Prestados</th>
              <th class="num">Reservados</th><th class="num">En tránsito</th><th class="num">Dañados</th><th class="num">En espera</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="libro in disponibilidadPorLibro" :key="libro.isbn">
              <tr v-for="(f, i) in libro.sedes" :key="f.sede_id">
                <td v-if="i === 0" :rowspan="libro.sedes.length">
                  <strong>{{ libro.titulo }}</strong><br />
                  <span class="small muted">{{ libro.autor }}</span><br />
                  <span class="small" :class="libro.totalDisp ? '' : 'muted'">{{ libro.totalDisp }} disponible(s) en la red</span>
                </td>
                <td>{{ f.sede }} <span v-if="!f.sede_activa" class="small muted">(baja)</span></td>
                <td class="num"><strong>{{ f.disponibles }}</strong></td>
                <td class="num">{{ f.prestados }}</td>
                <td class="num">{{ f.reservados }}</td>
                <td class="num">{{ f.en_transito }}</td>
                <td class="num">{{ f.danados }}</td>
                <td class="num">{{ f.reservas_en_espera || '' }}</td>
              </tr>
            </template>
          </tbody>
        </table>
        <p v-if="!disponibilidadPorLibro.length" class="empty">Sin resultados.</p>
      </div>
    </div>

    <!-- Libros -->
    <div v-if="tab === 'libros'" class="card">
      <div class="toolbar" style="margin-bottom: 12px">
        <div class="grow"><input v-model="qLibros" placeholder="Buscar por título, autor o ISBN…" /></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>ISBN</th><th>Título</th><th>Autor</th><th>Editorial</th><th>Año</th><th>Género</th><th /></tr></thead>
          <tbody>
            <tr v-for="l in libros" :key="l.isbn">
              <td class="mono">{{ l.isbn }}</td>
              <td><strong>{{ l.titulo }}</strong></td>
              <td>{{ l.autor }}</td>
              <td>{{ l.editorial }}</td>
              <td>{{ l.anio_publicacion }}</td>
              <td>{{ l.genero }}</td>
              <td class="actions">
                <div class="btn-group" style="justify-content: flex-end">
                  <button class="btn btn-sm" @click="verEjemplares(l)">Ejemplares</button>
                  <button class="btn btn-sm" @click="abrirLibro(l)">Editar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Ejemplares -->
    <div v-if="tab === 'ejemplares'" class="card">
      <div class="toolbar" style="margin-bottom: 12px">
        <div class="grow"><input v-model="filtrosEj.q" placeholder="Título, autor o código de inventario…" /></div>
        <select v-model="filtrosEj.sede_id">
          <option value="">Todas las sedes</option>
          <option v-for="s in sedes" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <select v-model="filtrosEj.estado">
          <option value="">Todos los estados</option>
          <option v-for="e in ESTADOS" :key="e" :value="e">{{ etiqueta(e) }}</option>
        </select>
        <button v-if="filtrosEj.isbn" class="btn btn-sm" @click="filtrosEj.isbn = ''">ISBN {{ filtrosEj.isbn }} ✕</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Libro</th><th>Sede propietaria</th><th>Ubicación actual</th><th>Estado</th><th>Condición</th><th /></tr></thead>
          <tbody>
            <tr v-for="e in ejemplares" :key="e.id">
              <td class="mono">{{ e.codigo_inventario }}</td>
              <td>{{ e.titulo }}</td>
              <td>{{ e.sede }}</td>
              <td :class="{ muted: e.sede_actual_id === e.sede_id }">{{ e.sede_actual }}</td>
              <td><EstadoBadge :estado="e.estado" /></td>
              <td class="small">{{ etiqueta(e.condicion) }}</td>
              <td class="actions">
                <div class="btn-group" style="justify-content: flex-end">
                  <button v-if="e.estado === 'DISPONIBLE'" class="btn btn-sm" @click="trasladando = e; sedeTraslado = ''">Trasladar</button>
                  <button v-if="e.estado === 'DANADO'" class="btn btn-sm" @click="accionEjemplar(() => catalogoApi.repararEjemplar(e.id), 'Ejemplar reincorporado')">Reparar</button>
                  <button v-if="['DISPONIBLE', 'DANADO'].includes(e.estado)" class="btn btn-sm btn-danger" @click="accionEjemplar(() => catalogoApi.bajaEjemplar(e.id), 'Ejemplar dado de baja')">Baja</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!ejemplares.length" class="empty">Sin ejemplares para los filtros elegidos.</p>
      </div>
    </div>

    <!-- Modales -->
    <ModalDialog v-if="libroEditando" :titulo="libroEditando.isbn ? 'Editar libro' : 'Nuevo libro'" @cerrar="libroEditando = null">
      <form class="form" @submit.prevent="guardarLibro">
        <label class="field">
          <span>ISBN *</span>
          <input v-model="formLibro.isbn" :disabled="!!libroEditando.isbn" required placeholder="978-…" />
          <small class="hint">ISBN-10 o ISBN-13 válido (se verifica el dígito de control).</small>
        </label>
        <label class="field"><span>Título *</span><input v-model="formLibro.titulo" required /></label>
        <label class="field"><span>Autor *</span><input v-model="formLibro.autor" required /></label>
        <div class="form-row">
          <label class="field"><span>Editorial</span><input v-model="formLibro.editorial" /></label>
          <label class="field"><span>Año</span><input v-model.number="formLibro.anio_publicacion" type="number" /></label>
          <label class="field"><span>Género</span><input v-model="formLibro.genero" /></label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn" @click="libroEditando = null">Cancelar</button>
          <button class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog v-if="nuevoEjemplar" titulo="Nuevo ejemplar físico" @cerrar="nuevoEjemplar = null">
      <form class="form" @submit.prevent="crearEjemplar">
        <label class="field">
          <span>Libro *</span>
          <select v-model="nuevoEjemplar.isbn" required>
            <option value="" disabled>Elegí un libro…</option>
            <option v-for="l in libros" :key="l.isbn" :value="l.isbn">{{ l.titulo }} — {{ l.autor }}</option>
          </select>
        </label>
        <label class="field">
          <span>Sede a la que pertenece *</span>
          <select v-model="nuevoEjemplar.sede_id" required>
            <option value="" disabled>Elegí una sede…</option>
            <option v-for="s in sedesActivas" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </label>
        <label class="field">
          <span>Código de inventario</span>
          <input v-model="nuevoEjemplar.codigo_inventario" placeholder="Se genera automáticamente si se deja vacío" />
        </label>
        <div class="form-actions">
          <button type="button" class="btn" @click="nuevoEjemplar = null">Cancelar</button>
          <button class="btn btn-primary">Registrar</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog v-if="trasladando" titulo="Trasladar ejemplar a otra sede" @cerrar="trasladando = null">
      <form class="form" @submit.prevent="confirmarTraslado">
        <p class="alert">
          Se generará un remito de <strong>traslado</strong> para {{ trasladando.codigo_inventario }}
          («{{ trasladando.titulo }}»). Al recibirse, el ejemplar pasará a pertenecer a la sede destino.
        </p>
        <label class="field">
          <span>Sede destino *</span>
          <select v-model="sedeTraslado" required>
            <option value="" disabled>Elegí una sede…</option>
            <option v-for="s in sedesActivas.filter((x) => x.id !== trasladando.sede_id)" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </label>
        <div class="form-actions">
          <button type="button" class="btn" @click="trasladando = null">Cancelar</button>
          <button class="btn btn-primary">Generar remito</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>
