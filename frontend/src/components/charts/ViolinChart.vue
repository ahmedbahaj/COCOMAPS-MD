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
import { getInteractionBaseColor, formatResiduePairFromParts } from '../../utils/chartHelpers'
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
          `Frames with interaction: ${uniqueFrames}/${dataStore.totalFrames}<br>` +
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
          color: '#1d1d1f'
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
      filename: `violin_${selectedInteractionType.value}_${dataStore.currentSystem?.id}`,
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
