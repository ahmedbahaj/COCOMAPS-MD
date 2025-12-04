import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import HighchartsVue from 'highcharts-vue'
import Highcharts from 'highcharts'
import SankeyModule from 'highcharts/modules/sankey'
import DependencyWheelModule from 'highcharts/modules/dependency-wheel'
import ArcDiagramModule from 'highcharts/modules/arc-diagram'
import HeatmapModule from 'highcharts/modules/heatmap'
import XRangeModule from 'highcharts/modules/xrange'
import ExportingModule from 'highcharts/modules/exporting'

// Initialize Highcharts modules
SankeyModule(Highcharts)
DependencyWheelModule(Highcharts)
ArcDiagramModule(Highcharts)
HeatmapModule(Highcharts)
XRangeModule(Highcharts)
ExportingModule(Highcharts)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(HighchartsVue)

app.mount('#app')

