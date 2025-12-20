import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import HighchartsVue from 'highcharts-vue'
import Highcharts from 'highcharts'
import SankeyModule from 'highcharts/modules/sankey'
import DependencyWheelModule from 'highcharts/modules/dependency-wheel'
import HeatmapModule from 'highcharts/modules/heatmap'
import ExportingModule from 'highcharts/modules/exporting'

// Initialize Highcharts modules
SankeyModule(Highcharts)
DependencyWheelModule(Highcharts)
HeatmapModule(Highcharts)
ExportingModule(Highcharts)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(HighchartsVue)

app.mount('#app')

