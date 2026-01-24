import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import HighchartsVue from 'highcharts-vue'
import Highcharts from 'highcharts'
import HeatmapModule from 'highcharts/modules/heatmap'
import ExportingModule from 'highcharts/modules/exporting'

// Initialize Highcharts modules
HeatmapModule(Highcharts)
ExportingModule(Highcharts)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(HighchartsVue)

app.mount('#app')

