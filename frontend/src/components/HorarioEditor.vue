<script setup>
/**
 * Editor visual del horario de atención: plantillas rápidas y franjas con
 * selección de días y horas (sin escribir texto libre).
 */
import { computed } from 'vue'
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
      <button type="button" class="quitar" :aria-label="`Quitar franja ${i + 1}`" @click="quitar(i)">✕</button>
    </div>

    <button v-if="franjas.length < 7" type="button" class="btn btn-sm agregar" @click="agregar">+ Agregar franja</button>

    <p class="resumen" :class="{ error: error }">
      <span aria-hidden="true">{{ error ? '⚠' : '🕘' }}</span>
      {{ error || resumen }}
    </p>
  </div>
</template>

<style scoped>
.horario { display: grid; gap: 10px; }
.presets { display: flex; flex-wrap: wrap; gap: 6px; }
.preset {
  padding: 4px 11px; border-radius: 999px; border: 1px solid var(--border);
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 12.5px; cursor: pointer;
}
.preset:hover { background: var(--surface-2); }
.preset.activo { background: var(--accent-soft); border-color: var(--accent); color: var(--ink); }
.franja {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 10px; border: 1px solid var(--grid); border-radius: 10px; background: var(--surface-2);
}
.dias { display: flex; gap: 4px; }
.dia {
  width: 30px; height: 30px; border-radius: 50%; border: 1px solid var(--axis);
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
}
.dia.on { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.horas { display: flex; align-items: center; gap: 6px; }
.horas select { width: auto; }
.quitar { margin-left: auto; border: 0; background: none; color: var(--muted); cursor: pointer; font-size: 14px; }
.agregar { width: fit-content; }
.resumen {
  margin: 0; padding: 8px 10px; border-radius: 8px; font-size: 13px;
  background: var(--info-bg); color: var(--info-ink);
}
.resumen.error { background: var(--critical-bg); color: var(--critical-ink); }
</style>
