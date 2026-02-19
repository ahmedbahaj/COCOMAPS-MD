<template>
  <div class="chart-selector">
    <div class="tabs-container">
      <div class="tabs-wrapper">
        <button
          v-for="chart in charts"
          :key="chart.id"
          :ref="el => { if (el) tabRefs[chart.id] = el }"
          :class="['tab', { active: dataStore.currentChartType === chart.id }]"
          @click="selectChart(chart.id)"
        >
          <span class="tab-icon" v-html="chart.icon"></span>
          <span class="tab-label">{{ chart.label }}</span>
        </button>
        <div class="tab-indicator" :style="indicatorStyle"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useDataStore } from '../stores/dataStore'

const dataStore = useDataStore()
const tabRefs = ref({})

const charts = [
  { 
    id: 'interactionConservationMatrix', 
    label: 'Conservation Matrix',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/></svg>'
  },
  { 
    id: 'filteredHeatmap', 
    label: 'Interaction Heatmap',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>'
  },
  { 
    id: 'line', 
    label: 'Interaction Trends',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 20h18"/><path d="M3 17l5-5 4 2 5-7 4 4"/><circle cx="8" cy="12" r="1.5" fill="currentColor"/><circle cx="12" cy="14" r="1.5" fill="currentColor"/><circle cx="17" cy="7" r="1.5" fill="currentColor"/></svg>'
  },
  { 
    id: 'violinPlot', 
    label: 'Distance Distribution',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v18"/><ellipse cx="12" cy="12" rx="5" ry="8" opacity="0.2" fill="currentColor"/><ellipse cx="12" cy="12" rx="5" ry="8"/></svg>'
  },
  { 
    id: 'area', 
    label: 'Area Composition',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 20h18"/><path d="M3 17l5-7 4 4 5-8 4 6" fill="currentColor" opacity="0.2"/><path d="M3 17l5-7 4 4 5-8 4 6"/></svg>'
  },
  { 
    id: 'conservedIslandsList', 
    label: 'Conserved Islands',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>'
  }
]

const indicatorStyle = ref({})

const updateIndicator = () => {
  const activeTab = tabRefs.value[dataStore.currentChartType]
  if (activeTab) {
    indicatorStyle.value = {
      width: `${activeTab.offsetWidth}px`,
      transform: `translateX(${activeTab.offsetLeft}px)`
    }
  }
}

const selectChart = (chartId) => {
  dataStore.setChartType(chartId)
}

watch(() => dataStore.currentChartType, () => {
  nextTick(updateIndicator)
})

onMounted(() => {
  nextTick(updateIndicator)
  window.addEventListener('resize', updateIndicator)
})
</script>

<style scoped>
.chart-selector {
  margin-bottom: 16px;
}

.tabs-container {
  display: flex;
  justify-content: center;
}

.tabs-wrapper {
  display: inline-flex;
  position: relative;
  background: #f5f5f7;
  border-radius: 16px;
  padding: 6px;
  gap: 6px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  background: transparent;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  color: #6e6e73;
  cursor: pointer;
  transition: color 0.2s ease;
  font-family: inherit;
  position: relative;
  z-index: 1;
  white-space: nowrap;
}

.tab:hover {
  color: #1d1d1f;
}

.tab.active {
  color: #1d1d1f;
}

.tab-icon {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.tab-label {
  letter-spacing: -0.01em;
}

.tab-indicator {
  position: absolute;
  bottom: 6px;
  left: 0;
  height: calc(100% - 12px);
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 0;
}

@media (max-width: 1100px) {
  .tabs-wrapper {
    flex-wrap: wrap;
    justify-content: center;
    max-width: 100%;
  }
  
  .tab-indicator {
    display: none;
  }
  
  .tab.active {
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }
}

@media (max-width: 600px) {
  .tabs-container {
    overflow-x: auto;
    justify-content: flex-start;
    padding: 0 16px;
    margin: 0 -16px;
  }
  
  .tabs-wrapper {
    flex-wrap: nowrap;
  }
  
  .tab {
    padding: 12px 18px;
    font-size: 14px;
  }
  
  .tab-icon {
    width: 18px;
    height: 18px;
  }
}
</style>

