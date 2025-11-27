<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="dropdown-group">
        <label for="interaction-type-select" class="dropdown-label">Interaction Type:</label>
        <select 
          id="interaction-type-select"
          v-model="selectedInteractionType" 
          class="interaction-dropdown"
          @change="updateChart"
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
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import Highcharts from 'highcharts'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor } from '../../utils/chartHelpers'
import api from '../../services/api'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
const distanceData = ref(null)
const selectedInteractionType = ref('')

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

const updateChart = () => {
  if (!chartContainer.value) return

  if (!selectedInteractionType.value) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">Please select an interaction type to view the interaction timeline.</div>'
    return
  }

  // Use all interactions regardless of global conservation threshold
  const filteredData = dataStore.interactions

  if (filteredData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try selecting a different interaction type.</div>'
    return
  }

  // Create unique residue pairs, but only include pairs that have the selected interaction type
  const pairMap = new Map()
  filteredData.forEach(interaction => {
    // Only include interactions that have the selected type
    if (!interaction.typesArray || !interaction.typesArray.includes(selectedInteractionType.value)) {
      return
    }
    
    const pairKey = `${interaction.id1} ↔ ${interaction.id2}`
    if (!pairMap.has(pairKey)) {
      pairMap.set(pairKey, {
        pair: pairKey,
        id1: interaction.id1,
        id2: interaction.id2,
        interactions: []
      })
    }
    pairMap.get(pairKey).interactions.push(interaction)
  })

  // Sort pairs by residue number (extract number from id)
  const sortedPairs = Array.from(pairMap.values()).sort((a, b) => {
    const numA1 = parseInt(a.id1.match(/\d+/)?.[0] || '0')
    const numA2 = parseInt(a.id2.match(/\d+/)?.[0] || '0')
    const numB1 = parseInt(b.id1.match(/\d+/)?.[0] || '0')
    const numB2 = parseInt(b.id2.match(/\d+/)?.[0] || '0')
    
    // Sort by first residue, then second
    if (numA1 !== numB1) return numA1 - numB1
    return numA2 - numB2
  })

  // If no pairs have the selected interaction type, show message
  if (sortedPairs.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No pairs found with the interaction type "${selectedInteractionType.value}". Try selecting a different interaction type.</div>`
    return
  }

  const pairLabels = sortedPairs.map(p => p.pair)
  const totalFrames = dataStore.totalFrames

  // Prepare data: only for the selected interaction type
  const dataPoints = []

  sortedPairs.forEach((pairData, pairIndex) => {
    pairData.interactions.forEach(interaction => {
      // Use typeFrames - only show interactions in frames where they actually occur
      const typeFrames = interaction.typeFrames || {}
      const typePersistence = interaction.typePersistence || {}
      
      // Only process the selected interaction type
      if (!interaction.typesArray.includes(selectedInteractionType.value)) {
        return
      }
      
      // Check if THIS SPECIFIC TYPE has 100% persistence
      const typePersist = typePersistence[selectedInteractionType.value] || 0
      let framesForType = []
      
      if (typePersist >= 0.9999) {
        // This type appears in 100% of frames - show pin in ALL frames
        framesForType = Array.from({ length: totalFrames }, (_, i) => i + 1)
      } else {
        // Get frames where this specific type actually occurs
        if (!typeFrames[selectedInteractionType.value] || !Array.isArray(typeFrames[selectedInteractionType.value]) || typeFrames[selectedInteractionType.value].length === 0) {
          return // Skip if we don't have frame data for it
        }
        framesForType = typeFrames[selectedInteractionType.value]
      }
      
      // Create data points for frames (all frames if 100%, otherwise only where type exists)
      framesForType.forEach(frameNum => {
        // Validate frame number is within range
        if (frameNum < 1 || frameNum > totalFrames) {
          console.warn(`Frame ${frameNum} out of range (1-${totalFrames}) for pair ${pairData.pair}`)
          return
        }
        
        // Get distance for this pair-frame-type combination
        const pairKey = `${interaction.id1}_${interaction.id2}`
        const distances = distanceData.value?.distances?.[pairKey]
        const distance = distances?.[frameNum]?.[selectedInteractionType.value] || null
        
        // Center dots in their rectangle (no jitter for single type)
        const yPosition = pairIndex
        
        dataPoints.push({
          x: frameNum - 1, // Convert to 0-based index for x-axis
          y: yPosition,
          frame: frameNum,
          pair: pairData.pair,
          type: selectedInteractionType.value,
          consistency: interaction.consistency,
          typePersistence: typePersist,
          distance: distance,
          custom: {
            pair: pairData.pair,
            frame: frameNum,
            type: selectedInteractionType.value,
            consistency: interaction.consistency,
            typePersistence: typePersist,
            typesArray: interaction.typesArray,
            distance: distance
          }
        })
      })
    })
  })

  // Create single series for the selected interaction type
  const series = [{
    name: selectedInteractionType.value,
    type: 'scatter',
    data: dataPoints,
    color: getInteractionBaseColor(selectedInteractionType.value),
    marker: {
      radius: 4,
      lineWidth: 1,
      lineColor: '#ffffff',
      symbol: 'circle'
    },
    tooltip: {
      pointFormat: '<b>{point.custom.pair}</b><br/>Frame: {point.custom.frame}<br/>Type: {point.custom.type}<br/>Conservation: {point.custom.consistency:.0%}'
    }
  }]

  if (chart) {
    chart.destroy()
  }

  chart = Highcharts.chart(chartContainer.value, {
    chart: {
      type: 'scatter',
      backgroundColor: 'transparent',
      height: Math.max(600, sortedPairs.length * 25 + 200),
      zoomType: 'xy'
    },
    title: {
      text: `Interaction Timeline: ${selectedInteractionType.value}`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: 'Frames (X-axis) × Residue Pairs (Y-axis)',
      style: {
        fontSize: '17px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    xAxis: {
      title: {
        text: 'Frame Number',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: 0,
      max: totalFrames - 1,
      tickInterval: Math.max(1, Math.floor(totalFrames / 20)),
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        },
        formatter: function() {
          return this.value + 1 // Convert back to 1-based frame numbers
        }
      },
      gridLineWidth: 1,
      gridLineColor: '#e8e8ed'
    },
    yAxis: {
      title: {
        text: 'Residue Pairs',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: -0.5,
      max: sortedPairs.length - 0.5,
      tickPositions: Array.from({ length: sortedPairs.length }, (_, i) => i),
      labels: {
        align: 'right',
        x: -5,
        useHTML: true,
        style: {
          fontSize: '11px',
          fontWeight: '500',
          color: '#1d1d1f',
          textAlign: 'right'
        },
        formatter: function() {
          const rawIndex = Math.round(this.value)
          const index = Math.max(0, Math.min(sortedPairs.length - 1, rawIndex))
          const label = pairLabels[index]
          return label ? `<div style="display: flex; align-items: center; justify-content: flex-end; height: 100%; line-height: 1;">${label}</div>` : ''
        }
      },
      gridLineWidth: 0,
      tickWidth: 0,
      reversed: false,
      softMin: -0.5,
      softMax: sortedPairs.length - 0.5,
      startOnTick: false,
      endOnTick: false,
      plotLines: Array.from({ length: sortedPairs.length + 1 }, (_, i) => ({
        value: i - 0.5,
        color: '#e8e8ed',
        width: 1,
        zIndex: 1
      }))
    },
    legend: {
      enabled: false // Only one type, so no need for legend
    },
    plotOptions: {
      scatter: {
        marker: {
          radius: 4,
          states: {
            hover: {
              enabled: true,
              lineColor: '#1d1d1f',
              lineWidth: 2,
              radius: 6
            }
          }
        },
        states: {
          hover: {
            marker: {
              enabled: true
            }
          }
        },
        jitter: {
          x: 0,  // Disable x-axis jitter - we want exact frame positions
          y: 0   // Disable y-axis jitter - we handle it deterministically
        }
      }
    },
    series: series,
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      formatter: function() {
        const point = this.point
        const custom = point.custom || {}
        const distance = custom.distance || point.distance
        const distanceHtml = distance !== null && distance !== undefined
          ? `<div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Distance: </span>
              <span style="color: #6e6e73;">${distance.toFixed(2)} Å</span>
            </div>`
          : ''
        
        return `
          <div style="padding: 10px;">
            <div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">
              ${custom.pair || point.pair || 'Unknown'}
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Frame: </span>
              <span style="color: #6e6e73;">${custom.frame || point.frame || 'N/A'}</span>
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Interaction Type: </span>
              <span style="color: #6e6e73;">${custom.type || point.type || 'N/A'}</span>
            </div>
            ${distanceHtml}
          </div>
        `
      }
    }
  })
}

const loadDistanceData = async () => {
  if (!dataStore.currentSystem) return
  
  try {
    const response = await api.getInteractionDistances(dataStore.currentSystem.id)
    distanceData.value = response
  } catch (error) {
    console.error('Error loading distance data:', error)
    distanceData.value = null
  }
}

onMounted(async () => {
  // Auto-select first available type if any
  if (availableInteractionTypes.value.length > 0) {
    selectedInteractionType.value = availableInteractionTypes.value[0]
  }
  await loadDistanceData()
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.interactions.length,
  () => dataStore.totalFrames,
  () => dataStore.currentSystem?.id,
  () => availableInteractionTypes.value
], async () => {
  if (dataStore.currentChartType === 'interactionTimeline') {
    // Update selected type if current one is no longer available
    if (selectedInteractionType.value && !availableInteractionTypes.value.includes(selectedInteractionType.value)) {
      if (availableInteractionTypes.value.length > 0) {
        selectedInteractionType.value = availableInteractionTypes.value[0]
      } else {
        selectedInteractionType.value = ''
      }
    }
    if (dataStore.currentSystem?.id && !distanceData.value) {
      await loadDistanceData()
    }
    updateChart()
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
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f5f7;
  border-radius: 12px;
}

.dropdown-group {
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

.chart-container {
  width: 100%;
  height: 100%;
}
</style>

