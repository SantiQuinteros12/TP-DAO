/**
 * Validación de formularios del lado del cliente.
 *
 * Replica las reglas de formato del backend (domain/validaciones.py) para
 * avisar mientras se completa el formulario. El backend vuelve a validar
 * todo: estas reglas sólo mejoran la experiencia.
 */
import { computed, reactive, ref, unref } from 'vue'

const LETRAS = 'A-Za-zÁÉÍÓÚÜÑáéíóúüñ'
const NOMBRE = new RegExp(`^[${LETRAS}]+(?:[ '\\-][${LETRAS}]+)*$`)
const AUTOR = new RegExp(`^[${LETRAS}.,' \\-]+$`)
const EMAIL = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/
const TELEFONO = /^\+?[\d\s()-]+$/
const vacio = (v) => v === null || v === undefined || String(v).trim() === ''

// --- reglas: (valor, form) => mensaje de error | '' ------------------------
export const r = {
  requerido: (campo = 'Este campo') => (v) => (vacio(v) ? `${campo} es obligatorio` : ''),
  minimo: (n) => (v) => (!vacio(v) && String(v).trim().length < n ? `Mínimo ${n} caracteres` : ''),
  maximo: (n) => (v) => (!vacio(v) && String(v).trim().length > n ? `Máximo ${n} caracteres` : ''),
  nombre: () => (v) => {
    if (vacio(v)) return ''
    const t = String(v).trim().replace(/\s+/g, ' ')
    if (/\d/.test(t)) return 'No puede contener números'
    if (!NOMBRE.test(t)) return 'Sólo letras, espacios, apóstrofos o guiones'
    return t.length < 2 ? 'Mínimo 2 letras' : ''
  },
  autor: () => (v) => (!vacio(v) && !AUTOR.test(String(v).trim()) ? 'Sólo letras, espacios, puntos, comas o guiones' : ''),
  email: () => (v) => (!vacio(v) && !EMAIL.test(String(v).trim()) ? 'Formato de email inválido (ej. nombre@dominio.com)' : ''),
  telefono: () => (v) => {
    if (vacio(v)) return ''
    const t = String(v).trim()
    if (/[A-Za-z]/.test(t)) return 'El teléfono no puede contener letras'
    if (!TELEFONO.test(t) || (t.match(/\+/g) ?? []).length > 1) return 'Sólo números, espacios, guiones, paréntesis y un "+" inicial'
    const digitos = t.replace(/\D/g, '').length
    return digitos < 7 || digitos > 15 ? 'Debe tener entre 7 y 15 dígitos' : ''
  },
  dni: () => (v) => (!vacio(v) && !/^\d{7,8}$/.test(String(v).replace(/[.\s]/g, '')) ? 'El DNI debe tener 7 u 8 dígitos' : ''),
  isbn: () => (v) => (!vacio(v) && !isbnValido(v) ? 'ISBN inválido (revisá los dígitos)' : ''),
  anio: () => (v) => {
    if (vacio(v)) return ''
    const max = new Date().getFullYear()
    return !Number.isInteger(Number(v)) || v < 1000 || v > max ? `Año entre 1000 y ${max}` : ''
  },
  altura: () => (v) => (!vacio(v) && !/^(\d{1,5}|S\/N)$/i.test(String(v).trim()) ? 'Número de hasta 5 dígitos o S/N' : ''),
  codigoPostal: () => (v) => (!vacio(v) && !/^[A-Za-z]?\d{4}([A-Za-z]{3})?$/.test(String(v).trim()) ? '4 dígitos (5000) o CPA (X5000ABC)' : ''),
  conLetras: () => (v) => (!vacio(v) && !/[A-Za-zÁÉÍÓÚÑáéíóúñ]/.test(v) ? 'Debe contener letras' : '')
}

/** Verifica el dígito de control de un ISBN-10 o ISBN-13. */
export function isbnValido(valor) {
  const isbn = String(valor ?? '').replace(/[-\s]/g, '').toUpperCase()
  if (/^\d{9}[\dX]$/.test(isbn)) {
    const total = [...isbn].reduce((s, c, i) => s + (10 - i) * (c === 'X' ? 10 : Number(c)), 0)
    return total % 11 === 0
  }
  if (/^\d{13}$/.test(isbn)) {
    const total = [...isbn].reduce((s, c, i) => s + Number(c) * (i % 2 ? 3 : 1), 0)
    return total % 10 === 0
  }
  return false
}

/**
 * Estado de validación de un formulario.
 *
 * @param form objeto reactivo con los valores
 * @param reglas { campo: [regla, ...] } (puede ser ref/computed)
 * Los errores de un campo se muestran después de salir de él o al intentar
 * enviar el formulario.
 */
export function useValidacion(form, reglas) {
  const tocados = reactive({})
  const intentado = ref(false)

  const errores = computed(() => {
    const resultado = {}
    const f = unref(form)
    for (const [campo, lista] of Object.entries(unref(reglas))) {
      for (const regla of lista) {
        const mensaje = regla(f?.[campo], f)
        if (mensaje) {
          resultado[campo] = mensaje
          break
        }
      }
    }
    return resultado
  })

  return {
    errores,
    valido: computed(() => !Object.keys(errores.value).length),
    error: (campo) => (intentado.value || tocados[campo] ? errores.value[campo] ?? '' : ''),
    tocar: (campo) => { tocados[campo] = true },
    /** Marca el intento de envío; devuelve true si se puede enviar. */
    validar: () => {
      intentado.value = true
      return !Object.keys(errores.value).length
    },
    reiniciar: () => {
      intentado.value = false
      for (const k of Object.keys(tocados)) delete tocados[k]
    }
  }
}

// --- directiva v-filtro: impide tipear caracteres no permitidos ------------
const FILTROS = {
  telefono: /[^\d\s()+-]/g,
  nombre: new RegExp(`[^${LETRAS}' -]`, 'g'),
  autor: new RegExp(`[^${LETRAS}.,' -]`, 'g'),
  digitos: /\D/g,
  dni: /[^\d.]/g,
  isbn: /[^\dXx\s-]/g,
  altura: /[^\dSsNn/]/g
}

export const vFiltro = {
  mounted(el, { value }) {
    const patron = FILTROS[value]
    if (!patron) return
    el.addEventListener('input', () => {
      const limpio = el.value.replace(patron, '')
      if (limpio !== el.value) {
        el.value = limpio
        el.dispatchEvent(new Event('input'))
      }
    })
  }
}
