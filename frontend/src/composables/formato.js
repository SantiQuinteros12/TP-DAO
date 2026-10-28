/** Utilidades de formato para la UI (es-AR). */

export const fecha = (iso) =>
  iso ? new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString('es-AR') : '—'

export const fechaHora = (iso) =>
  iso
    ? new Date(iso).toLocaleString('es-AR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
      })
    : '—'

export const moneda = (n) =>
  (n ?? 0).toLocaleString('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 })

export const numero = (n, decimales = 0) =>
  n === null || n === undefined ? '—' : Number(n).toLocaleString('es-AR', { maximumFractionDigits: decimales })

/** "EN_TRANSITO" -> "En tránsito" */
const ETIQUETAS = {
  EN_TRANSITO: 'En tránsito', EN_PRESTAMO: 'En préstamo', DANADO: 'Dañado', DANADA: 'Dañada',
  CON_INCIDENCIA: 'Con incidencia', PENDIENTE_ENVIO: 'Pendiente de envío',
  LISTO_PARA_RETIRO: 'Listo para retiro', INTERBIBLIOTECARIO: 'Interbibliotecario',
  DANO: 'Daño', EXTRAVIO: 'Extravío', RETORNO: 'Retorno', ENVIO: 'Envío', TRASLADO: 'Traslado'
}
export const etiqueta = (valor) => {
  if (!valor) return '—'
  if (ETIQUETAS[valor]) return ETIQUETAS[valor]
  const t = valor.toLowerCase().replaceAll('_', ' ')
  return t.charAt(0).toUpperCase() + t.slice(1)
}

/** Nombres legibles de las acciones del remito (patrón State en el backend). */
export const ACCIONES_REMITO = {
  empaquetar: 'Empaquetar',
  despachar: 'Despachar',
  registrar_checkpoint: 'Registrar checkpoint',
  recibir: 'Recibir',
  reportar_incidencia: 'Reportar incidencia',
  resolver_incidencia: 'Resolver incidencia',
  declarar_extravio: 'Declarar extravío',
  cancelar: 'Cancelar'
}
