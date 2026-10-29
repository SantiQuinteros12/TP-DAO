<script setup>
/**
 * Editor visual del horario de atención: plantillas rápidas y franjas con
 * selección de días y horas (sin escribir texto libre).
 */
import { computed } from 'vue'
import { AlertTriangle, Clock, Plus, X } from 'lucide-vue-next'
import { DIAS, DIAS_INICIAL, HORAS, PRESETS, copiarFranjas, errorHorario, textoHorario } from '../composables/horario'

const franjas = defineModel({ type: Array, required: true })

const error = computed(() => errorHorario(franjas.value))
const resumen = computed(() => textoHorario(franjas.value))
const presetActivo = computed(() => PRESETS.find((p) => textoHorario(p.franjas) === resumen.value)?.nombre)

function aplicar(preset) {
  franjas.value = copiarFranjas(preset.franjas)
}

function alternarDia(f, dia) {
  f.dias = f.dias.includes(dia) ? f.dias.filter((d) => d !== dia) : [...f.dias, dia].sort((a, b) => a - b)
}

function agregar() {
  const usados = new Set(franjas.value.flatMap((f) => f.dias))
  const libre = [5, 6, 0, 1, 2, 3, 4].find((d) => !usados.has(d))
  franjas.value = [...franjas.value, { dias: libre === undefined ? [] : [libre], desde: '09:00', hasta: '13:00' }]
}

function quitar(i) {
  franjas.value = franjas.value.filter((_, j) => j !== i)
}
</script>

<template>
  <div class="horario">
    <div class="presets" role="group" aria-label="Plantillas de horario">
      <button
        v-for="p in PRESETS"
        :key="p.nombre"
        type="button"
        class="preset"
        :class="{ activo: presetActivo === p.nombre }"
        @click="aplicar(p)"
      >
        {{ p.nombre }}
      </button>
    </div>

    <div v-for="(f, i) in franjas" :key="i" class="franja">
      <div class="dias" role="group" :aria-label="`Días de la franja ${i + 1}`">
        <button
          v-for="(inicial, d) in DIAS_INICIAL"
          :key="d"
          type="button"
          class="dia"
          :class="{ on: f.dias.includes(d) }"
          :title="DIAS[d]"
          :aria-pressed="f.dias.includes(d)"
          @click="alternarDia(f, d)"
        >
          {{ inicial }}
        </button>
      </div>
      <div class="horas">
        <select v-model="f.desde" aria-label="Apertura">
          <option v-for="h in HORAS" :key="h" :value="h">{{ h }}</option>
        </select>
        <span class="muted">a</span>
        <select v-model="f.hasta" aria-label="Cierre">
          <option v-for="h in HORAS" :key="h" :value="h">{{ h }}</option>
        </select>
      </div>
      <button type="button" class="quitar" :aria-label="`Quitar franja ${i + 1}`" @click="quitar(i)"><X :size="16" /></button>
    </div>

    <button v-if="franjas.length < 7" type="button" class="btn btn-sm agregar" @click="agregar"><Plus aria-hidden="true" /> Agregar franja</button>

    <p class="resumen" :class="{ error: error }">
      <component :is="error ? AlertTriangle : Clock" class="icono-resumen" :size="16" aria-hidden="true" />
      {{ error || resumen }}
    </p>
  </div>
</template>

<style scoped>
.horario { display: grid; gap: var(--space-3); }
.presets { display: flex; flex-wrap: wrap; gap: 6px; }
.preset {
  min-height: 30px; padding: 0 12px; border-radius: var(--radius-pill); border: 1px solid var(--border-strong);
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: var(--text-sm); font-weight: 550; cursor: pointer;
  transition: background var(--dur) var(--ease), border-color var(--dur) var(--ease), color var(--dur) var(--ease);
}
.preset:hover { background: var(--surface-2); }
.preset:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--focus); }
.preset.activo { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.franja {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3);
  padding: var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-2);
}
.dias { display: flex; gap: 4px; flex-wrap: wrap; }
.dia {
  width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--border-strong);
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: var(--text-sm); font-weight: 650; cursor: pointer;
  transition: background var(--dur) var(--ease), border-color var(--dur) var(--ease), color var(--dur) var(--ease);
}
.dia:hover { border-color: var(--accent); }
.dia:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--focus); }
.dia.on { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.horas { display: flex; align-items: center; gap: var(--space-2); }
.horas select { width: auto; min-height: 36px; }
.quitar {
  display: grid; place-items: center; width: 32px; height: 32px; margin-left: auto;
  border: 0; border-radius: var(--radius-sm); background: none; color: var(--muted); cursor: pointer;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease);
}
.quitar:hover { background: var(--critical-bg); color: var(--critical-ink); }
.agregar { width: fit-content; }
.resumen {
  display: flex; align-items: flex-start; gap: var(--space-2);
  margin: 0; padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); font-size: 14px;
  background: var(--info-bg); color: var(--info-ink);
}
.icono-resumen { flex: none; margin-top: 2px; }
.resumen.error { background: var(--critical-bg); color: var(--critical-ink); }
</style>
