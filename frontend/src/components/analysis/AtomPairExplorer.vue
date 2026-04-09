<template>
  <div v-if="visible" class="atom-pair-explorer-overlay" @click.self="close">
    <div class="atom-pair-explorer-panel">
      <div class="panel-header">
        <h2>Atom Pair Explorer</h2>
        <button class="close-button" @click="close">×</button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading atom pair data...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
      </div>

      <div v-else-if="data" class="panel-content">
        <!-- Residue Pair Info -->
        <div class="residue-info">
          <h3>{{ data.residuePair.id1 }} ↔ {{ data.residuePair.id2 }}</h3>
          <p class="interaction-types">
            <span v-for="(type, idx) in data.interactionTypes" :key="idx" class="type-badge">
              {{ type }}
            </span>
          </p>
        </div>

        <!-- Atom Pair Conservation Threshold Slider -->
        <div class="control-group slider-container-wrapper">
          <label for="atomPairConsistencySlider">Atom Pair Conservation Threshold</label>
          <div class="slider-container">
            <div class="slider-control">
              <input
                type="range"
                id="atomPairConsistencySlider"
                :min="ATOM_SLIDER_MIN"
                :max="ATOM_SLIDER_MAX"
                :step="ATOM_SLIDER_STEP"
                v-model="atomPairThreshold"
              />
              <div class="slider-ticks">
                <span
                  v-for="tick in atomPairTicks"
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
                :value="atomPairThresholdPercent"
                @input="updateAtomPairThresholdFromInput"
                @blur="validateAtomPairThresholdInput"
                min="0"
                max="100"
                step="1"
                class="value-input"
              />
              <span class="percent-symbol">%</span>
            </div>
          </div>
          <p class="slider-description">
            Show atom pairs present in at least {{ atomPairThresholdPercent }}% of frames
          </p>
        </div>

        <!-- Most Common Atom Pairs -->
        <div v-if="data.mostCommonAtomPairs && data.mostCommonAtomPairs.length > 0" class="most-common">
          <h4>{{ data.mostCommonAtomPairs.length === 1 ? 'Most Common Atom Pair' : 'Most Common Atom Pairs' }}</h4>
          <div class="atom-pairs-list">
            <div 
              v-for="(pair, idx) in data.mostCommonAtomPairs" 
              :key="idx"
              class="atom-pair-card"
            >
              <span class="atom-pair-label">{{ pair.atomPair }}</span>
              <span class="consistency-badge">
                {{ Math.round(pair.consistency * 100) }}% conservation
              </span>
              <span class="frame-count">{{ pair.frameCount }} frames</span>
            </div>
          </div>
        </div>

        <!-- Atom Pair Timeline -->
        <div class="section">
          <h4>Atom Pair Timeline</h4>
          <div class="timeline-container">
            <div 
              v-for="frame in totalFrames" 
              :key="frame"
              class="timeline-frame"
              :class="{ 'has-interaction': hasInteractionInFrame(frame) }"
              :title="getFrameTooltip(frame)"
            >
              <div class="frame-number">{{ frame }}</div>
              <div class="frame-atoms">
                <span 
                  v-for="(entry, idx) in getAtomPairsForFrame(frame)" 
                  :key="idx"
                  class="atom-pair-chip"
                  :style="{ backgroundColor: getAtomPairColor(entry.atomPair) }"
                >
                  {{ entry.atomPair }}
                </span>
                <span v-if="!hasInteractionInFrame(frame)" class="no-interaction">—</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Atom Pair Frequency -->
        <div class="section">
          <h4>Atom Pair Frequency</h4>
          <div ref="frequencyChart" class="chart-container"></div>
        </div>

        <!-- Atom Pair Transitions -->
        <div v-if="filteredTransitions.length > 0" class="section">
          <h4>Atom Pair Transitions</h4>
          <div class="transitions-list">
            <div 
              v-for="(transition, idx) in filteredTransitions" 
              :key="idx"
              class="transition-item"
            >
              <span class="transition-from">{{ transition.from }}</span>
              <span class="transition-arrow">→</span>
              <span class="transition-to">{{ transition.to }}</span>
              <span class="transition-frames">
                Frame {{ transition.fromFrame }} → {{ transition.toFrame }}
              </span>
            </div>
          </div>
        </div>

        <!-- Atom Pair Details Table -->
        <div class="section">
          <h4>Atom Pair Details</h4>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Atom Pair</th>
                  <th>Frames</th>
                  <th>Conservation</th>
                  <th>Avg Distance (Å)</th>
                  <th>Interaction Types</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pair in filteredAtomPairs" :key="pair.atomPair">
                  <td><strong>{{ pair.atomPair }}</strong></td>
                  <td>{{ pair.frameCount }} / {{ totalFrames }}</td>
                  <td>{{ Math.round(pair.consistency * 100) }}%</td>
                  <td>{{ pair.avgDistance ? pair.avgDistance.toFixed(2) : 'N/A' }}</td>
                  <td>
                    <span 
                      v-for="(type, idx) in pair.interactionTypes" 
                      :key="idx"
                      class="type-tag"
                    >
                      {{ type }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import Highcharts from 'highcharts'
import api from '../../services/api'
import { useDataStore } from '../../stores/dataStore'
import { parseResidueId } from '../../utils/chartHelpers'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  residuePair: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const dataStore = useDataStore()
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const frequencyChart = ref(null)
let chartInstance = null

const totalFrames = ref(0)
const transitions = ref([])

const ATOM_SLIDER_MIN = 0
const ATOM_SLIDER_MAX = 1
const ATOM_SLIDER_STEP = 0.1

// Atom pair consistency threshold (local to this component)
const atomPairThreshold = ref(0) // Default: show all atom pairs

// Computed properties for filtered data
const atomPairThresholdPercent = computed(() => {
  return Math.round(atomPairThreshold.value * 100)
})

const atomPairTicks = computed(() => {
  const ticks = []
  for (let value = ATOM_SLIDER_MIN; value <= ATOM_SLIDER_MAX + 0.0001; value += ATOM_SLIDER_STEP) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

const filteredAtomPairs = computed(() => {
  if (!data.value || !data.value.atomPairs) return []
  // Use >= for "at least" comparison (greater than or equal to)
  // Compare at percentage level to avoid floating point precision issues
  // Convert threshold to percentage (0-100) and round to integer
  const thresholdPercent = Math.round(atomPairThreshold.value * 100)
  return data.value.atomPairs.filter(pair => {
    // Convert consistency to percentage (0-100) and round to integer
    const consistencyPercent = Math.round(pair.consistency * 100)
    // Return true if consistency is >= threshold (greater than or equal to)
    // Use explicit >= comparison to ensure exact matches are included
    return consistencyPercent >= thresholdPercent
  })
})

const filteredAtomPairsByFrame = computed(() => {
  if (!data.value || !data.value.atomPairsByFrame) return {}
  
  // Get set of filtered atom pair keys
  const filteredKeys = new Set(filteredAtomPairs.value.map(pair => pair.atomPair))
  
  // Filter atomPairsByFrame to only include filtered atom pairs
  const filtered = {}
  for (const [frame, pairs] of Object.entries(data.value.atomPairsByFrame)) {
    const filteredPairs = pairs.filter(entry => filteredKeys.has(entry.atomPair))
    if (filteredPairs.length > 0) {
      filtered[frame] = filteredPairs
    }
  }
  return filtered
})

const filteredTransitions = computed(() => {
  if (!transitions.value || transitions.value.length === 0) return []
  
  // Get set of filtered atom pair keys
  const filteredKeys = new Set(filteredAtomPairs.value.map(pair => pair.atomPair))
  
  // Only include transitions where both from and to are in filtered pairs
  return transitions.value.filter(transition => 
    filteredKeys.has(transition.from) && filteredKeys.has(transition.to)
  )
})

// Functions to update threshold from input
const updateAtomPairThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    atomPairThreshold.value = value / 100
  }
}

const validateAtomPairThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = atomPairThresholdPercent.value
    return
  }
  // Clamp value between 0 and 100
  value = Math.max(0, Math.min(100, value))
  event.target.value = value
  atomPairThreshold.value = value / 100
}

