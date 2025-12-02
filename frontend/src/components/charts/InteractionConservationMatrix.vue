<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="slider-group">
        <label for="conservation-slider" class="slider-label">
          Interaction Type Conservation Threshold
        </label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="conservation-slider"
              type="range"
              min="0.5"
              max="1.0"
              step="0.1"
              :value="conservationThreshold"
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
              :value="Math.round(conservationThreshold * 100)"
              @input="updateThresholdFromInput"
              @blur="validateThresholdInput"
              min="50"
              max="100"
              step="1"
              class="value-input"
            />
            <span class="percent-symbol">%</span>
          </div>
        </div>
      </div>
      <div class="info-notice">
        <strong>Note:</strong> Only showing stable pairs (≥50% overall conservation)
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
const conservationThreshold = ref(0.5) // Default 50%

const conservationTicks = computed(() => {
  const ticks = []
  for (let value = 0.5; value <= 1.0 + 0.0001; value += 0.1) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

const updateThreshold = (event) => {
  conservationThreshold.value = parseFloat(event.target.value)
  updateChart()
}

const updateThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 50 && value <= 100) {
    conservationThreshold.value = value / 100
    updateChart()
  }
}

const validateThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = Math.round(conservationThreshold.value * 100)
    return
  }
  // Clamp value between 50 and 100
  value = Math.max(50, Math.min(100, value))
  event.target.value = value
  conservationThreshold.value = value / 100
  updateChart()
}

