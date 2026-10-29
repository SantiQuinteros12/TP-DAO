<script setup>
/**
 * Catálogo de libros. Cada libro se despliega (acordeón) mostrando sus
 * totales por estado y la disponibilidad por sede; cada sede se despliega a
 * su vez con el detalle de sus ejemplares físicos.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import CampoForm from '../components/CampoForm.vue'
import EstadoBadge from '../components/EstadoBadge.vue'
import ModalDialog from '../components/ModalDialog.vue'
import TypeAhead from '../components/TypeAhead.vue'
import { buscar, catalogoApi, sedesApi } from '../services/api'
import { ejecutar } from '../composables/useToast'
import { etiqueta } from '../composables/formato'
import { r, useValidacion } from '../composables/validacion'

const router = useRouter()
const sedes = ref([])
const sedesActivas = computed(() => sedes.value.filter((s) => s.activa))

/** Estados que se totalizan, en orden de prioridad para el estado del libro. */
const ESTADOS = [
  { clave: 'disponibles', estado: 'DISPONIBLE', nombre: 'Disponible', tono: 'good', icono: '●' },
  { clave: 'prestados', estado: 'EN_PRESTAMO', nombre: 'Prestado', tono: 'info', icono: '◆' },
  { clave: 'reservados', estado: 'RESERVADO', nombre: 'Reservado', tono: 'warning', icono: '▲' },
  { clave: 'en_transito', estado: 'EN_TRANSITO', nombre: 'En tránsito', tono: 'info', icono: '➜' },
  { clave: 'danados', estado: 'DANADO', nombre: 'Dañado', tono: 'serious', icono: '◼' }
]
const ESTADO_POR_CODIGO = Object.fromEntries(ESTADOS.map((e) => [e.estado, e]))

// --- libros + conteos -------------------------------------------------------
const libros = ref([])
const disponibilidad = ref([])
const q = ref('')
const filtroEstado = ref('')

async function cargar() {
  const [l, d] = await Promise.all([
    ejecutar(() => catalogoApi.listarLibros(q.value)),
    ejecutar(() => catalogoApi.disponibilidad({ q: q.value }))
  ])
  libros.value = l ?? []
  disponibilidad.value = d ?? []
}

const cero = () => Object.fromEntries(ESTADOS.map((e) => [e.clave, 0]))

/** Conteos por estado de cada libro (sumando todas sus sedes). */
const conteos = computed(() => {
  const m = new Map()
  for (const f of disponibilidad.value) {
    const c = m.get(f.isbn) ?? { ...cero(), total: 0, en_espera: 0 }
    for (const e of ESTADOS) c[e.clave] += f[e.clave] ?? 0
    c.total += f.total
    c.en_espera += f.reservas_en_espera ?? 0
    m.set(f.isbn, c)
  }
  return m
})
const conteoDe = (isbn) => conteos.value.get(isbn) ?? { ...cero(), total: 0, en_espera: 0 }

/** Estado actual del libro: el primero de la lista con ejemplares. */
function estadoLibro(isbn) {
  const c = conteoDe(isbn)
  return ESTADOS.find((e) => c[e.clave] > 0) ?? null
}

const visibles = computed(() =>
  filtroEstado.value ? libros.value.filter((l) => conteoDe(l.isbn)[filtroEstado.value] > 0) : libros.value
)

const totales = computed(() => {
  const t = cero()
  for (const l of libros.value) for (const e of ESTADOS) t[e.clave] += conteoDe(l.isbn)[e.clave]
  return t
})

// --- acordeón ---------------------------------------------------------------
const abierto = ref(null) // isbn del libro desplegado
const ejemplares = ref([])
const sedesAbiertas = reactive(new Set())

async function alternar(libro) {
  if (abierto.value === libro.isbn) {
    abierto.value = null
    return
  }
  abierto.value = libro.isbn
  sedesAbiertas.clear()
  ejemplares.value = []
  await cargarEjemplares()
}

async function cargarEjemplares() {
  const isbn = abierto.value
  const lista = (await ejecutar(() => catalogoApi.listarEjemplares({ isbn }))) ?? []
  if (abierto.value === isbn) ejemplares.value = lista
}

