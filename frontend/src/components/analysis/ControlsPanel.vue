<template>
  <div class="controls-panel" v-if="hasAnyControls">
    <div class="controls-divider"></div>

    <!-- Conservation Threshold Slider -->
    <div
      v-if="showSlider"
      class="control-section"
    >
      <label for="consistencySlider">Pair Conservation Threshold</label>
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
        <div class="slider-value-input">
          <input
            type="number"
            :value="thresholdPercent"
            @input="updateThresholdFromInput"
            @blur="validateThresholdInput"
            min="0"
            max="100"
            step="1"
            class="value-input"
          />
          <span class="percent-symbol">%</span>
        </div>
      </div>
      <p class="slider-description">
        Show interactions present in at least {{ thresholdPercent }}% of frames
      </p>
    </div>

    <!-- Log Scale Toggle -->
    <div
      v-if="showLogScale"
      class="control-section"
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

    <!-- Time Unit Selector (for charts with time axis) -->
    <div
      v-if="showTimeUnit"
      class="control-section"
    >
      <label>Time Axis Label</label>
      <div class="time-unit-chips">
        <button
          v-for="unit in TIME_UNITS"
          :key="unit.value"
          type="button"
          :class="['time-unit-chip', { active: isTimeUnitActive(unit.value) }]"
          @click="selectTimeUnit(unit.value)"
        >
          {{ unit.label }}
        </button>
        <button
          type="button"
          :class="['time-unit-chip', { active: isCustomTimeUnit }]"
          @click="enableCustomTimeUnit"
        >
          Custom
        </button>
        <input
          v-if="isCustomTimeUnit"
          type="text"
          v-model="customTimeUnit"
          @input="updateCustomTimeUnit"
          placeholder="Enter unit..."
          class="time-unit-input"
          ref="customTimeUnitInput"
        />
      </div>
    </div>

    <!-- Interaction Type Filter (expandable, always visible when applicable) -->
    <div
      v-if="showInteractionFilter"
      class="control-section filter-section"
    >
      <div class="filter-header" @click="interactionFilterExpanded = !interactionFilterExpanded">
        <div class="filter-header-left">
          <label style="cursor: pointer; margin-bottom: 0;">Interaction Type Filter</label>
          <span class="filter-badge">{{ selectedCount }}/{{ totalCount }} selected</span>
        </div>
        <div class="filter-header-right">
          <!-- Compact color dots preview when collapsed -->
          <div v-if="!interactionFilterExpanded" class="filter-dots-preview">
            <span
              v-for="type in INTERACTION_TYPES"
              :key="type.id"
              class="filter-dot"
              :class="{ inactive: !dataStore.selectedInteractionTypes.has(type.id) }"
              :style="{ backgroundColor: getTypeColor(type) }"
              :title="type.label"
            ></span>
          </div>
          <span class="expand-icon" :class="{ expanded: interactionFilterExpanded }">
            <svg viewBox="0 0 12 12" width="14" height="14"><path d="M3 5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
      </div>
      <div v-show="interactionFilterExpanded" class="filter-body">
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
              class="interaction-checkbox-input"
            />
            <span 
              class="custom-checkbox"
              :style="{ 
                borderColor: getTypeColor(type),
                backgroundColor: dataStore.selectedInteractionTypes.has(type.id) ? getTypeColor(type) : 'transparent'
              }"
            >
              <svg v-if="dataStore.selectedInteractionTypes.has(type.id)" viewBox="0 0 12 12" class="checkmark">
                <path d="M2 6l3 3 5-5" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            <span>{{ type.label }}</span>
          </label>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, nextTick } from 'vue'
import { useDataStore } from '../../stores/dataStore'
import { INTERACTION_TYPES } from '../../utils/constants'
import { getInteractionBaseColor } from '../../utils/chartHelpers'

const dataStore = useDataStore()

const interactionFilterExpanded = ref(false)

// Common MD time units
const TIME_UNITS = [
  { value: null, label: 'Frame' },
  { value: 'fs', label: 'fs' },
  { value: 'ps', label: 'ps' },
  { value: 'ns', label: 'ns' },
  { value: 'μs', label: 'μs' },
  { value: 'ms', label: 'ms' }
]

// Custom time unit state
const customTimeUnit = ref('')
const customTimeUnitInput = ref(null)

const isCustomTimeUnit = computed(() => {
  const currentUnit = dataStore.timeUnit
  if (!currentUnit) return false
  return !TIME_UNITS.some(u => u.value === currentUnit)
})

const isTimeUnitActive = (value) => {
  if (isCustomTimeUnit.value) return false
  return dataStore.timeUnit === value
}