const updateChart = () => {
  if (!chartContainer.value) return

  const allInteractions = dataStore.interactions

  if (allInteractions.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found.</div>'
    return
  }

  // LEVEL 1: Filter pairs by overall conservation (≥50%)
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= 0.50)

  if (stablePairs.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No stable pairs found (≥50% conservation).</div>'
    return
  }

  // Create unique residue pairs and sort them
  const pairMap = new Map()
  stablePairs.forEach(interaction => {
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

  const totalFrames = dataStore.totalFrames

  // Prepare data: group by interaction type for each pair-frame combination
  // LEVEL 2: Only show interaction types with conservation ≥ threshold
  const seriesMap = new Map() // type -> data points

  // Track which pairs have at least one type meeting threshold
  const visiblePairIndices = new Set()
  
  // First pass: collect all types per pair to determine vertical stacking
  const pairTypeCount = new Map() // pairIndex -> Set of types
  
  sortedPairs.forEach((pairData, pairIndex) => {
    pairData.interactions.forEach(interaction => {
      const typePersistence = interaction.typePersistence || {}
      
      interaction.typesArray.forEach((type) => {
        const typeConservation = typePersistence[type] || 0
        
        if (typeConservation >= conservationThreshold.value) {
          if (!pairTypeCount.has(pairIndex)) {
            pairTypeCount.set(pairIndex, new Set())
          }
          pairTypeCount.get(pairIndex).add(type)
        }
      })
    })
  })
  
  // Create type index map for each pair
  const pairTypeIndexMap = new Map() // pairIndex -> Map(type -> index)
  pairTypeCount.forEach((types, pairIndex) => {
    const typeArray = Array.from(types).sort()
    const indexMap = new Map()
    typeArray.forEach((type, idx) => {
      indexMap.set(type, idx)
    })
    pairTypeIndexMap.set(pairIndex, { count: typeArray.length, indexMap })
  })

  sortedPairs.forEach((pairData, pairIndex) => {
    pairData.interactions.forEach(interaction => {
      const typeFrames = interaction.typeFrames || {}
      const typePersistence = interaction.typePersistence || {}
      
      // For each interaction type, check if its conservation meets threshold
      interaction.typesArray.forEach((type) => {
        const typeConservation = typePersistence[type] || 0
        
        // LEVEL 2 FILTER: Only show if type conservation ≥ threshold
        if (typeConservation < conservationThreshold.value) {
          return // Skip this interaction type
        }

        // Mark this pair as visible
        visiblePairIndices.add(pairIndex)

        if (!seriesMap.has(type)) {
          seriesMap.set(type, [])
        }
        
        // Get frames for this type
        let framesForType = []
        
        if (typeConservation >= 0.9999) {
          // This type appears in 100% of frames
          framesForType = Array.from({ length: totalFrames }, (_, i) => i + 1)
        } else {
          // Get frames where this specific type actually occurs
          if (!typeFrames[type] || !Array.isArray(typeFrames[type]) || typeFrames[type].length === 0) {
            return
          }
          framesForType = typeFrames[type]
        }
        
        // Calculate y position with smart vertical distribution
        const pairKey = `${interaction.id1}_${interaction.id2}`
        const typeInfo = pairTypeIndexMap.get(pairIndex)
        let yOffset = 0
        
        if (typeInfo && typeInfo.count > 1) {
          // Multiple types in this pair: distribute evenly within safe zone
          const typeIndex = typeInfo.indexMap.get(type)
          const maxOffset = 0.3 // Stay within ±0.3 of center (well within ±0.5 boundaries)
          const step = (2 * maxOffset) / Math.max(1, typeInfo.count - 1)
          yOffset = -maxOffset + (typeIndex * step)
        }
        // If only one type, yOffset stays at 0 (centered)
        
        // Create data points for frames
        framesForType.forEach(frameNum => {
          if (frameNum < 1 || frameNum > totalFrames) {
            return
          }
          
          // Get distance for this pair-frame-type combination
          const distances = distanceData.value?.distances?.[pairKey]
          const distance = distances?.[frameNum]?.[type] || null
          
          // Calculate final y position: center of row + vertical offset
          // Clamp to safe zone to ensure dots stay well within their rectangle
          const yPosition = Math.max(pairIndex - 0.35, Math.min(pairIndex + 0.35, pairIndex + yOffset))
          
          seriesMap.get(type).push({
            x: frameNum - 1,
            y: yPosition,
            frame: frameNum,
            pair: pairData.pair,
            type: type,
            pairConsistency: interaction.consistency,
            typeConservation: typeConservation,
            distance: distance,
            custom: {
              pair: pairData.pair,
              frame: frameNum,
              type: type,
              pairConsistency: interaction.consistency,
              typeConservation: typeConservation,
              typesArray: interaction.typesArray,
              distance: distance
            }
          })
        })
      })
    })
  })

  // Filter sortedPairs to only include visible ones
  const visiblePairs = sortedPairs.filter((_, idx) => visiblePairIndices.has(idx))
  
  if (visiblePairs.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interaction types meet the ${Math.round(conservationThreshold.value * 100)}% conservation threshold in stable pairs.</div>`
    return
  }

  // Remap pair indices for visible pairs only
  const oldToNewIndexMap = new Map()
  visiblePairIndices.forEach((oldIdx, newIdx) => {
    oldToNewIndexMap.set(oldIdx, newIdx)
  })

  // Update y positions in series data
  seriesMap.forEach((dataPoints) => {
    dataPoints.forEach(point => {
      const oldPairIndex = sortedPairs.findIndex(p => p.pair === point.pair)
      if (oldToNewIndexMap.has(oldPairIndex)) {
        const newPairIndex = Array.from(visiblePairIndices).indexOf(oldPairIndex)
        const jitterOffset = point.y - oldPairIndex
        point.y = newPairIndex + jitterOffset
      }
    })
  })

  const pairLabels = visiblePairs.map(p => p.pair)

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
    }
  }))

  if (chart) {
    chart.destroy()
  }

  chart = Highcharts.chart(chartContainer.value, {
    chart: {
      type: 'scatter',
      backgroundColor: 'transparent',
      height: Math.max(600, visiblePairs.length * 25 + 200),
      zoomType: 'xy'
    },
    title: {
      text: `Interaction Conservation Matrix (${visiblePairs.length} stable pairs)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Showing stable pairs (≥50% overall) with interaction types ≥${Math.round(conservationThreshold.value * 100)}% conservation`,
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
          return this.value + 1
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
      max: visiblePairs.length - 0.5,
      tickPositions: Array.from({ length: visiblePairs.length }, (_, i) => i),
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
          const index = Math.max(0, Math.min(visiblePairs.length - 1, rawIndex))
          const label = pairLabels[index]
          return label ? `<div style="display: flex; align-items: center; justify-content: flex-end; height: 100%; line-height: 1;">${label}</div>` : ''
        }
      },
      gridLineWidth: 0,
      tickWidth: 0,
      reversed: false,
      softMin: -0.5,
      softMax: visiblePairs.length - 0.5,
      startOnTick: false,
      endOnTick: false,
      plotLines: Array.from({ length: visiblePairs.length + 1 }, (_, i) => ({
        value: i - 0.5,
        color: '#e8e8ed',
        width: 1,
        zIndex: 1
      }))
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
          x: 0,
          y: 0
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
            <div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Type Conservation: </span>
              <span style="color: #6e6e73;">${Math.round((custom.typeConservation || point.typeConservation || 0) * 100)}%</span>
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Pair Conservation: </span>
              <span style="color: #6e6e73;">${Math.round((custom.pairConsistency || point.pairConsistency || 0) * 100)}%</span>
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
  () => dataStore.interactions.length,
  () => dataStore.totalFrames,
  () => dataStore.currentSystem?.id
], async () => {
  if (dataStore.currentChartType === 'interactionConservationMatrix') {
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
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
  padding: 20px;
  background: #f5f5f7;
  border-radius: 12px;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slider-label {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 0;
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

input[type="range"]::-moz-range-thumb {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.15s ease;
}

input[type="range"]::-moz-range-thumb:hover {
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

.info-notice {
  font-size: 14px;
  color: #1d1d1f;
  padding: 12px 16px;
  background: #ffffff;
  border-left: 4px solid #3B6EF5;
  border-radius: 8px;
}

.info-notice strong {
  font-weight: 700;
  color: #3B6EF5;
}

.chart-container {
  width: 100%;
  height: 100%;
}
</style>