/** Ejemplares del libro abierto agrupados por sede propietaria. */
const porSede = computed(() => {
  const grupos = new Map()
  for (const e of ejemplares.value) {
    if (!grupos.has(e.sede_id)) {
      const sede = sedes.value.find((s) => s.id === e.sede_id)
      grupos.set(e.sede_id, { sede_id: e.sede_id, sede: e.sede, activa: sede?.activa ?? true, ejemplares: [], conteo: cero(), bajas: 0 })
    }
    const g = grupos.get(e.sede_id)
    g.ejemplares.push(e)
    const est = ESTADO_POR_CODIGO[e.estado]
    if (est) g.conteo[est.clave]++
    else g.bajas++
  }
  return [...grupos.values()].sort((a, b) => a.sede.localeCompare(b.sede))
})

const alternarSede = (id) => (sedesAbiertas.has(id) ? sedesAbiertas.delete(id) : sedesAbiertas.add(id))
const enUso = (g) => ESTADOS.reduce((s, e) => s + g.conteo[e.clave], 0)

// --- libro (alta/edición) ---------------------------------------------------
const libroEditando = ref(null)
const formLibro = reactive({ isbn: '', titulo: '', autor: '', editorial: '', anio_publicacion: null, genero: '' })
const vLibro = useValidacion(formLibro, {
  isbn: [r.requerido('El ISBN'), r.isbn()],
  titulo: [r.requerido('El título'), r.maximo(200)],
  autor: [r.requerido('El autor'), r.autor(), r.maximo(120)],
  editorial: [r.maximo(80)],
  anio_publicacion: [r.anio()],
  genero: [r.nombre(), r.maximo(60)]
})

/**
 * Géneros del catálogo completo (no sólo de los libros filtrados por la
 * búsqueda). Se elige con un desplegable que siempre muestra todas las
 * opciones; "Otro…" habilita escribir un género nuevo.
 */
const OTRO_GENERO = '__otro__'
const generosCatalogo = ref([])
const generoElegido = ref('')
const generos = computed(() => {
  const lista = new Set(generosCatalogo.value)
  if (formLibro.genero && generoElegido.value !== OTRO_GENERO) lista.add(formLibro.genero)
  return [...lista].sort((a, b) => a.localeCompare(b, 'es'))
})

async function cargarGeneros() {
  const todos = (await ejecutar(() => catalogoApi.listarLibros(''))) ?? []
  generosCatalogo.value = [...new Set(todos.map((l) => l.genero).filter(Boolean))]
}

function elegirGenero() {
  formLibro.genero = generoElegido.value === OTRO_GENERO ? '' : generoElegido.value
}

function abrirLibro(libro = {}) {
  const { isbn = '', titulo = '', autor = '', editorial = '', anio_publicacion = null, genero = '' } = libro
  Object.assign(formLibro, { isbn, titulo, autor, editorial, anio_publicacion, genero: genero ?? '' })
  generoElegido.value = formLibro.genero
  vLibro.reiniciar()
  libroEditando.value = libro
  cargarGeneros()
}

async function guardarLibro() {
  if (!vLibro.validar()) return
  const { isbn, ...datos } = formLibro
  datos.anio_publicacion = datos.anio_publicacion || null
  const ok = libroEditando.value.isbn
    ? await ejecutar(() => catalogoApi.actualizarLibro(isbn, datos), 'Libro actualizado')
    : await ejecutar(() => catalogoApi.crearLibro({ isbn, ...datos }), 'Libro agregado al catálogo')
  if (ok) {
    libroEditando.value = null
    cargar()
  }
}

// --- ejemplares (alta, traslado, reparación, baja) -------------------------
const nuevoEjemplar = ref(null)
const formEjemplar = reactive({ isbn: null, sede_id: '', codigo_inventario: '' })
const vEjemplar = useValidacion(formEjemplar, {
  isbn: [r.requerido('El libro')],
  sede_id: [r.requerido('La sede')],
  codigo_inventario: [(c) => (c && !/^[A-Za-z0-9-]{3,30}$/.test(c) ? 'Letras, números y guiones (3 a 30)' : '')]
})

