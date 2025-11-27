<template>
  <div class="controls-panel">
    <!-- Conservation Threshold Slider -->
    <div
      v-if="showSlider"
      class="control-group slider-container-wrapper"
    >
      <label for="consistencySlider">Conservation Threshold</label>
      <div class="slider-container">
        <div class="slider-control">
          <input
            type="range"
            id="consistencySlider"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :step="SLIDER_STEP"
            :value="dataStore.currentThreshold"
            @input="updateThreshold"
          />
          <div class="slider-ticks">
            <span
              v-for="tick in thresholdTicks"
              :key="tick.value"
              class="slider-tick"
            >
              <span class="slider-tick-label">{{ tick.label }}</span>
            </span>
          </div>
        </div>
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
          <div class="stat-label">Avg Conservation</div>
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

const SLIDER_MIN = 0.5
const SLIDER_MAX = 1
const SLIDER_STEP = 0.1

const showSlider = computed(() => {
  // Do NOT show the global conservation slider for interactionTimeline;
  // that chart always shows all interactions.
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

const thresholdTicks = computed(() => {
  const ticks = []
  for (let value = SLIDER_MIN; value <= SLIDER_MAX + 0.0001; value += SLIDER_STEP) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
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
  gap: 12px;
}

.slider-control {
  position: relative;
  flex: 1;
}

.slider-ticks {
  position: absolute;
  left: 14px;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}

.slider-tick {
  position: relative;
  width: 2px;
  height: 16px;
  background: #b4b4bb;
  opacity: 0.7;
}

.slider-tick-label {
  position: absolute;
  top: -24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 600;
  color: #6e6e73;
}
/* Ensure labels don't shift left/right per tick */

input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  position: relative;
  z-index: 2; /* Slider thumb above tick marks */
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

