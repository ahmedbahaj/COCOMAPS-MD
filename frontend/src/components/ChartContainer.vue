<template>
  <div id="chartContainer" class="chart-container">
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <div>Loading chart data...</div>
    </div>
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    <div v-else-if="!hasData" class="no-data">
      No data available. Please select a system.
    </div>
    <component
      v-else
      :is="currentChartComponent"
      :key="chartKey"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useDataStore } from '../stores/dataStore'
import ChordDiagram from './charts/ChordDiagram.vue'
import SankeyChart from './charts/SankeyChart.vue'
import FilteredHeatmap from './charts/FilteredHeatmap.vue'
import AreaChart from './charts/AreaChart.vue'
import LineChart from './charts/LineChart.vue'
import InteractionConservationMatrix from './charts/InteractionConservationMatrix.vue'
import ViolinChart from './charts/ViolinChart.vue'

const dataStore = useDataStore()

const chartKey = ref(0)

const loading = computed(() => {
  return dataStore.loading.interactions || 
         dataStore.loading.area || 
         dataStore.loading.trends
})

const error = computed(() => {
  return dataStore.errors.interactions || 
         dataStore.errors.area || 
         dataStore.errors.trends
})

const hasData = computed(() => {
  return dataStore.currentSystem !== null
})

const chartComponents = {
  chord: ChordDiagram,
  sankey: SankeyChart,
  filteredHeatmap: FilteredHeatmap,
  area: AreaChart,
  line: LineChart,
  interactionConservationMatrix: InteractionConservationMatrix,
  violinPlot: ViolinChart
}

const currentChartComponent = computed(() => {
  return chartComponents[dataStore.currentChartType] || ChordDiagram
})

// Force re-render when chart type or data changes
watch([
  () => dataStore.currentChartType,
  () => dataStore.currentThreshold,
  () => dataStore.currentSystem?.id
], () => {
  chartKey.value++
})
</script>

<style scoped>
.chart-container {
  background: #ffffff;
  border-radius: 18px;
  padding: 32px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
  min-height: 850px;
}

.loading,
.error,
.no-data {
  text-align: center;
  padding: 100px 20px;
  color: #6e6e73;
  font-size: 19px;
}

.loading-spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid #d2d2d7;
  border-top-color: #1d1d1f;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