function abrirEjemplar(libro = null) {
  Object.assign(formEjemplar, { isbn: libro?.isbn ?? null, sede_id: '', codigo_inventario: '' })
  vEjemplar.reiniciar()
  nuevoEjemplar.value = { libro }
}

async function crearEjemplar() {
  if (!vEjemplar.validar()) return
  const { isbn, sede_id, codigo_inventario } = formEjemplar
  const ok = await ejecutar(
    () => catalogoApi.crearEjemplar({ isbn, sede_id, codigo_inventario: codigo_inventario || null }),
    'Ejemplar registrado'
  )
  if (ok) {
    nuevoEjemplar.value = null
    refrescar()
  }
}

function refrescar() {
  cargar()
  if (abierto.value) cargarEjemplares()
}

async function accionEjemplar(fn, mensaje) {
  if (await ejecutar(fn, mensaje)) refrescar()
}

const trasladando = ref(null)
const sedeTraslado = ref('')

async function confirmarTraslado() {
  if (!sedeTraslado.value) return
  const remito = await ejecutar(
    () => catalogoApi.trasladarEjemplar(trasladando.value.id, Number(sedeTraslado.value)),
    'Remito de traslado generado'
  )
  if (remito) {
    trasladando.value = null
    router.push({ path: `/remitos/${remito.id}`, query: { volver: '/catalogo' } })
  }
}

// --- carga ------------------------------------------------------------------
let espera
watch(q, () => {
  clearTimeout(espera)
  espera = setTimeout(cargar, 250)
})