// Color palette for atom pairs
const atomPairColors = {}
let colorIndex = 0
const colorPalette = [
  '#3B6EF5', '#FF8A4C', '#34C759', '#FF3B30', '#AF52DE',
  '#FF9500', '#00C7BE', '#FF2D55', '#5856D6', '#007AFF'
]

const getAtomPairColor = (atomPair) => {
  if (!atomPairColors[atomPair]) {
    atomPairColors[atomPair] = colorPalette[colorIndex % colorPalette.length]
    colorIndex++
  }
  return atomPairColors[atomPair]
}

const close = () => {
  emit('close')
}

const hasInteractionInFrame = (frame) => {
  const frameData = filteredAtomPairsByFrame.value[frame.toString()]
  return frameData && frameData.length > 0
}

const getAtomPairsForFrame = (frame) => {
  const frameData = filteredAtomPairsByFrame.value[frame.toString()]
  return frameData || []
}

const getFrameTooltip = (frame) => {
  const pairs = getAtomPairsForFrame(frame)
  if (pairs.length === 0) return `Frame ${frame}: No interaction`
  return `Frame ${frame}: ${pairs.map(p => p.atomPair).join(', ')}`
}

const loadAtomPairData = async () => {
  if (!props.residuePair || !dataStore.currentSystem) return

  loading.value = true
  error.value = null
  data.value = null

  try {
    // Extract residue info from the pair
    const [id1, id2] = [props.residuePair.id1, props.residuePair.id2]
    
    const res1 = parseResidueId(id1)
    const res2 = parseResidueId(id2)

    if (!res1 || !res2) {
      throw new Error('Invalid residue pair format')
    }

    const params = {
      resName1: res1.resName,
      resNum1: res1.resNum,
      chain1: res1.chain,
      resName2: res2.resName,
      resNum2: res2.resNum,
      chain2: res2.chain
    }

    const response = await api.getAtomPairs(dataStore.currentSystem.id, params)
    data.value = response
    totalFrames.value = response.totalFrames || dataStore.totalFrames
    
    // Process transitions
    if (response.transitions) {
      transitions.value = response.transitions
    }

    await nextTick()
    updateFrequencyChart()
  } catch (err) {
    error.value = err.message || 'Failed to load atom pair data'
    console.error('Error loading atom pair data:', err)
  } finally {
    loading.value = false
  }
}