const selectTimeUnit = (value) => {
  customTimeUnit.value = ''
  dataStore.setTimeUnit(value)
}

const enableCustomTimeUnit = async () => {
  if (!isCustomTimeUnit.value) {
    customTimeUnit.value = dataStore.timeUnit || ''
    dataStore.setTimeUnit(customTimeUnit.value || 'custom')
  }
  await nextTick()
  customTimeUnitInput.value?.focus()
}

const updateCustomTimeUnit = () => {
  dataStore.setTimeUnit(customTimeUnit.value || null)
}

// Get the color for an interaction type based on its keywords
const getTypeColor = (type) => {
  // Use the first keyword to look up the color
  return getInteractionBaseColor(type.keywords[0])
}

const SLIDER_MIN = 0
const SLIDER_MAX = 1
const SLIDER_STEP = 0.1

const showSlider = computed(() => {
  return ['filteredHeatmap'].includes(dataStore.currentChartType)
})

const showLogScale = computed(() => {
  return ['line'].includes(dataStore.currentChartType)
})

const showInteractionFilter = computed(() => {
  return ['filteredHeatmap', 'interactionConservationMatrix'].includes(dataStore.currentChartType)
})

const showTimeUnit = computed(() => {
  return ['line', 'area', 'interactionConservationMatrix'].includes(dataStore.currentChartType)
})

const hasAnyControls = computed(() => {
  return showSlider.value || showLogScale.value || showInteractionFilter.value || showTimeUnit.value
})

const selectedCount = computed(() => dataStore.selectedInteractionTypes.size)
const totalCount = computed(() => INTERACTION_TYPES.length)

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

const updateThreshold = (event) => {
  dataStore.setThreshold(parseFloat(event.target.value))
}

const updateThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    dataStore.setThreshold(value / 100)
  }
}

const validateThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = thresholdPercent.value
    return
  }
  // Clamp value between 0 and 100
  value = Math.max(0, Math.min(100, value))
  event.target.value = value
  dataStore.setThreshold(value / 100)
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
  padding: 0 32px 32px;
}

.controls-divider {
  height: 1px;
  background: #e8e8ed;
  margin-bottom: 28px;
}

.control-section {
  margin-bottom: 24px;
}

.control-section:last-child {
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

/* Slider */
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

input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  position: relative;
  z-index: 2;
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

.slider-value-input {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 80px;
}

.value-input {
  width: 60px;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  text-align: right;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  padding: 6px 8px;
  background: #ffffff;
  font-variant-numeric: tabular-nums;
  transition: all 0.15s ease;
  font-family: inherit;
}

.value-input:focus {
  outline: none;
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, 0.1);
}

.value-input::-webkit-inner-spin-button,
.value-input::-webkit-outer-spin-button {
  opacity: 1;
  cursor: pointer;
}

.percent-symbol {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.slider-description {
  font-size: 14px;
  color: #6e6e73;
  margin-top: 8px;
}

/* Interaction Filter Section */
.filter-section {
  background: #f8f8fa;
  border-radius: 14px;
  padding: 16px 20px;
  border: 1px solid #e8e8ed;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  gap: 12px;
}

.filter-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.filter-badge {
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  background: #e8e8ed;
  padding: 3px 10px;
  border-radius: 980px;
  white-space: nowrap;
}

.filter-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-dots-preview {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: nowrap;
}

.filter-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: opacity 0.15s ease;
}

.filter-dot.inactive {
  opacity: 0.15;
}

.expand-icon {
  color: #8e8e93;
  transition: transform 0.2s ease, color 0.15s ease;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.filter-header:hover .expand-icon {
  color: #1d1d1f;
}

.filter-body {
  margin-top: 16px;
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
  background: #ffffff;
  color: #1d1d1f;
  border: 1px solid #d2d2d7;
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
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e8e8ed;
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

.interaction-checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.custom-checkbox {
  width: 18px;
  height: 18px;
  border: 2px solid;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.custom-checkbox .checkmark {
  width: 12px;
  height: 12px;
}

.checkbox-label:hover .custom-checkbox {
  transform: scale(1.05);
}

/* Time Unit Chips */
.time-unit-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.time-unit-chip {
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  background: #f5f5f7;
  border: 2px solid transparent;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.time-unit-chip:hover {
  background: #e8e8ed;
}

.time-unit-chip.active {
  background: #1d1d1f;
  color: #ffffff;
  border-color: #1d1d1f;
}

.time-unit-input {
  width: 90px;
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  background: #ffffff;
  font-family: inherit;
  transition: all 0.15s ease;
}

.time-unit-input:focus {
  outline: none;
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, 0.1);
}

.time-unit-input::placeholder {
  color: #a1a1a6;
  font-weight: 400;
}
</style>
