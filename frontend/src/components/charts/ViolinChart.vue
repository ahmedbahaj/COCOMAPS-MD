<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="dropdown-group">
        <label for="interaction-type-select" class="dropdown-label">Interaction Type:</label>
        <select 
          id="interaction-type-select"
          v-model="selectedInteractionType" 
          class="interaction-dropdown"
          @change="loadDistanceData"
        >
          <option value="">Select an interaction type...</option>
          <option 
            v-for="type in availableInteractionTypes" 
            :key="type" 
            :value="type"
          >
            {{ type }}
          </option>
        </select>
      </div>
      <div class="slider-group">
        <label for="conservation-slider" class="dropdown-label">Min Conservation:</label>
        <input
          id="conservation-slider"
          type="range"
          min="50"
          max="100"
          step="5"
          v-model.number="minConsistency"
          @input="updateChart"
          class="conservation-slider"
        />
        <span class="slider-value">{{ minConsistency }}%</span>
      </div>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor } from '../../utils/chartHelpers'
import api from '../../services/api'

const dataStore = useDataStore()
const chartContainer = ref(null)
const selectedInteractionType = ref('')
const distanceData = ref(null)
const loading = ref(false)
const minConsistency = ref(50)

// Get all unique interaction types from filtered data
const availableInteractionTypes = computed(() => {
  const typesSet = new Set()
  dataStore.filteredInteractions.forEach(interaction => {
    if (interaction.typesArray && Array.isArray(interaction.typesArray)) {
      interaction.typesArray.forEach(type => {
        typesSet.add(type)
      })
    }
  })
  return Array.from(typesSet).sort()
})

