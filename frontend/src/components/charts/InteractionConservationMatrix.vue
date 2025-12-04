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
        <strong>Interaction Timeline View:</strong> Each row shows one residue pair + interaction type. Colored segments indicate frames where the interaction is present. Gaps show breaks in continuity. Hover for details, click for full analysis.
      </div>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
    
    <!-- Interaction Trajectory Modal -->
    <InteractionTrajectoryModal
      :visible="showTrajectoryModal"
      :interactionData="selectedInteraction"
      @close="showTrajectoryModal = false"
      @openAtomPairExplorer="handleOpenAtomPairExplorer"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import Highcharts from 'highcharts'
import HeatmapModule from 'highcharts/modules/heatmap'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'
import api from '../../services/api'
import InteractionTrajectoryModal from '../InteractionTrajectoryModal.vue'

// Initialize heatmap module
if (typeof Highcharts === 'object') {
  HeatmapModule(Highcharts)
}

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
const distanceData = ref(null)
const conservationThreshold = ref(0.5) // Default 50%
const showTrajectoryModal = ref(false)
const selectedInteraction = ref(null)

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

const handleOpenAtomPairExplorer = (data) => {
  showTrajectoryModal.value = false
  console.log('Open atom pair explorer for:', data)
}

const updateChart = () => {
  if (!chartContainer.value) return

  // Use filteredInteractions which already applies the interaction type filter
  const allInteractions = dataStore.filteredInteractions

  if (allInteractions.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try adjusting the threshold or interaction type filters.</div>'
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

  // Build list of pair-type combinations (each gets its own row)
  const pairTypeCombinations = []
  const pairTypeToRowIndex = new Map() // "pairKey_type" -> row index
  
  // First pass: collect all pair-type combinations that meet threshold
  sortedPairs.forEach((pairData) => {
    const typesForThisPair = new Set()
    
    pairData.interactions.forEach(interaction => {
      const typePersistence = interaction.typePersistence || {}
      
      interaction.typesArray.forEach((type) => {
        const typeConservation = typePersistence[type] || 0
        
        // Check if type meets conservation threshold
        if (typeConservation < conservationThreshold.value) {
          return
        }
        
        // Check if type matches selected interaction types filter
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return // Skip this type if it doesn't match filter
          }
        }
        
        typesForThisPair.add(type)
      })
    })
    
    // Sort types for consistent ordering
    const sortedTypes = Array.from(typesForThisPair).sort()
    
    // Create a row for each type
    sortedTypes.forEach(type => {
      const rowIndex = pairTypeCombinations.length
      pairTypeCombinations.push({
        pair: pairData.pair,
        type: type,
        pairData: pairData
      })
      pairTypeToRowIndex.set(`${pairData.pair}_${type}`, rowIndex)
    })
  })
  
  if (pairTypeCombinations.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interaction types meet the ${Math.round(conservationThreshold.value * 100)}% conservation threshold in stable pairs.</div>`
    return
  }

  // Second pass: create cell data for each pair-type-frame combination
  sortedPairs.forEach((pairData) => {
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
        
        // LEVEL 3 FILTER: Only show if type matches selected interaction types
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return // Skip this type if it doesn't match filter
          }
        }

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
        
        // Get the row index for this pair-type combination
        const rowIndex = pairTypeToRowIndex.get(`${pairData.pair}_${type}`)
        if (rowIndex === undefined) {
          return
        }
        
        const pairKey = `${interaction.id1}_${interaction.id2}`
        const framesSet = new Set(framesForType)
        
        // Create a cell for EACH frame (colored if present, will be filtered by heatmap)
        for (let frameNum = 1; frameNum <= totalFrames; frameNum++) {
          const isPresent = framesSet.has(frameNum)
          
          if (isPresent) {
            // Get distance for this frame
            const distances = distanceData.value?.distances?.[pairKey]
            const distance = distances?.[frameNum]?.[type] || null
            
            seriesMap.get(type).push({
              x: frameNum - 1,  // Frame (0-indexed for chart)
              y: rowIndex,
              value: 1,  // Present
              pair: pairData.pair,
              type: type,
              frame: frameNum,
              pairConsistency: interaction.consistency,
              typeConservation: typeConservation,
              distance: distance,
              custom: {
                pair: pairData.pair,
                type: type,
                frame: frameNum,
                pairConsistency: interaction.consistency,
                typeConservation: typeConservation,
                typesArray: interaction.typesArray,
                distance: distance,
                allFrames: framesForType
              }
            })
          }
        }
      })
    })
  })

  // Create labels for Y-axis: "Pair (Type)"
  const pairTypeLabels = pairTypeCombinations.map(pt => `${pt.pair} (${pt.type})`)

  // Combine all data into a single heatmap series
  // Each point needs [x, y, value] and color information
  const allData = []
  const interactionTypes = new Set()
  
  seriesMap.forEach((dataPoints, type) => {
    interactionTypes.add(type)
    dataPoints.forEach(point => {
      allData.push({
        x: point.x,
        y: point.y,
        value: 1,
        color: getInteractionBaseColor(type),
        custom: point.custom,
        pair: point.pair,
        type: point.type,
        frame: point.frame,
        pairConsistency: point.pairConsistency,
        typeConservation: point.typeConservation,
        distance: point.distance
      })
    })
  })
  
  // Main heatmap series with all data
  const series = [{
    type: 'heatmap',
    name: 'Interactions',
    data: allData,
    borderWidth: 1,
    borderColor: '#e8e8ed',
    nullColor: 'transparent',
    colsize: 1,
    rowsize: 1,
    dataLabels: {
      enabled: false
    },
    showInLegend: false
  }]
  
  // Add invisible scatter series for legend items (one per interaction type)
  Array.from(interactionTypes).sort().forEach(type => {
    series.push({
      type: 'scatter',
      name: type,
      color: getInteractionBaseColor(type),
      data: [],  // Empty data - just for legend
      marker: {
        symbol: 'square',
        radius: 7
      },
      showInLegend: true,
      enableMouseTracking: false
    })
  })

  if (chart) {
    chart.destroy()
  }

  chart = Highcharts.chart(chartContainer.value, {
    chart: {
      type: 'heatmap',
      backgroundColor: 'transparent',
      height: Math.max(600, pairTypeCombinations.length * 25 + 200),
      zoomType: 'xy',
      marginLeft: 250,
      marginRight: 200
    },
    title: {
      text: `Interaction Conservation Timeline (${pairTypeCombinations.length} pair-type combinations)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Stable pairs (≥50%) • Type conservation ≥${Math.round(conservationThreshold.value * 100)}% • Click any segment for detailed analysis`,
      style: {
        fontSize: '15px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    colors: null,  // Don't use default Highcharts color palette
    colorAxis: null,  // Disable any color axis
    xAxis: {
      title: {
        text: 'Frame Number',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: -0.5,
      max: totalFrames - 0.5,
      tickInterval: Math.max(1, Math.floor(totalFrames / 20)),
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#6e6e73'
        },
        formatter: function() {
          return Math.round(this.value) + 1
        }
      },
      gridLineWidth: 1,
      gridLineColor: '#e8e8ed',
      lineWidth: 1,
      lineColor: '#d2d2d7',
      tickWidth: 1,
      tickColor: '#d2d2d7'
    },
    yAxis: {
      title: {
        text: '',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: -0.5,
      max: pairTypeCombinations.length - 0.5,
      tickPositions: Array.from({ length: pairTypeCombinations.length }, (_, i) => i),
      labels: {
        align: 'right',
        x: -10,
        useHTML: true,
        style: {
          fontSize: '12px',
          fontWeight: '600',
          color: '#1d1d1f',
          textAlign: 'right',
          width: '220px',
          whiteSpace: 'nowrap',
          overflow: 'visible'
        },
        formatter: function() {
          const rawIndex = Math.round(this.value)
          const index = Math.max(0, Math.min(pairTypeCombinations.length - 1, rawIndex))
          const label = pairTypeLabels[index]
          return label ? `<div style="padding: 4px 0; width: 220px; text-overflow: ellipsis; overflow: hidden;" title="${label}">${label}</div>` : ''
        }
      },
      gridLineWidth: 0,
      lineWidth: 1,
      lineColor: '#d2d2d7',
      tickWidth: 1,
      tickColor: '#d2d2d7',
      reversed: false,
      startOnTick: false,
      endOnTick: false,
      plotLines: Array.from({ length: pairTypeCombinations.length + 1 }, (_, i) => ({
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
      heatmap: {
        cursor: 'pointer',
        borderWidth: 1,
        borderColor: '#e8e8ed',
        point: {
          events: {
            click: function() {
              const point = this
              selectedInteraction.value = {
                pair: point.custom?.pair || point.pair,
                type: point.custom?.type || point.type,
                frame: point.custom?.frame || point.frame,
                pairConsistency: point.custom?.pairConsistency || point.pairConsistency,
                typeConservation: point.custom?.typeConservation || point.typeConservation,
                distance: point.custom?.distance || point.distance,
                frames: point.custom?.allFrames || []
              }
              showTrajectoryModal.value = true
            },
            mouseOver: function() {
              const hoveredType = this.type
              // Dim all cells that are NOT of this type
              this.series.data.forEach(point => {
                if (point.type !== hoveredType) {
                  point.graphic?.attr({ opacity: 0.2 })
                }
              })
            },
            mouseOut: function() {
              // Restore all cells to full opacity
              this.series.data.forEach(point => {
                point.graphic?.attr({ opacity: 1 })
              })
            }
          }
        },
        states: {
          hover: {
            brightness: -0.1,
            borderColor: '#1d1d1f',
            borderWidth: 2
          }
        }
      }
    },
    colorAxis: false,
    legend: {
      enabled: true,
      align: 'right',
      verticalAlign: 'top',
      layout: 'vertical',
      x: -10,
      y: 80,
      symbolWidth: 20,
      symbolHeight: 14,
      itemStyle: {
        fontSize: '12px',
        fontWeight: '500',
        color: '#1d1d1f'
      },
      itemMarginTop: 3,
      itemMarginBottom: 3,
      padding: 10,
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderWidth: 1,
      borderColor: '#e8e8ed',
      borderRadius: 8,
      labelFormatter: function() {
        return this.name
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
        
        const frame = custom.frame || point.frame
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
              <span style="color: #6e6e73;">${frame}</span>
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
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e8e8ed; font-size: 12px; color: #86868b;">
              Click to view trajectory analysis
            </div>
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
  () => dataStore.currentSystem?.id,
  () => dataStore.selectedInteractionTypes.size
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
