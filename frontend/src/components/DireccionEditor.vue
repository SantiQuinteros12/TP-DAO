<script setup>
/**
 * Carga de una dirección postal estructurada (calle, altura, piso, barrio,
 * ciudad, provincia y CP) con vista previa y validación por campo.
 */
import { computed } from 'vue'
import CampoForm from './CampoForm.vue'

const props = defineProps({
  provincias: { type: Array, required: true },
  // Resultado de useValidacion() sobre el mismo objeto de dirección
  validacion: { type: Object, required: true }
})
const dir = defineModel({ type: Object, required: true })
const v = props.validacion

const sinNumero = computed({
  get: () => dir.value.numero === 'S/N',
  set: (marcado) => { dir.value.numero = marcado ? 'S/N' : '' }
})

const vistaPrevia = computed(() => {
  const d = dir.value
  if (!d.calle) return ''
  const partes = [`${d.calle} ${d.numero || ''}`.trim()]
  if (d.piso_depto) partes.push(d.piso_depto)
  if (d.barrio) partes.push(`B° ${d.barrio}`)
  if (d.ciudad) partes.push(d.ciudad === d.provincia ? d.ciudad : [d.ciudad, d.provincia].filter(Boolean).join(', '))
  return partes.join(', ') + (d.codigo_postal ? ` (${d.codigo_postal.toUpperCase()})` : '')
})
</script>

<template>
  <fieldset class="direccion">
    <legend>Dirección</legend>
    <div class="fila calle">
      <CampoForm etiqueta="Calle" requerido :error="v.error('calle')" @tocar="v.tocar('calle')">
        <input v-model="dir.calle" placeholder="Av. Colón" maxlength="80" autocomplete="address-line1" />
      </CampoForm>
      <CampoForm etiqueta="Altura" requerido :error="v.error('numero')" @tocar="v.tocar('numero')">
        <div class="altura">
          <input v-model="dir.numero" v-filtro="'digitos'" inputmode="numeric" maxlength="5" placeholder="1250" :disabled="sinNumero" />
          <label class="sn"><input v-model="sinNumero" type="checkbox" /> S/N</label>
        </div>
      </CampoForm>
    </div>
    <div class="fila">
      <CampoForm etiqueta="Piso / depto." :error="v.error('piso_depto')" @tocar="v.tocar('piso_depto')">
        <input v-model="dir.piso_depto" placeholder="PB, 2° B…" maxlength="20" />
      </CampoForm>
      <CampoForm etiqueta="Barrio" :error="v.error('barrio')" @tocar="v.tocar('barrio')">
        <input v-model="dir.barrio" placeholder="Centro" maxlength="60" />
      </CampoForm>
    </div>
    <div class="fila tres">
      <CampoForm etiqueta="Ciudad" requerido :error="v.error('ciudad')" @tocar="v.tocar('ciudad')">
        <input v-model="dir.ciudad" v-filtro="'nombre'" placeholder="Córdoba" maxlength="60" autocomplete="address-level2" />
      </CampoForm>
      <CampoForm etiqueta="Provincia" requerido :error="v.error('provincia')" @tocar="v.tocar('provincia')">
        <select v-model="dir.provincia">
          <option value="" disabled>Elegí…</option>
          <option v-for="p in provincias" :key="p" :value="p">{{ p }}</option>
        </select>
      </CampoForm>
      <CampoForm etiqueta="Código postal" :error="v.error('codigo_postal')" @tocar="v.tocar('codigo_postal')">
        <input v-model="dir.codigo_postal" placeholder="X5000" maxlength="8" autocomplete="postal-code" />
      </CampoForm>
    </div>
    <p v-if="vistaPrevia" class="vista-previa">
      <span aria-hidden="true">📍</span>
      <span>{{ vistaPrevia }}</span>
    </p>
  </fieldset>
</template>

<style scoped>
.direccion {
  display: grid; gap: 10px; margin: 0; padding: 12px 14px 14px;
  border: 1px solid var(--grid); border-radius: 12px;
}
legend { padding: 0 6px; font-size: 12.5px; font-weight: 600; color: var(--ink-2); }
.fila { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }
.fila.calle { grid-template-columns: minmax(0, 2fr) minmax(130px, 1fr); }
.fila.tres { grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.2fr) minmax(90px, 0.8fr); }
@media (max-width: 520px) { .fila, .fila.calle, .fila.tres { grid-template-columns: 1fr; } }
.altura { display: flex; gap: 8px; align-items: center; }
.sn { display: inline-flex; gap: 4px; align-items: center; font-size: 12px; color: var(--ink-2); white-space: nowrap; }
.sn input { width: auto; }
.vista-previa {
  display: flex; gap: 8px; align-items: center; margin: 2px 0 0; padding: 8px 10px;
  border-radius: 8px; background: var(--surface-2); font-size: 13px;
}
</style>
