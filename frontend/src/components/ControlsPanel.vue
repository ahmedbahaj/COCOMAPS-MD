<template>
  <div class="controls-panel">
    <!-- Consistency Threshold Slider -->
    <div
      v-if="showSlider"
      class="control-group slider-container-wrapper"
    >
      <label for="consistencySlider">Consistency Threshold</label>
      <div class="slider-container">
        <input
          type="range"
          id="consistencySlider"
          min="0.5"
          max="1"
          step="0.01"
          :value="dataStore.currentThreshold"
          @input="updateThreshold"
        />
        <span class="slider-value">{{ thresholdPercent }}%</span>
      </div>
      <p class="slider-description">
        Show interactions present in at least {{ thresholdPercent }}% of frames
      </p>
    </div>

    <!-- Log Scale Toggle -->
    <div
      v-if="showLogScale"
      class="control-group slider-container-wrapper"
    >
      <label for="logScaleToggle">Chart Scale</label>
      <div style="display: flex; gap: 12px; align-items: center;">
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin: 0;">
          <input
            type="checkbox"
            id="logScaleToggle"
            :checked="dataStore.useLogScale"
            @change="toggleLogScale"
            style="width: 20px; height: 20px; cursor: pointer; accent-color: #1d1d1f;"
          />
          <span style="font-size: 15px; font-weight: 500; color: #1d1d1f;">Use Logarithmic Scale</span>
        </label>
      </div>
    </div>

    <!-- Interaction Type Filter -->
    <div
      v-if="showInteractionFilter"
      class="control-group slider-container-wrapper"
    >
      <label>Filter Interaction Types</label>
      <div class="filter-buttons">
        <button
          type="button"
          @click="selectAllTypes"
          class="filter-btn secondary"
        >
          Select All
        </button>
        <button
          type="button"
          @click="deselectAllTypes"
          class="filter-btn secondary"
        >
          Deselect All
        </button>
      </div>
      <div class="interaction-checkboxes">
        <label
          v-for="type in INTERACTION_TYPES"
          :key="type.id"
          class="checkbox-label"
        >
          <input
            type="checkbox"
            :checked="dataStore.selectedInteractionTypes.has(type.id)"
            @change="toggleInteractionType(type.id)"
            class="interaction-checkbox"
          />
          <span>{{ type.label }}</span>
        </label>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="control-group">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ totalInteractions }}</div>
          <div class="stat-label">Total Interactions</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ visibleInteractions }}</div>
          <div class="stat-label">Visible Interactions</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ avgConsistency }}</div>
          <div class="stat-label">Avg Consistency</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ dataStore.totalFrames }}</div>
          <div class="stat-label">Total Frames</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDataStore } from '../stores/dataStore'
import { INTERACTION_TYPES } from '../utils/constants'

const dataStore = useDataStore()

const showSlider = computed(() => {
  return ['arc', 'chord', 'filteredHeatmap', 'timePairMatrix'].includes(dataStore.currentChartType)
})

const showLogScale = computed(() => {
  return ['area', 'line'].includes(dataStore.currentChartType)
})

const showInteractionFilter = computed(() => {
  return ['arc', 'chord', 'heatmap', 'filteredHeatmap'].includes(dataStore.currentChartType)
})

const thresholdPercent = computed(() => {
  return Math.round(dataStore.currentThreshold * 100)
})

const totalInteractions = computed(() => {
  return dataStore.interactions.length
})

const visibleInteractions = computed(() => {
  return dataStore.filteredInteractions.length
})

const avgConsistency = computed(() => {
  if (dataStore.interactions.length === 0) return '-'
  const avg = dataStore.interactions.reduce((sum, d) => sum + d.consistency, 0) / dataStore.interactions.length
  return Math.round(avg * 100) + '%'
})

const updateThreshold = (event) => {
  dataStore.setThreshold(parseFloat(event.target.value))
}

const toggleLogScale = (event) => {
  dataStore.setLogScale(event.target.checked)
}

const toggleInteractionType = (typeId) => {
  dataStore.toggleInteractionType(typeId)
}

const selectAllTypes = () => {
  dataStore.selectAllInteractionTypes()
}

const deselectAllTypes = () => {
  dataStore.clearInteractionTypes()
}
</script>

<style scoped>
.controls-panel {
  background: #fbfbfd;
  border-radius: 18px;
  padding: 32px;
  margin-bottom: 32px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
}

.control-group {
  margin-bottom: 24px;
}

.control-group:last-child {
  margin-bottom: 0;
}

label {
  display: block;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  letter-spacing: -0.022em;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 20px;
}

input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #d2d2d7;
  outline: none;
  flex: 1;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.15s ease;
}

input[type="range"]::-webkit-slider-thumb:hover {
  background: #000000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
  transform: scale(1.05);
}

.slider-value {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  min-width: 80px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.slider-description {
  font-size: 14px;
  color: #6e6e73;
  margin-top: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  border: 1px solid #d2d2d7;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6e6e73;
  font-weight: 500;
}

.filter-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.filter-btn {
  padding: 8px 16px;
  font-size: 14px;
  border: none;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.filter-btn.secondary {
  background: #f5f5f7;
  color: #1d1d1f;
}

.filter-btn.secondary:hover {
  background: #e8e8ed;
}

.interaction-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: #f5f5f7;
  border-radius: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  margin: 0;
}

.interaction-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #1d1d1f;
}
</style>

