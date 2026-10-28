/**
 * Cliente HTTP de la API REST (axios).
 *
 * Cada recurso expone funciones que devuelven directamente el cuerpo JSON.
 * Los errores se normalizan a `Error` con el mensaje de negocio que envía el
 * backend (campo `detail`), listo para mostrarse al usuario.
 */
import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000
})

http.interceptors.response.use(
  (respuesta) => respuesta.data,
  (error) => {
    const detalle = error.response?.data?.detail
    let mensaje = 'No se pudo conectar con el servidor'
    if (typeof detalle === 'string') {
      mensaje = detalle
    } else if (Array.isArray(detalle)) {
      // Errores de validación de FastAPI/Pydantic
      mensaje = detalle
        .map((d) => `${d.loc?.slice(-1)[0] ?? 'dato'}: ${d.msg}`)
        .join(' · ')
    } else if (error.response) {
      mensaje = `Error ${error.response.status}`
    }
    return Promise.reject(new Error(mensaje))
  }
)

/** Quita parámetros vacíos para no enviar `?estado=` en blanco. */
const limpiar = (params = {}) =>
  Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  )

const get = (url, params) => http.get(url, { params: limpiar(params) })

export const sedesApi = {
  listar: (params) => get('/sedes', params),
  provincias: () => http.get('/sedes/provincias'),
  crear: (datos) => http.post('/sedes', datos),
  actualizar: (id, datos) => http.put(`/sedes/${id}`, datos),
  darDeBaja: (id) => http.post(`/sedes/${id}/baja`),
  reactivar: (id) => http.post(`/sedes/${id}/reactivar`)
}

export const sociosApi = {
  listar: (params) => get('/socios', params),
  obtener: (id) => http.get(`/socios/${id}`),
  crear: (datos) => http.post('/socios', datos),
  actualizar: (id, datos) => http.put(`/socios/${id}`, datos),
  inhabilitar: (id, motivo) => http.post(`/socios/${id}/inhabilitar`, { motivo }),
  habilitar: (id) => http.post(`/socios/${id}/habilitar`),
  notificaciones: (id) => get(`/socios/${id}/notificaciones`),
  marcarLeidas: (id) => http.post(`/socios/${id}/notificaciones/leidas`)
}

export const catalogoApi = {
  listarLibros: (q) => get('/libros', { q }),
  crearLibro: (datos) => http.post('/libros', datos),
  actualizarLibro: (isbn, datos) => http.put(`/libros/${isbn}`, datos),
  listarEjemplares: (params) => get('/ejemplares', params),
  crearEjemplar: (datos) => http.post('/ejemplares', datos),
  bajaEjemplar: (id) => http.post(`/ejemplares/${id}/baja`),
  repararEjemplar: (id) => http.post(`/ejemplares/${id}/reparar`),
  trasladarEjemplar: (id, sedeDestinoId) =>
    http.post(`/ejemplares/${id}/traslado`, { sede_destino_id: sedeDestinoId }),
  disponibilidad: (params) => get('/disponibilidad', params)
}

export const prestamosApi = {
  listar: (params) => get('/prestamos', params),
  obtener: (id) => http.get(`/prestamos/${id}`),
  elegibilidad: (socioId) => http.get(`/prestamos/elegibilidad/${socioId}`),
  solicitar: (datos) => http.post('/prestamos', datos),
  entregar: (id) => http.post(`/prestamos/${id}/entregar`),
  devolver: (id, condicion, observaciones) =>
    http.post(`/prestamos/${id}/devolucion`, { condicion, observaciones }),
  cancelar: (id, motivo) => http.post(`/prestamos/${id}/cancelar`, { motivo })
}

export const reservasApi = {
  listar: (params) => get('/reservas', params),
  crear: (datos) => http.post('/reservas', datos),
  cancelar: (id) => http.post(`/reservas/${id}/cancelar`),
  concretar: (id) => http.post(`/reservas/${id}/concretar`),
  procesarVencimientos: () => http.post('/reservas/procesar-vencimientos')
}

export const remitosApi = {
  listar: (params) => get('/remitos', params),
  obtener: (id) => http.get(`/remitos/${id}`),
  operar: (id, accion, datos = {}) => http.post(`/remitos/${id}/acciones/${accion}`, datos)
}

export const reportesApi = {
  resumen: () => http.get('/reportes/resumen'),
  prestamosActivos: () => http.get('/reportes/prestamos-activos'),
  vencidos: () => http.get('/reportes/vencidos'),
  masSolicitados: (params) => get('/reportes/libros-mas-solicitados', params),
  disponibilidadSedes: () => http.get('/reportes/disponibilidad-sedes'),
  logistica: (params) => get('/reportes/logistica', params),
  tendencias: (params) => get('/reportes/tendencias', params)
}

export const recomendacionesApi = {
  paraSocio: (socioId, limite = 8) => get('/recomendaciones', { socio_id: socioId, limite }),
  similares: (isbn, limite = 6) => get(`/recomendaciones/similares/${isbn}`, { limite })
}

/** Buscadores para los componentes type-ahead. */
export const buscar = {
  socios: (q, extra = {}) => sociosApi.listar({ q, ...extra }),
  libros: (q) => catalogoApi.listarLibros(q)
}