const loadDistanceData = async () => {
  if (!selectedInteractionType.value || !dataStore.currentSystem) {
    updateChart()
    return
  }

  loading.value = true
  
  try {
    const response = await api.getDistanceDistributions(
      dataStore.currentSystem.id,
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

  // Filter by conservation threshold
  const filteredPairs = distanceData.value.filter(pair => 
    (pair.consistency * 100) >= minConsistency.value
  )

  if (filteredPairs.length === 0) {
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No pairs found with conservation ≥ ' + minConsistency.value + '%</div>'
    return
  }

  // Limit to top 50 pairs for performance
  const topPairs = filteredPairs.slice(0, 50)
  
  // Prepare data for Plotly violin plot
  const traces = topPairs.map((pair, index) => {
    const pairLabel = `${pair.chain1}:${pair.resName1}${pair.resNum1}-${pair.chain2}:${pair.resName2}${pair.resNum2}`
    
    // Calculate statistics for hover info
    const sorted = [...pair.distances].sort((a, b) => a - b)
    const mean = pair.distances.reduce((a, b) => a + b, 0) / pair.distances.length
    const median = sorted[Math.floor(sorted.length / 2)]
    const min = sorted[0]
    const max = sorted[sorted.length - 1]
    const range = (max - min).toFixed(2)
    
    // Fix conservation - cap at 100% (backend may return >100% due to multiple atom pairs per frame)
    const conservationPercent = Math.min(100, pair.consistency * 100).toFixed(1)
    
    // Calculate frequency (count) at each distance point for hover
    const distanceCounts = {}
    pair.distances.forEach(d => {
      const rounded = d.toFixed(1) // Group by 0.1 Å bins
      distanceCounts[rounded] = (distanceCounts[rounded] || 0) + 1
    })
    
    return {
      type: 'violin',
      y: pair.distances,
      x: Array(pair.distances.length).fill(pairLabel),
      name: pairLabel,
      box: {
        visible: false
      },
      meanline: {
        visible: true,
        line: {
          color: '#1d1d1f',
          width: 2
        }
      },
      fillcolor: getInteractionBaseColor(selectedInteractionType.value),
      opacity: 0.6,
      points: 'all',
      pointpos: 0,
      jitter: 0.3,
      marker: {
        size: 5,
        color: '#1d1d1f',
        opacity: 0.6,
        line: {
          width: 0
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
        const frequencyPercent = ((countAtDistance / pair.distances.length) * 100).toFixed(1)
        
        return `${pairLabel}<br>` +
          `<b>Distance: ${d.toFixed(2)} Å</b><br>` +
          `Frequency at ~${rounded} Å: ${countAtDistance} measurements (${frequencyPercent}%)<br>` +
          `<br>Statistics:<br>` +
          `Total measurements: ${pair.distances.length}<br>` +
          `Mean: ${mean.toFixed(2)} Å<br>` +
          `Median: ${median.toFixed(2)} Å<br>` +
          `Range: ${min.toFixed(2)} - ${max.toFixed(2)} Å (${range} Å)<br>` +
          `Conservation: ${conservationPercent}%`
      }),
      hoveron: 'points+kde'
    }
  })

  const layout = {
    title: {
      text: `Distance Distribution: ${selectedInteractionType.value}`,
      font: {
        size: 20,
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        color: '#1d1d1f'
      }
    },
    annotations: [{
      text: `Showing ${topPairs.length} pairs with conservation ≥ ${minConsistency.value}% (out of ${distanceData.value.length} total)`,
      xref: 'paper',
      yref: 'paper',
      x: 0.5,
      y: 1.05,
      xanchor: 'center',
      yanchor: 'bottom',
      showarrow: false,
      font: {
        size: 14,
        color: '#6e6e73'
      }
    }],
    xaxis: {
      title: {
        text: 'Residue Pairs',
        font: {
          size: 14,
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          color: '#1d1d1f'
        }
      },
      tickangle: -45,
      tickfont: {
        size: 11,
        color: '#1d1d1f'
      },
      showgrid: false
    },
    yaxis: {
      title: {
        text: 'Distance (Å)',
        font: {
          size: 14,
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          color: '#1d1d1f'
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
      filename: `violin_${selectedInteractionType.value}_${dataStore.currentSystem?.id}`,
      height: layout.height,
      width: 1400,
      scale: 2
    }
  }

  Plotly.newPlot(chartContainer.value, traces, layout, config)
}

onMounted(() => {
  // Auto-select first interaction type if available
  if (availableInteractionTypes.value.length > 0 && !selectedInteractionType.value) {
    selectedInteractionType.value = availableInteractionTypes.value[0]
    loadDistanceData()
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
  () => dataStore.currentChartType,
  () => dataStore.currentSystem?.id,
  () => availableInteractionTypes.value
], () => {
  if (dataStore.currentChartType === 'violinPlot') {
    // Update selected type if current one is no longer available
    if (selectedInteractionType.value && !availableInteractionTypes.value.includes(selectedInteractionType.value)) {
      if (availableInteractionTypes.value.length > 0) {
        selectedInteractionType.value = availableInteractionTypes.value[0]
        loadDistanceData()
      } else {
        selectedInteractionType.value = ''
        distanceData.value = null
        updateChart()
      }
    } else if (selectedInteractionType.value && dataStore.currentSystem?.id) {
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
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f5f7;
  border-radius: 12px;
  flex-wrap: wrap;
}

.dropdown-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dropdown-label {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  white-space: nowrap;
}

.interaction-dropdown {
  padding: 10px 16px;
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
  background: #ffffff;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  cursor: pointer;
  min-width: 300px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.interaction-dropdown:hover {
  border-color: #6e6e73;
}

.interaction-dropdown:focus {
  outline: none;
  border-color: #3B6EF5;
}

.conservation-slider {
  width: 150px;
  height: 6px;
  border-radius: 3px;
  background: #d2d2d7;
  outline: none;
  cursor: pointer;
}

.conservation-slider::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
}

.conservation-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  border: none;
}

.slider-value {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  min-width: 45px;
}

.chart-container {
  width: 100%;
  min-height: 600px;
}
</style>
