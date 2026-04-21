<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
    <div class="chart-toolbar">
      <!-- Interaction Type Chips -->
      <div class="control-group">
        <label>Select Interaction Type</label>
        <div class="interaction-chips">
          <button
            v-for="type in availableInteractionTypes"
            :key="type"
            type="button"
            :class="['interaction-chip', { active: selectedInteractionType === type }]"
            @click="selectInteractionType(type)"
          >
            <span class="chip-color-dot" :style="{ backgroundColor: getInteractionBaseColor(type) }"></span>
            {{ type }}
          </button>
        </div>
        <p v-if="availableInteractionTypes.length === 0" class="no-types-message">
          No interaction types available. Adjust filters to see more types.
        </p>
      </div>
      
      <!-- Pair Conservation Threshold Slider -->
      <div class="control-group">
        <label for="conservation-slider">Pair Conservation Threshold</label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="conservation-slider"
              type="range"
              min="0"
              max="1"
              step="0.1"
              :value="chartUiStore.currentThreshold"
              @input="updateThreshold"
            />
            <div class="slider-ticks">
              <span
                v-for="tick in conservationTicks"
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
        <p class="slider-description">Show pairs with conservation ≥ {{ thresholdPercent }}%</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { getInteractionBaseColor, formatResiduePairFromParts } from '../../utils/chartHelpers'
import api from '../../services/api'

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
const selectedInteractionType = ref('')
const distanceData = ref(null)
const loading = ref(false)

// Threshold percent (derived from store)
const thresholdPercent = computed(() => Math.round(chartUiStore.currentThreshold * 100))

