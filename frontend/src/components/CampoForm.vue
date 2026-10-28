<script setup>
/**
 * Envoltorio de un campo de formulario: etiqueta, marca de obligatorio y
 * mensaje de error. Avisa al salir del campo para mostrar su validación.
 */
defineProps({
  etiqueta: { type: String, required: true },
  error: { type: String, default: '' },
  requerido: { type: Boolean, default: false }
})
defineEmits(['tocar'])
</script>

<template>
  <label class="field" :class="{ invalido: error }" @focusout="$emit('tocar')">
    <span>{{ etiqueta }}<b v-if="requerido" class="req" aria-hidden="true"> *</b></span>
    <slot />
    <small v-if="error" class="error-campo" role="alert">{{ error }}</small>
  </label>
</template>
