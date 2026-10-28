/**
 * Horario de atención como lista de franjas { dias: [0..6], desde, hasta }
 * (0 = lunes). Mismo modelo y reglas que el Value Object Horario del backend.
 */

export const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
export const DIAS_INICIAL = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

/** Horas cada 30 minutos entre 06:00 y 23:30. */
export const HORAS = Array.from({ length: 36 }, (_, i) => {
  const minutos = 6 * 60 + i * 30
  return `${String(Math.floor(minutos / 60)).padStart(2, '0')}:${String(minutos % 60).padStart(2, '0')}`
})

const franja = (desdeDia, hastaDia, desde, hasta) => ({
  dias: Array.from({ length: hastaDia - desdeDia + 1 }, (_, i) => desdeDia + i), desde, hasta
})

export const PRESETS = [
  { nombre: 'Lun a Vie 8 a 20', franjas: [franja(0, 4, '08:00', '20:00')] },
  { nombre: 'Lun a Vie 9 a 18', franjas: [franja(0, 4, '09:00', '18:00')] },
  { nombre: 'Lun a Vie + Sáb mañana', franjas: [franja(0, 4, '08:00', '20:00'), franja(5, 5, '09:00', '13:00')] },
  { nombre: 'Horario cortado', franjas: [franja(0, 4, '08:00', '13:00'), franja(0, 4, '16:00', '20:00')] },
  { nombre: 'Sin atención', franjas: [] }
]

function textoDias(dias) {
  const d = [...dias].sort((a, b) => a - b)
  const corrido = d.length > 2 && d.every((x, i) => i === 0 || x === d[i - 1] + 1)
  if (corrido) return `${DIAS[d[0]]} a ${DIAS[d.at(-1)]}`
  const nombres = d.map((i) => DIAS[i])
  return nombres.length === 1 ? nombres[0] : `${nombres.slice(0, -1).join(', ')} y ${nombres.at(-1)}`
}

export function textoHorario(franjas = []) {
  if (!franjas.length) return 'Sin atención al público'
  return [...franjas]
    .filter((f) => f.dias.length)
    .sort((a, b) => Math.min(...a.dias) - Math.min(...b.dias) || a.desde.localeCompare(b.desde))
    .map((f) => `${textoDias(f.dias)} ${f.desde} a ${f.hasta}`)
    .join(' · ')
}

/** Devuelve el primer problema del horario o '' si es válido. */
export function errorHorario(franjas = []) {
  for (const [i, f] of franjas.entries()) {
    if (!f.dias.length) return `Elegí al menos un día en la franja ${i + 1}`
    if (f.desde >= f.hasta) return `En la franja ${i + 1} la apertura debe ser anterior al cierre`
  }
  for (let i = 0; i < franjas.length; i++) {
    for (let j = i + 1; j < franjas.length; j++) {
      const a = franjas[i]
      const b = franjas[j]
      const comun = a.dias.find((d) => b.dias.includes(d))
      if (comun !== undefined && a.desde < b.hasta && b.desde < a.hasta) {
        return `Las franjas ${i + 1} y ${j + 1} se superponen el ${DIAS[comun]}`
      }
    }
  }
  return ''
}

export const copiarFranjas = (franjas = []) => franjas.map((f) => ({ ...f, dias: [...f.dias] }))