const updateFrequencyChart = () => {
  if (!frequencyChart.value || !data.value) return

  if (chartInstance) {
    chartInstance.destroy()
  }

  // Use filtered atom pairs
  const chartData = filteredAtomPairs.value.map(pair => ({
    name: pair.atomPair,
    y: pair.frameCount,
    consistency: pair.consistency,
    color: getAtomPairColor(pair.atomPair)
  })).sort((a, b) => b.y - a.y)

  chartInstance = Highcharts.chart(frequencyChart.value, {
    chart: {
      type: 'bar',
      backgroundColor: 'transparent',
      height: Math.max(300, chartData.length * 40)
    },
    title: {
      text: null
    },
    credits: {
      enabled: false
    },
    xAxis: {
      type: 'category',
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      }
    },
    yAxis: {
      title: {
        text: 'Frame Count',
        style: {
          fontSize: '13px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '12px',
          color: '#6e6e73'
        }
      }
    },
    legend: {
      enabled: false
    },
    plotOptions: {
      bar: {
        dataLabels: {
          enabled: true,
          format: '{y} frames ({point.consistency:.0%})',
          style: {
            fontSize: '11px',
            fontWeight: '500',
            color: '#1d1d1f'
          }
        }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 8,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      formatter: function() {
        return `<b>${this.point.name}</b><br/>` +
               `Frames: ${this.point.y} / ${totalFrames.value}<br/>` +
               `Conservation: ${(this.point.consistency * 100).toFixed(1)}%`
      }
    },
    series: [{
      name: 'Frame Count',
      data: chartData
    }]
  })
}