// Conservation threshold ticks (0% to 100% in 10% steps)
const conservationTicks = computed(() => {
  const ticks = []
  for (let value = 0; value <= 1.0 + 0.0001; value += 0.1) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

// Slider update handlers — write to the shared store
const updateThreshold = (event) => {
  chartUiStore.setThreshold(parseFloat(event.target.value))
  updateChart()
}

const updateThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    chartUiStore.setThreshold(value / 100)
    updateChart()
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
  chartUiStore.setThreshold(value / 100)
  updateChart()
}

// Get all unique interaction types from filtered data
const availableInteractionTypes = computed(() => {
  const typesSet = new Set()
  analysisStore.filteredInteractions.forEach(interaction => {
    if (interaction.typesArray && Array.isArray(interaction.typesArray)) {
      interaction.typesArray.forEach(type => {
        typesSet.add(type)
      })
    }
  })
  return Array.from(typesSet).sort()
})

const selectInteractionType = (type) => {
  selectedInteractionType.value = type
  loadDistanceData()
}

const loadDistanceData = async () => {
  if (!selectedInteractionType.value || !systemsStore.currentSystem) {
    updateChart()
    return
  }

  loading.value = true
  
  try {
    const response = await api.getDistanceDistributions(
      systemsStore.currentSystem.id,
      [selectedInteractionType.value]
    )
    distanceData.value = response.pairs || []
  } catch (error) {
    console.error('Failed to load distance data:', error)
    distanceData.value = []
  } finally {
    loading.value = false
    updateChart()
  }
}

const selectFirstTypeWithData = async () => {
  if (!systemsStore.currentSystem || availableInteractionTypes.value.length === 0) {
    updateChart()
    return
  }

  loading.value = true
  updateChart()

  const threshold = chartUiStore.currentThreshold

  for (const type of availableInteractionTypes.value) {
    try {
      const response = await api.getDistanceDistributions(
        systemsStore.currentSystem.id,
        [type]
      )
      const pairs = response.pairs || []
      if (pairs.some(p => p.consistency >= threshold)) {
        selectedInteractionType.value = type
        distanceData.value = pairs
        loading.value = false
        updateChart()
        return
      }
    } catch {
      // skip this type, try next
    }
  }

  selectedInteractionType.value = availableInteractionTypes.value[0]
  distanceData.value = []
  loading.value = false
  updateChart()
}

const updateChart = () => {
  if (!chartContainer.value) return

  if (!selectedInteractionType.value) {
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">Please select an interaction type to view the distance distribution.</div>'
    return
  }

  if (loading.value) {
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">Loading distance data...</div>'
    return
  }

  if (!distanceData.value || distanceData.value.length === 0) {
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No distance data available for the selected interaction type.</div>'
    return
  }

  // Filter by conservation threshold (from shared store)
  const filteredPairs = distanceData.value.filter(pair => 
    pair.consistency >= chartUiStore.currentThreshold
  )

  if (filteredPairs.length === 0) {
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No pairs found with conservation ≥ ' + thresholdPercent.value + '%</div>'
    return
  }

  // Limit to top 50 pairs for performance
  const topPairs = filteredPairs.slice(0, 50)
  
  // Calculate global mean across all pairs
  const allDistances = topPairs.flatMap(pair => pair.distances)
  const globalMean = allDistances.reduce((a, b) => a + b, 0) / allDistances.length
  
  // Get interaction color
  const interactionColor = getInteractionBaseColor(selectedInteractionType.value)
  
  // Prepare data for Plotly violin plot
  const pairLabels = topPairs.map(pair => formatResiduePairFromParts(
    { resName: pair.resName1, resNum: pair.resNum1, chain: pair.chain1 },
    { resName: pair.resName2, resNum: pair.resNum2, chain: pair.chain2 }
  ))

  const traces = topPairs.map((pair, index) => {
    const pairLabel = pairLabels[index]
    
    // Calculate statistics for hover info
    const sorted = [...pair.distances].sort((a, b) => a - b)
    const mean = pair.distances.reduce((a, b) => a + b, 0) / pair.distances.length
    const median = sorted[Math.floor(sorted.length / 2)]
    const min = sorted[0]
    const max = sorted[sorted.length - 1]
    const range = (max - min).toFixed(2)
    
    const conservationPercent = (pair.consistency * 100).toFixed(1)
    
    // Calculate frequency (count) at each distance point for hover
    const distanceCounts = {}
    pair.distances.forEach(d => {
      const rounded = d.toFixed(1) // Group by 0.1 Å bins
      distanceCounts[rounded] = (distanceCounts[rounded] || 0) + 1
    })
    
    // Total measurements (may be more than frames if multiple atom pairs)
    const totalMeasurements = pair.totalMeasurements || pair.distances.length
    const uniqueFrames = pair.frameCount
    
    return {
      type: 'violin',
      y: pair.distances,
      x: Array(pair.distances.length).fill(pairLabel),
      name: pairLabel,
      box: {
        visible: false
      },
      meanline: {
        visible: false  // We'll add custom short dashes instead
      },
      fillcolor: interactionColor,
      opacity: 0.45,  // Balanced opacity - visible but points still stand out
      points: 'all',
      pointpos: 0,
      jitter: 0.3,  // Fixed jitter value
      marker: {
        size: 6,  // Slightly larger
        color: interactionColor,  // Match interaction type color
        opacity: 1.0,  // Fully opaque for prominence
        line: {
          width: 0.5,
          color: '#ffffff'
        }
      },
      bandwidth: null, // Auto bandwidth
      scalemode: 'width',
      width: 0.9,
      showlegend: false,
      hoverinfo: 'text',
      text: pair.distances.map((d, i) => {
        const rounded = d.toFixed(1)
        const countAtDistance = distanceCounts[rounded]
        const frequencyPercent = ((countAtDistance / totalMeasurements) * 100).toFixed(1)
        
        return `<b>${pairLabel}</b><br>` +
          `Distance: ${d.toFixed(2)} Å<br>` +
          `<b>Frequency at ~${rounded} Å: ${countAtDistance} (${frequencyPercent}%)</b><br>` +
          `<br>Statistics:<br>` +
          `Total measurements: ${totalMeasurements}<br>` +
          `Frames with interaction: ${uniqueFrames}/${systemsStore.totalFrames}<br>` +
          `Mean: ${mean.toFixed(2)} Å<br>` +
          `Median: ${median.toFixed(2)} Å<br>` +
          `Range: ${min.toFixed(2)} - ${max.toFixed(2)} Å<br>` +
          `Conservation: ${conservationPercent}%`
      }),
      hoveron: 'points+kde'
    }
  })
  
  // Collect mean positions for annotations
  const meanAnnotations = topPairs.map((pair, index) => {
    const mean = pair.distances.reduce((a, b) => a + b, 0) / pair.distances.length
    return {
      mean,
      x: pairLabels[index],
      pairLabel: pairLabels[index]
    }
  })
  
  // Add invisible trace for legend entry (global mean)
  traces.push({
    type: 'scatter',
    mode: 'lines',
    x: [null],  // Invisible trace, just for legend
    y: [null],
    line: {
      color: '#1d1d1f',  // Black for global mean
      width: 2.5,
      dash: 'dash'
    },
    name: `Global Mean: ${globalMean.toFixed(2)} Å`,
    showlegend: true,
    hoverinfo: 'skip'
  })

  // Add overlay markers for local means (horizontal line marker)
  traces.push({
    type: 'scatter',
    mode: 'markers',
    x: meanAnnotations.map(item => item.x),
    y: meanAnnotations.map(item => item.mean),
    marker: {
      symbol: 'line-ew',
      size: 18,
      color: interactionColor,
      line: {
        width: 2.5,
        color: interactionColor
      }
    },
    hoverinfo: 'skip',
    showlegend: false
  })

  const layout = {
    title: {
      text: `${systemsStore.currentSystem?.name || 'System'} - Distance Distribution: ${selectedInteractionType.value}`,
      font: {
        size: 20,
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        color: '#1d1d1f'
      }
    },
    annotations: [],
    shapes: [
      // Global mean line - rendered on top of all violins
      {
        type: 'line',
        x0: 0,
        x1: 1,
        xref: 'paper',
        y0: globalMean,
        y1: globalMean,
        yref: 'y',
        line: {
          color: '#1d1d1f',  // Black for global mean
          width: 2.5,
          dash: 'dash'
        },
        layer: 'above'
      }
    ],
    xaxis: {
      title: {
        text: 'Residue Pairs',
        font: {
          size: 14,
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          color: '#1d1d1f',
          weight: 'bold'
        }
      },
      tickangle: -45,
      type: 'category',
      categoryorder: 'array',
      categoryarray: pairLabels,
      tickmode: 'array',
      tickvals: pairLabels,
      ticktext: pairLabels,
      tickfont: {
        size: 11,
        color: '#1d1d1f',
        weight: 'bold'
      },
      showgrid: false
    },
    yaxis: {
      title: {
        text: 'Distance (Å)',
        font: {
          size: 14,
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          color: '#1d1d1f',
          weight: 'bold'
        }
      },
      tickfont: {
        size: 12,
        color: '#1d1d1f'
      },
      gridcolor: '#e5e5e7',
      zeroline: false
    },
    plot_bgcolor: '#ffffff',
    paper_bgcolor: '#ffffff',
    margin: {
      l: 80,
      r: 40,
      t: 120,
      b: 150
    },
    height: Math.max(600, topPairs.length * 50),
    hovermode: 'closest',
    violinmode: 'group',
    legend: {
      x: 1.02,
      y: 1,
      xanchor: 'left',
      yanchor: 'top',
      bgcolor: 'rgba(255, 255, 255, 0.9)',
      bordercolor: '#d2d2d7',
      borderwidth: 1,
      font: {
        size: 13,
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        color: '#1d1d1f'
      }
    },
    font: {
      family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
    }
  }

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    toImageButtonOptions: {
      format: 'png',
      filename: `violin_${selectedInteractionType.value}_${systemsStore.currentSystem?.id}`,
      height: layout.height,
      width: 1400,
      scale: 2
    }
  }

  // Clear any previous content before rendering
  chartContainer.value.innerHTML = ''
  Plotly.newPlot(chartContainer.value, traces, layout, config)
}

