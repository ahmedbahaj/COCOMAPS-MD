t<template>
  <div class="chart-selector">
    <div
      v-for="(row, rowIndex) in chartRows"
      :key="`chart-row-${rowIndex}`"
      class="chart-row"
    >
      <button
        v-for="chart in row"
        :key="chart.id"
        :class="['chart-btn', { active: dataStore.currentChartType === chart.id }]"
        @click="selectChart(chart.id)"
      >
        {{ chart.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDataStore } from '../stores/dataStore'

const dataStore = useDataStore()

const charts = [
  { id: 'arc', label: 'Arc Diagram' },
  { id: 'chord', label: 'Chord Diagram' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'filteredHeatmap', label: 'Filtered Heatmap' },
  { id: 'area', label: 'Area Chart' },
  { id: 'line', label: 'Interaction Trends' },
  { id: 'similarity', label: 'Similarity Matrix' },
  { id: 'timePairMatrix', label: 'Time-Pair Matrix' },
  { id: 'interactionTimeline', label: 'Interaction Time-line' },
  { id: 'interactionConservationMatrix', label: 'Interaction Conservation Matrix' },
  { id: 'conservationScatter', label: '2D Conservation Plot' },
  { id: 'violinPlot', label: 'Distance Distribution' }
]

const chartRows = computed(() => {
  const rows = []
  for (let i = 0; i < charts.length; i += 5) {
    rows.push(charts.slice(i, i + 5))
  }
  return rows
})

const selectChart = (chartId) => {
  dataStore.setChartType(chartId)
}
</script>

<style scoped>
.chart-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.chart-row {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.chart-btn {
  flex: 0 0 180px;
  max-width: 180px;
  background: #f5f5f7;
  color: #1d1d1f;
  border: 2px solid transparent;
  border-radius: 980px;
  padding: 12px 24px;
  font-size: 17px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  letter-spacing: -0.022em;
  text-align: center;
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

@media (max-width: 768px) {
  .chart-row {
    flex-direction: column;
    align-items: stretch;
  }

  .chart-btn {
    flex: 1;
    max-width: none;
  }
}
</style>