watch(() => props.visible, (newVal) => {
  if (newVal && props.residuePair) {
    loadAtomPairData()
  }
})

watch(() => props.residuePair, () => {
  if (props.visible && props.residuePair) {
    loadAtomPairData()
  }
})

// Watch threshold changes to update chart
watch(atomPairThreshold, () => {
  if (data.value) {
    nextTick(() => {
      updateFrequencyChart()
    })
  }
})

// Watch filtered atom pairs to update chart when data changes
watch(filteredAtomPairs, () => {
  if (data.value) {
    nextTick(() => {
      updateFrequencyChart()
    })
  }
}, { deep: true })
</script>

<style scoped>
.atom-pair-explorer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.atom-pair-explorer-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 1200px;
  max-height: 90vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8ed;
}

.panel-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-button {
  background: none;
  border: none;
  font-size: 32px;
  color: #6e6e73;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: #f5f5f7;
}

.panel-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.loading-state,
.error-state {
  padding: 60px 24px;
  text-align: center;
  color: #6e6e73;
}

.spinner {
  border: 3px solid #e8e8ed;
  border-top: 3px solid #3B6EF5;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.residue-info {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e8e8ed;
}

.residue-info h3 {
  margin: 0 0 12px 0;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.interaction-types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-badge {
  background: #f5f5f7;
  color: #1d1d1f;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.most-common {
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f5f7;
  border-radius: 12px;
}

.most-common h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.atom-pairs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.atom-pair-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e8e8ed;
}

.atom-pair-label {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.consistency-badge {
  background: #3B6EF5;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.frame-count {
  color: #6e6e73;
  font-size: 14px;
}

.section {
  margin-bottom: 32px;
}

.section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.timeline-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
  background: #fafafa;
  border-radius: 8px;
}

.timeline-frame {
  min-width: 120px;
  padding: 8px;
  background: white;
  border: 2px solid #e8e8ed;
  border-radius: 8px;
  transition: all 0.2s;
}

.timeline-frame.has-interaction {
  border-color: #3B6EF5;
  background: #f0f4ff;
}

.frame-number {
  font-size: 11px;
  font-weight: 600;
  color: #6e6e73;
  margin-bottom: 4px;
}

.frame-atoms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.atom-pair-chip {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: white;
  white-space: nowrap;
}

.no-interaction {
  color: #c7c7cc;
  font-size: 12px;
}

.chart-container {
  min-height: 300px;
  width: 100%;
}

.transitions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.transition-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f5f7;
  border-radius: 8px;
  font-size: 14px;
}

.transition-from,
.transition-to {
  font-weight: 600;
  color: #1d1d1f;
}

.transition-arrow {
  color: #6e6e73;
  font-size: 18px;
}

.transition-frames {
  margin-left: auto;
  color: #6e6e73;
  font-size: 12px;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f5f5f7;
}

th {
  padding: 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

td {
  padding: 12px;
  font-size: 14px;
  color: #1d1d1f;
  border-bottom: 1px solid #e8e8ed;
}

.type-tag {
  display: inline-block;
  background: #e8e8ed;
  color: #1d1d1f;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  margin-right: 4px;
}

.control-group {
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f5f7;
  border-radius: 12px;
}

.control-group label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
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
  margin-bottom: 0;
}
</style>

