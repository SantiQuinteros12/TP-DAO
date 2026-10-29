<script setup>
/**
 * Línea de tiempo con el historial de estados del remito (trazabilidad),
 * con estilo de seguimiento de envío. Recibe el historial del más reciente
 * al más antiguo: el primer movimiento es el estado actual y se destaca.
 */
import { AlertTriangle, CalendarClock, MapPin, PackageCheck, User } from 'lucide-vue-next'
import EstadoBadge from './EstadoBadge.vue'
import { etiqueta, fechaHora } from '../composables/formato'

defineProps({ historial: { type: Array, required: true } })

const FINALES = ['RECIBIDO', 'EXTRAVIADO', 'CANCELADO']
</script>

<template>
  <ol class="timeline">
    <li
      v-for="(m, i) in historial"
      :key="i"
      :class="{
        incidencia: m.tipo_incidencia,
        actual: i === 0,
        enCurso: i === 0 && !FINALES.includes(m.estado),
        perdida: m.estado === 'EXTRAVIADO',
        completado: m.estado === 'RECIBIDO',
        ultimo: i === historial.length - 1
      }"
    >
      <span class="punto" aria-hidden="true">
        <AlertTriangle v-if="m.tipo_incidencia" :size="12" :stroke-width="2.6" />
      </span>
      <div class="cuerpo">
        <div class="linea">
          <EstadoBadge :estado="m.estado" />
          <span v-if="i === 0" class="etiqueta-actual">Estado actual</span>
          <time class="fecha"><CalendarClock :size="14" aria-hidden="true" /> {{ fechaHora(m.fecha_hora) }}</time>
        </div>
        <p v-if="m.tipo_incidencia" class="aviso-incidencia">
          <AlertTriangle :size="15" aria-hidden="true" /> Incidencia: {{ etiqueta(m.tipo_incidencia) }}
        </p>
        <p v-if="m.observacion" class="observacion">{{ m.observacion }}</p>
        <ul v-if="m.ubicacion || m.responsable || m.condicion" class="metadatos">
          <li v-if="m.ubicacion"><MapPin :size="14" aria-hidden="true" /><span class="sr">Ubicación:</span> {{ m.ubicacion }}</li>
          <li v-if="m.responsable"><User :size="14" aria-hidden="true" /><span class="sr">Responsable:</span> {{ m.responsable }}</li>
          <li v-if="m.condicion"><PackageCheck :size="14" aria-hidden="true" /> Estado físico: {{ etiqueta(m.condicion) }}</li>
        </ul>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.timeline { list-style: none; margin: 0; padding: 0; }
.timeline > li {
  --punto: var(--accent); --linea: var(--accent-soft-2);
  position: relative; display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: var(--space-3);
  padding-bottom: var(--space-5);
}
/* Conector vertical entre puntos */
.timeline > li::before {
  content: ''; position: absolute; left: 13px; top: 22px; bottom: -2px;
  width: 2px; border-radius: 2px; background: var(--linea);
}
.timeline > li.ultimo { padding-bottom: 0; }
.timeline > li.ultimo::before { display: none; }

.punto {
  position: relative; z-index: 1; display: grid; place-items: center;
  width: 14px; height: 14px; margin: 5px 0 0 7px; border-radius: 50%;
  background: var(--surface); border: 3px solid var(--punto); color: #fff;
}
.timeline > li.incidencia { --punto: var(--warning); }
.timeline > li.incidencia .punto { width: 22px; height: 22px; margin: 1px 0 0 3px; border: 0; background: var(--warning); color: #3b2600; }
.timeline > li.perdida { --punto: var(--critical); }
.timeline > li.completado { --punto: var(--good); }

/* Estado actual: punto lleno con halo */
.timeline > li.actual .punto {
  width: 20px; height: 20px; margin: 2px 0 0 4px; border: 0; background: var(--punto);
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--punto) 22%, transparent);
}
.timeline > li.actual.incidencia .punto { width: 22px; height: 22px; margin: 1px 0 0 3px; }
.timeline > li.enCurso .punto { animation: latido 2s var(--ease) infinite; }

.cuerpo {
  display: grid; gap: 6px; min-width: 0; padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface);
}
.timeline > li.actual .cuerpo { border-color: color-mix(in srgb, var(--punto) 45%, var(--border)); background: color-mix(in srgb, var(--punto) 6%, var(--surface)); }
.timeline > li.incidencia .cuerpo { border-color: color-mix(in srgb, var(--warning) 50%, var(--border)); background: var(--warning-bg); }

.linea { display: flex; gap: var(--space-2) var(--space-3); align-items: center; flex-wrap: wrap; }
.etiqueta-actual {
  font-size: var(--text-xs); font-weight: 650; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent);
}
.fecha {
  display: inline-flex; align-items: center; gap: 5px; margin-left: auto;
  font-size: var(--text-sm); font-weight: 550; color: var(--ink-2); font-variant-numeric: tabular-nums;
}
.fecha svg { color: var(--muted); }
.aviso-incidencia {
  display: flex; align-items: center; gap: 6px; margin: 0;
  font-size: 14px; font-weight: 650; color: var(--warning-ink);
}
.observacion { margin: 0; font-size: 14px; color: var(--ink); }
.metadatos {
  display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-4); margin: 0; padding: 0; list-style: none;
  font-size: var(--text-sm); color: var(--ink-2);
}
.metadatos li { display: inline-flex; align-items: center; gap: 5px; }
.metadatos svg { color: var(--muted); flex: none; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

@keyframes latido {
  0%, 100% { box-shadow: 0 0 0 5px color-mix(in srgb, var(--punto) 22%, transparent); }
  50% { box-shadow: 0 0 0 8px color-mix(in srgb, var(--punto) 8%, transparent); }
}
</style>