onMounted(async () => {
  sedes.value = (await ejecutar(() => sedesApi.listar())) ?? []
  cargar()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <h1>Catálogo de libros</h1>
      <div class="btn-group">
        <button class="btn" @click="abrirEjemplar()">+ Ejemplar</button>
        <button class="btn btn-primary" @click="abrirLibro()">+ Libro</button>
      </div>
    </header>

    <!-- Totalizadores (también filtran) -->
    <div class="totales" role="group" aria-label="Ejemplares por estado">
      <button
        v-for="e in ESTADOS"
        :key="e.clave"
        type="button"
        class="total"
        :class="[e.tono, { activo: filtroEstado === e.clave }]"
        :aria-pressed="filtroEstado === e.clave"
        @click="filtroEstado = filtroEstado === e.clave ? '' : e.clave"
      >
        <span class="total-nombre"><span aria-hidden="true">{{ e.icono }}</span> {{ e.nombre }}</span>
        <strong>{{ totales[e.clave] }}</strong>
        <span class="total-pie">ejemplares</span>
      </button>
    </div>

    <div class="card">
      <div class="toolbar" style="margin-bottom: 12px">
        <div class="grow"><input v-model="q" type="search" placeholder="Buscar por título, autor o ISBN…" /></div>
        <button v-if="filtroEstado" class="btn btn-sm" @click="filtroEstado = ''">
          Con ejemplares «{{ ESTADOS.find((e) => e.clave === filtroEstado).nombre }}» ✕
        </button>
        <span class="small muted">{{ visibles.length }} libros</span>
      </div>

      <div class="table-wrap">
        <table class="libros">
          <thead>
            <tr><th class="col-chevron" /><th>Libro</th><th>ISBN</th><th>Género</th><th>Año</th><th>Estado actual</th><th class="num">Ejemplares</th><th /></tr>
          </thead>
          <tbody>
            <template v-for="l in visibles" :key="l.isbn">
              <tr class="clickable fila-libro" :class="{ selected: abierto === l.isbn }" @click="alternar(l)">
                <td class="col-chevron">
                  <span class="chevron" :class="{ girado: abierto === l.isbn }" aria-hidden="true">›</span>
                </td>
                <td><strong>{{ l.titulo }}</strong><br /><span class="small muted">{{ l.autor }}</span></td>
                <td class="mono">{{ l.isbn }}</td>
                <td class="small">{{ l.genero || '—' }}</td>
                <td class="small">{{ l.anio_publicacion || '—' }}</td>
                <td>
                  <EstadoBadge v-if="estadoLibro(l.isbn)" :estado="estadoLibro(l.isbn).estado" />
                  <span v-else class="small muted">Sin ejemplares</span>
                </td>
                <td class="num">{{ conteoDe(l.isbn).total }}</td>
                <td class="actions" @click.stop>
                  <div class="btn-group" style="justify-content: flex-end">
                    <button class="btn btn-sm" :aria-expanded="abierto === l.isbn" @click="alternar(l)">
                      Ejemplares {{ abierto === l.isbn ? '▴' : '▾' }}
                    </button>
                    <button class="btn btn-sm" @click="abrirLibro(l)">Editar</button>
                  </div>
                </td>
              </tr>

              <!-- Acordeón del libro -->
              <tr v-if="abierto === l.isbn" class="detalle-libro">
                <td colspan="8">
                  <div class="panel-libro">
                    <div class="panel-cabecera">
                      <div class="chips">
                        <span
                          v-for="e in ESTADOS"
                          :key="e.clave"
                          class="chip"
                          :class="[e.tono, { cero: !conteoDe(l.isbn)[e.clave] }]"
                        >
                          <span aria-hidden="true">{{ e.icono }}</span> {{ e.nombre }} <strong>{{ conteoDe(l.isbn)[e.clave] }}</strong>
                        </span>
                        <span v-if="conteoDe(l.isbn).en_espera" class="chip">⏳ Reservas en espera <strong>{{ conteoDe(l.isbn).en_espera }}</strong></span>
                      </div>
                      <button class="btn btn-sm" @click="abrirEjemplar(l)">+ Agregar ejemplar</button>
                    </div>

                    <p v-if="!porSede.length" class="empty">Este libro todavía no tiene ejemplares.</p>

                    <!-- Acordeón de disponibilidad por sede -->
                    <div v-for="g in porSede" :key="g.sede_id" class="sede" :class="{ abierta: sedesAbiertas.has(g.sede_id) }">
                      <button type="button" class="sede-cabecera" :aria-expanded="sedesAbiertas.has(g.sede_id)" @click="alternarSede(g.sede_id)">
                        <span class="chevron" :class="{ girado: sedesAbiertas.has(g.sede_id) }" aria-hidden="true">›</span>
                        <span class="sede-nombre">
                          {{ g.sede }} <span v-if="!g.activa" class="small muted">(baja)</span>
                        </span>
                        <span class="barra" :title="ESTADOS.map((e) => `${e.nombre}: ${g.conteo[e.clave]}`).join(' · ')">
                          <template v-for="e in ESTADOS" :key="e.clave">
                            <span
                              v-if="g.conteo[e.clave]"
                              class="segmento"
                              :class="e.clave"
                              :style="{ flexGrow: g.conteo[e.clave] }"
                            />
                          </template>
                        </span>
                        <span class="conteos">
                          <span v-for="e in ESTADOS" :key="e.clave" :class="{ cero: !g.conteo[e.clave] }" :title="e.nombre">
                            <span aria-hidden="true" :class="['punto', e.clave]" />{{ g.conteo[e.clave] }}
                          </span>
                        </span>
                        <span class="small muted">{{ enUso(g) }} ej.</span>
                      </button>

                      <div v-if="sedesAbiertas.has(g.sede_id)" class="sede-detalle">
                        <table>
                          <thead><tr><th>Código</th><th>Ubicación actual</th><th>Estado</th><th>Condición</th><th /></tr></thead>
                          <tbody>
                            <tr v-for="e in g.ejemplares" :key="e.id">
                              <td class="mono">{{ e.codigo_inventario }}</td>
                              <td class="small" :class="{ muted: e.sede_actual_id === e.sede_id }">{{ e.sede_actual }}</td>
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
                      </div>
                    </div>

                    <ul class="leyenda">
                      <li v-for="e in ESTADOS" :key="e.clave"><span :class="['punto', e.clave]" aria-hidden="true" />{{ e.nombre }}</li>
                    </ul>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <p v-if="!visibles.length" class="empty">Sin resultados.</p>
      </div>
    </div>

    <!-- Modales -->
    <ModalDialog v-if="libroEditando" :titulo="libroEditando.isbn ? 'Editar libro' : 'Nuevo libro'" @cerrar="libroEditando = null">
      <form class="form" novalidate @submit.prevent="guardarLibro">
        <CampoForm etiqueta="ISBN-10 o ISBN-13" requerido :error="vLibro.error('isbn')" @tocar="vLibro.tocar('isbn')">
          <input v-model="formLibro.isbn" v-filtro="'isbn'" :disabled="!!libroEditando.isbn" maxlength="17" placeholder="978-…" />
        </CampoForm>
        <CampoForm etiqueta="Título" requerido :error="vLibro.error('titulo')" @tocar="vLibro.tocar('titulo')">
          <input v-model="formLibro.titulo" maxlength="200" />
        </CampoForm>
        <CampoForm etiqueta="Autor" requerido :error="vLibro.error('autor')" @tocar="vLibro.tocar('autor')">
          <input v-model="formLibro.autor" v-filtro="'autor'" maxlength="120" />
        </CampoForm>
        <div class="form-row">
          <CampoForm etiqueta="Editorial" :error="vLibro.error('editorial')" @tocar="vLibro.tocar('editorial')">
            <input v-model="formLibro.editorial" maxlength="80" />
          </CampoForm>
          <CampoForm etiqueta="Año" :error="vLibro.error('anio_publicacion')" @tocar="vLibro.tocar('anio_publicacion')">
            <input v-model.number="formLibro.anio_publicacion" type="number" min="1000" :max="new Date().getFullYear()" />
          </CampoForm>
          <CampoForm etiqueta="Género" :error="vLibro.error('genero')" @tocar="vLibro.tocar('genero')">
            <select v-model="generoElegido" @change="elegirGenero">
              <option value="">Sin género</option>
              <option v-for="g in generos" :key="g" :value="g">{{ g }}</option>
              <option :value="OTRO_GENERO">Otro (nuevo)…</option>
            </select>
            <input
              v-if="generoElegido === OTRO_GENERO"
              v-model="formLibro.genero"
              v-filtro="'nombre'"
              maxlength="60"
              placeholder="Nombre del nuevo género"
            />
          </CampoForm>
        </div>
        <div class="form-actions">
          <button type="button" class="btn" @click="libroEditando = null">Cancelar</button>
          <button class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog v-if="nuevoEjemplar" titulo="Nuevo ejemplar físico" @cerrar="nuevoEjemplar = null">
      <form class="form" novalidate @submit.prevent="crearEjemplar">
        <CampoForm etiqueta="Libro" requerido :error="vEjemplar.error('isbn')" @tocar="vEjemplar.tocar('isbn')">
          <TypeAhead
            v-model="formEjemplar.isbn"
            :seleccionado="nuevoEjemplar.libro"
            :buscar="buscar.libros"
            :texto-de="(l) => l.titulo"
            :detalle-de="(l) => `${l.autor} · ISBN ${l.isbn}`"
            :clave-de="(l) => l.isbn"
            placeholder="Buscá por título, autor o ISBN…"
          />
        </CampoForm>
        <CampoForm etiqueta="Sede a la que pertenece" requerido :error="vEjemplar.error('sede_id')" @tocar="vEjemplar.tocar('sede_id')">
          <select v-model="formEjemplar.sede_id">
            <option value="" disabled>Elegí una sede…</option>
            <option v-for="s in sedesActivas" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </CampoForm>
        <CampoForm etiqueta="Código de inventario (opcional)" :error="vEjemplar.error('codigo_inventario')" @tocar="vEjemplar.tocar('codigo_inventario')">
          <input v-model="formEjemplar.codigo_inventario" maxlength="30" placeholder="Automático si se deja vacío" />
        </CampoForm>
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
          <span>Sede destino <b class="req">*</b></span>
          <select v-model="sedeTraslado" required>
            <option value="" disabled>Elegí una sede…</option>
            <option v-for="s in sedesActivas.filter((x) => x.id !== trasladando.sede_id)" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </label>
        <div class="form-actions">
          <button type="button" class="btn" @click="trasladando = null">Cancelar</button>
          <button class="btn btn-primary" :disabled="!sedeTraslado">Generar remito</button>
        </div>
      </form>
    </ModalDialog>
  </section>
</template>

<style scoped>
/* Totalizadores */
.totales { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
.total {
  display: grid; gap: 2px; text-align: left; padding: 12px 14px; cursor: pointer;
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--surface); box-shadow: var(--shadow); font: inherit; color: var(--ink);
  border-top: 3px solid var(--tono);
}
.total:hover { background: var(--surface-2); }
.total.activo { outline: 2px solid var(--tono); outline-offset: -1px; background: var(--tono-bg); }
.total strong { font-size: 24px; font-weight: 650; line-height: 1.2; font-variant-numeric: tabular-nums; }
.total-nombre { font-size: 12.5px; color: var(--tono-ink); font-weight: 600; }
.total-pie { font-size: 11.5px; color: var(--muted); }
.good { --tono: var(--good); --tono-ink: var(--good-ink); --tono-bg: var(--good-bg); }
.info { --tono: var(--accent); --tono-ink: var(--info-ink); --tono-bg: var(--info-bg); }
.warning { --tono: var(--warning); --tono-ink: var(--warning-ink); --tono-bg: var(--warning-bg); }
.serious { --tono: var(--serious); --tono-ink: var(--serious-ink); --tono-bg: var(--serious-bg); }

/* Tabla de libros + acordeón */
.col-chevron { width: 28px; padding-right: 0; }
.chevron {
  display: inline-block; font-size: 18px; line-height: 1; color: var(--muted);
  transition: transform 0.15s;
}
.chevron.girado { transform: rotate(90deg); color: var(--accent); }
.detalle-libro > td { padding: 0 0 14px; background: var(--accent-soft); }
.detalle-libro:hover > td { background: var(--accent-soft); }
.panel-libro {
  display: grid; gap: 10px; margin: 0 10px; padding: 14px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
}
.panel-cabecera { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }

.sede { border: 1px solid var(--grid); border-radius: 10px; overflow: hidden; }
.sede.abierta { border-color: var(--axis); }
.sede-cabecera {
  display: grid; grid-template-columns: 18px minmax(130px, 1.2fr) minmax(80px, 1fr) auto auto;
  align-items: center; gap: 12px; width: 100%; padding: 10px 12px;
  border: 0; background: var(--surface); color: var(--ink); font: inherit; text-align: left; cursor: pointer;
}
.sede-cabecera:hover { background: var(--surface-2); }
.sede-nombre { font-weight: 600; }
.barra { display: flex; gap: 2px; height: 10px; border-radius: 999px; overflow: hidden; background: var(--grid); }
.segmento { min-width: 4px; }
.conteos { display: flex; gap: 10px; font-size: 12px; font-variant-numeric: tabular-nums; }
.conteos > span { display: inline-flex; align-items: center; gap: 4px; }
.conteos .cero { opacity: 0.35; }
.punto { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.disponibles { background: var(--good); }
.prestados { background: var(--series-1); }
.reservados { background: var(--warning); }
.en_transito { background: var(--info-ink); }
.danados { background: var(--serious); }
.sede-detalle { padding: 4px 12px 8px; border-top: 1px solid var(--grid); background: var(--surface-2); }
.sede-detalle tbody tr:hover td { background: transparent; }
.leyenda { display: flex; flex-wrap: wrap; gap: 4px 14px; list-style: none; margin: 0; padding: 0; font-size: 12px; color: var(--ink-2); }
.leyenda li { display: inline-flex; align-items: center; gap: 6px; }

@media (max-width: 720px) {
  .sede-cabecera { grid-template-columns: 18px 1fr auto; }
  .barra, .conteos { grid-column: 2 / -1; }
}
</style>