onMounted(() => {
  if (availableInteractionTypes.value.length > 0 && !selectedInteractionType.value) {
    selectFirstTypeWithData()
  } else {
    updateChart()
  }
})

onBeforeUnmount(() => {
  if (chartContainer.value) {
    Plotly.purge(chartContainer.value)
  }
})

watch([
  () => chartUiStore.currentChartType,
  () => systemsStore.currentSystem?.id,
  () => chartUiStore.currentThreshold,
  () => availableInteractionTypes.value
], () => {
  if (chartUiStore.currentChartType === 'violinPlot') {
    if (selectedInteractionType.value && !availableInteractionTypes.value.includes(selectedInteractionType.value)) {
      if (availableInteractionTypes.value.length > 0) {
        selectFirstTypeWithData()
      } else {
        selectedInteractionType.value = ''
        distanceData.value = null
        updateChart()
      }
    } else if (selectedInteractionType.value && systemsStore.currentSystem?.id) {
      loadDistanceData()
    } else {
      updateChart()
    }
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
  height: 100%;
}

.chart-toolbar {
  padding: 24px 32px 0;
  margin-top: 8px;
  border-top: 1px solid #e8e8ed;
}

.control-group {
  margin-bottom: 24px;
}

.control-group:last-child {
  margin-bottom: 0;
}

.control-group > label {
  display: block;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  letter-spacing: -0.022em;
}

/* Interaction Type Chips */
.interaction-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.interaction-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
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

.interaction-chip:hover {
  background: #e8e8ed;
}

.interaction-chip.active {
  background: #1d1d1f;
  color: #ffffff;
  border-color: #1d1d1f;
}

.chip-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.interaction-chip.active .chip-color-dot {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.4);
}

.no-types-message {
  font-size: 14px;
  color: #6e6e73;
  font-style: italic;
  margin: 0;
}

/* Slider styles matching ControlsPanel */
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
  margin-bottom: 0;
}

.chart-container {
  width: 100%;
  min-height: 600px;
}
</style>
