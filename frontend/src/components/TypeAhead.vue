<script setup>
/**
 * Búsqueda predictiva (type-ahead) accesible para listas extensas.
 *
 * - `buscar(texto)` devuelve (o resuelve) los candidatos; se invoca con
 *   espera de 250 ms mientras se tipea.
 * - `v-model` guarda la clave del elemento elegido; `seleccionado` recibe
 *   el objeto completo para mostrar su texto (p. ej. al precargar).
 * Teclado: ↑/↓ para moverse, Enter para elegir, Esc para cerrar.
 */
import { computed, ref, watch } from 'vue'
import { LoaderCircle, Search, X } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: [String, Number], default: null },
  buscar: { type: Function, required: true },
  textoDe: { type: Function, required: true },
  detalleDe: { type: Function, default: null },
  claveDe: { type: Function, default: (item) => item.id },
  seleccionado: { type: Object, default: null },
  placeholder: { type: String, default: 'Escribí para buscar…' },
  minimo: { type: Number, default: 1 },
  limite: { type: Number, default: 8 },
  deshabilitado: { type: Boolean, default: false },
  invalido: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'elegir'])

const id = `ta-${Math.random().toString(36).slice(2, 8)}`
const texto = ref(props.seleccionado ? props.textoDe(props.seleccionado) : '')
const resultados = ref([])
const abierto = ref(false)
const activo = ref(-1)
const cargando = ref(false)
const elegido = ref(props.seleccionado)

watch(() => props.seleccionado, (item) => {
  elegido.value = item
  texto.value = item ? props.textoDe(item) : ''
})
watch(() => props.modelValue, (valor) => {
  if (valor === null || valor === '' || valor === undefined) {
    elegido.value = null
    texto.value = ''
  }
})

let espera
let consulta = 0
async function consultar() {
  const n = ++consulta
  cargando.value = true
  try {
    const items = (await props.buscar(texto.value.trim())) ?? []
    if (n !== consulta) return
    resultados.value = items.slice(0, props.limite)
    activo.value = resultados.value.length ? 0 : -1
    abierto.value = true
  } finally {
    if (n === consulta) cargando.value = false
  }
}

function alEscribir() {
  if (elegido.value) {
    elegido.value = null
    emit('update:modelValue', null)
    emit('elegir', null)
  }
  clearTimeout(espera)
  if (texto.value.trim().length < props.minimo) {
    abierto.value = false
    resultados.value = []
    return
  }
  espera = setTimeout(consultar, 250)
}

function elegir(item) {
  elegido.value = item
  texto.value = props.textoDe(item)
  abierto.value = false
  emit('update:modelValue', props.claveDe(item))
  emit('elegir', item)
}

function limpiar() {
  texto.value = ''
  alEscribir()
}

function teclado(e) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    if (!abierto.value) {
      if (texto.value.trim().length >= props.minimo) consultar()
      return
    }
    const n = resultados.value.length
    if (n) activo.value = (activo.value + (e.key === 'ArrowDown' ? 1 : n - 1)) % n
  } else if (e.key === 'Enter' && abierto.value) {
    e.preventDefault()
    const item = resultados.value[activo.value]
    if (item) elegir(item)
  } else if (e.key === 'Escape' && abierto.value) {
    e.stopPropagation()
    abierto.value = false
  }
}

function alEnfocar() {
  if (texto.value && !elegido.value && texto.value.trim().length >= props.minimo) consultar()
}

const sinResultados = computed(() => abierto.value && !cargando.value && !resultados.value.length)

/** Divide el texto en [antes, coincidencia, después] para resaltarlo. */
function partes(cadena) {
  const q = texto.value.trim()
  const i = q && !elegido.value ? cadena.toLowerCase().indexOf(q.toLowerCase()) : -1
  return i < 0 ? [cadena, '', ''] : [cadena.slice(0, i), cadena.slice(i, i + q.length), cadena.slice(i + q.length)]
}
</script>

<template>
  <div class="typeahead" :class="{ 'con-valor': elegido }">
    <Search class="lupa" :size="16" aria-hidden="true" />
    <input
      v-model="texto"
      type="text"
      role="combobox"
      autocomplete="off"
      :placeholder="placeholder"
      :disabled="deshabilitado"
      :aria-expanded="abierto"
      :aria-controls="`${id}-lista`"
      :aria-activedescendant="activo >= 0 ? `${id}-${activo}` : undefined"
      :aria-invalid="invalido || undefined"
      @input="alEscribir"
      @keydown="teclado"
      @focus="alEnfocar"
      @blur="abierto = false"
    />
    <LoaderCircle v-if="cargando" class="estado girando" :size="16" aria-hidden="true" />
    <button v-else-if="texto && !deshabilitado" type="button" class="estado limpiar" aria-label="Borrar búsqueda" @mousedown.prevent="limpiar"><X :size="15" /></button>
    <ul v-if="abierto" :id="`${id}-lista`" class="opciones" role="listbox">
      <li
        v-for="(item, i) in resultados"
        :id="`${id}-${i}`"
        :key="claveDe(item)"
        role="option"
        :aria-selected="i === activo"
        :class="{ activo: i === activo }"
        @mousedown.prevent="elegir(item)"
        @mousemove="activo = i"
      >
        <span class="texto">{{ partes(textoDe(item))[0] }}<mark>{{ partes(textoDe(item))[1] }}</mark>{{ partes(textoDe(item))[2] }}</span>
        <span v-if="detalleDe" class="detalle">{{ detalleDe(item) }}</span>
      </li>
      <li v-if="sinResultados" class="vacio">Sin coincidencias para «{{ texto }}»</li>
    </ul>
  </div>
</template>

<style scoped>
.typeahead { position: relative; }
.typeahead input { padding-left: 36px; padding-right: 36px; }
.lupa {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  color: var(--muted); pointer-events: none;
}
.con-valor input { border-color: var(--accent); background: var(--accent-soft); font-weight: 550; }
.con-valor .lupa { color: var(--accent); }
.estado {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  display: grid; place-items: center; color: var(--muted);
}
.limpiar {
  width: 26px; height: 26px; border: 0; border-radius: var(--radius-sm); background: none; cursor: pointer;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease);
}
.limpiar:hover { background: var(--surface-3); color: var(--ink); }
.girando { animation: girar 0.8s linear infinite; }
@keyframes girar { to { transform: translateY(-50%) rotate(360deg); } }
.opciones {
  position: absolute; z-index: 60; left: 0; right: 0; top: calc(100% + 6px);
  margin: 0; padding: var(--space-1); list-style: none; max-height: 300px; overflow-y: auto;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow-lg); animation: desplegar 140ms var(--ease);
}
.opciones li { display: grid; gap: 2px; padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm); cursor: pointer; }
.opciones li.activo { background: var(--accent-soft); }
.texto { font-size: 14.5px; font-weight: 500; color: var(--ink); }
.detalle { font-size: var(--text-sm); color: var(--muted); }
mark {
  background: none; color: inherit; font-weight: 700;
  text-decoration: underline; text-decoration-color: var(--accent); text-decoration-thickness: 2px; text-underline-offset: 2px;
}
.vacio { color: var(--muted); cursor: default; font-size: 14px; }
@keyframes desplegar { from { opacity: 0; transform: translateY(-4px); } }
</style>
