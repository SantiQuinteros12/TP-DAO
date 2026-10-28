import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { vFiltro } from './composables/validacion'
import './styles.css'

createApp(App).use(router).directive('filtro', vFiltro).mount('#app')
