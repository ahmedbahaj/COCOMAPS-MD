<template>
  <div class="chart-selector">
    <button
      v-for="chart in charts"
      :key="chart.id"
      :class="['chart-btn', { active: dataStore.currentChartType === chart.id }]"
      @click="selectChart(chart.id)"
    >
      {{ chart.label }}
    </button>
  </div>
</template>

<script setup>
import { useDataStore } from '../stores/dataStore'

const dataStore = useDataStore()

const charts = [
  { id: 'arc', label: 'Arc Diagram' },
  { id: 'chord', label: 'Chord Diagram' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'filteredHeatmap', label: 'Filtered Heatmap' },
  { id: 'area', label: 'Area Chart' },
  { id: 'line', label: 'Interaction Trends' },
  { id: 'similarity', label: 'Similarity Matrix' }
]

const selectChart = (chartId) => {
  dataStore.setChartType(chartId)
}
</script>

<style scoped>
.chart-selector {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 32px;
}

.chart-btn {
  background: #f5f5f7;
  color: #1d1d1f;
  border: 2px solid transparent;
  border-radius: 980px;
  padding: 12px 32px;
  font-size: 17px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  letter-spacing: -0.022em;
}

.chart-btn:hover {
  background: #e8e8ed;
}

.chart-btn.active {
  background: #1d1d1f;
  color: white;
  border-color: #1d1d1f;
}

.chart-btn.active:hover {
  background: #000000;
}
</style>

