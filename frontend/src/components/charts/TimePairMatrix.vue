<template>
  <div ref="chartContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from 'highcharts'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor } from '../../utils/chartHelpers'
import api from '../../services/api'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
const distanceData = ref(null)

const updateChart = () => {
  if (!chartContainer.value) return

  const filteredData = dataStore.filteredInteractions

  if (filteredData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try adjusting the threshold or interaction type filters.</div>'
    return
  }

  // Create unique residue pairs and sort them
  const pairMap = new Map()
  filteredData.forEach(interaction => {
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

  const pairLabels = sortedPairs.map(p => p.pair)
  const totalFrames = dataStore.totalFrames

  // Prepare data: group by interaction type for each pair-frame combination
  const seriesMap = new Map() // type -> data points

  // Helper function to generate deterministic jitter based on pair and type
  const getDeterministicJitter = (pairKey, type, typeIndex) => {
    // Create a hash from pair key and type for consistent jitter
    let hash = 0
    const str = `${pairKey}_${type}_${typeIndex}`
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32-bit integer
    }
    // Normalize to -0.2 to 0.2 range for jitter
    return ((hash % 41) / 100) - 0.2
  }

  sortedPairs.forEach((pairData, pairIndex) => {
    pairData.interactions.forEach(interaction => {
      // Use typeFrames - only show interactions in frames where they actually occur
      const typeFrames = interaction.typeFrames || {}
      const typePersistence = interaction.typePersistence || {}
      
      // For each interaction type, only show it in frames where it actually occurs
      interaction.typesArray.forEach((type, typeIndex) => {
        if (!seriesMap.has(type)) {
          seriesMap.set(type, [])
        }
        
        // Check if THIS SPECIFIC TYPE has 100% persistence (not the overall interaction)
        const typePersist = typePersistence[type] || 0
        let framesForType = []
        
        if (typePersist >= 0.9999) {
          // This type appears in 100% of frames - show pin in ALL frames
          framesForType = Array.from({ length: totalFrames }, (_, i) => i + 1)
        } else {
          // Get frames where this specific type actually occurs
          if (!typeFrames[type] || !Array.isArray(typeFrames[type]) || typeFrames[type].length === 0) {
            return // Skip this type if we don't have frame data for it
          }
          framesForType = typeFrames[type]
        }
        
        // Generate deterministic jitter for this pair-type combination
        const pairKey = `${interaction.id1}_${interaction.id2}`
        const jitter = getDeterministicJitter(pairKey, type, typeIndex)
        
        // Create data points for frames (all frames if 100%, otherwise only where type exists)
        framesForType.forEach(frameNum => {
          // Get distance for this pair-frame-type combination
          const distances = distanceData.value?.distances?.[pairKey]
          const distance = distances?.[frameNum]?.[type] || null
          
          seriesMap.get(type).push({
            x: frameNum - 1, // Convert to 0-based index for x-axis
            y: pairIndex + jitter, // Add deterministic jitter for visibility
            frame: frameNum,
            pair: pairData.pair,
            type: type,
            consistency: interaction.consistency,
            typePersistence: typePersist,
            distance: distance,
            custom: {
              pair: pairData.pair,
              frame: frameNum,
              type: type,
              consistency: interaction.consistency,
              typePersistence: typePersist,
              typesArray: interaction.typesArray,
              distance: distance
            }
          })
        })
      })
    })
  })

  // Convert to series array
  const series = Array.from(seriesMap.entries()).map(([type, data]) => ({
    name: type,
    type: 'scatter',
    data: data,
    color: getInteractionBaseColor(type),
    marker: {
      radius: 4,
      lineWidth: 1,
      lineColor: '#ffffff',
      symbol: 'circle'
    },
    tooltip: {
      pointFormat: '<b>{point.custom.pair}</b><br/>Frame: {point.custom.frame}<br/>Type: {point.custom.type}<br/>Conservation: {point.custom.consistency:.0%}'
    }
  }))

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
      text: `Interaction Timeline Matrix (${filteredData.length} pairs)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Frames (X-axis) × Residue Pairs (Y-axis) | Threshold: ${Math.round(dataStore.currentThreshold * 100)}%`,
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
        style: {
          fontSize: '11px',
          fontWeight: '500',
          color: '#1d1d1f'
        },
        formatter: function() {
          const index = Math.round(this.value)
          return pairLabels[index] || ''
        }
      },
      gridLineWidth: 1,
      gridLineColor: '#e8e8ed',
      reversed: false
    },
    legend: {
      enabled: true,
      align: 'right',
      verticalAlign: 'top',
      layout: 'vertical',
      itemStyle: {
        fontSize: '12px',
        fontWeight: '500',
        color: '#1d1d1f'
      },
      maxHeight: 400,
      navigation: {
        activeColor: '#3B6EF5',
        inactiveColor: '#6e6e73'
      }
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
  await loadDistanceData()
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.currentThreshold,
  () => dataStore.filteredInteractions.length,
  () => dataStore.selectedInteractionTypes.size,
  () => dataStore.totalFrames,
  () => dataStore.currentSystem?.id
], async () => {
  if (dataStore.currentChartType === 'timePairMatrix') {
    if (dataStore.currentSystem?.id && !distanceData.value) {
      await loadDistanceData()
    }
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
div {
  width: 100%;
  height: 100%;
}
</style>

