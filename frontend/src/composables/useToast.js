/**
 * Notificaciones efímeras (toasts) compartidas por toda la SPA.
 */
import { reactive } from 'vue'

const estado = reactive({ items: [] })
let siguienteId = 1

function mostrar(mensaje, tipo = 'ok', duracion = 4000) {
  const id = siguienteId++
  estado.items.push({ id, mensaje, tipo })
  setTimeout(() => cerrar(id), duracion)
}

function cerrar(id) {
  const i = estado.items.findIndex((t) => t.id === id)
  if (i >= 0) estado.items.splice(i, 1)
}

export function useToast() {
  return {
    toasts: estado.items,
    cerrar,
    exito: (m) => mostrar(m, 'ok'),
    error: (m) => mostrar(m, 'error', 7000)
  }
}

/**
 * Ejecuta una acción asíncrona mostrando el resultado como toast.
 * Devuelve el resultado o `undefined` si falló.
 */
export async function ejecutar(accion, mensajeExito) {
  const toast = useToast()
  try {
    const resultado = await accion()
    if (mensajeExito) toast.exito(mensajeExito)
    return resultado
  } catch (e) {
    toast.error(e.message)
    return undefined
  }
}
