<template>
  <div class="chart-wrapper">
    <div class="chart-area">
      <div v-if="chartLoading" class="chart-loading-overlay">
        <div class="chart-loading-spinner"></div>
        <p>Building matrix...</p>
      </div>
      <div ref="chartContainer" class="chart-container"></div>
    </div>
    
    <div class="chart-toolbar">
      <!-- Pair Conservation Threshold (like FilteredHeatmap) -->
      <div class="slider-group">
        <label for="pair-conservation-slider" class="slider-label">
          Pair Conservation Threshold
          <span class="info-icon" @mouseenter="showTooltip($event, 'Filter residue pairs by their overall conservation. Only pairs present in at least this percentage of trajectory frames will be shown.')" @mouseleave="hideTooltip">ⓘ</span>
        </label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="pair-conservation-slider"
              type="range"
              min="0"
              max="1.0"
              step="0.1"
              :value="dataStore.currentThreshold"
              @input="updatePairThreshold"
            />
            <div class="slider-ticks">
              <span
                v-for="tick in pairConservationTicks"
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
              :value="Math.round(dataStore.currentThreshold * 100)"
              @input="updatePairThresholdFromInput"
              @blur="validatePairThresholdInput"
              min="0"
              max="100"
              step="10"
              class="value-input"
            />
            <span class="percent-symbol">%</span>
          </div>
        </div>
        <p class="slider-description">Show pairs present in at least {{ Math.round(dataStore.currentThreshold * 100) }}% of frames</p>
      </div>
      
      <!-- Type Conservation Threshold -->
      <div class="slider-group">
        <label for="conservation-slider" class="slider-label">
          Interaction Type Conservation Threshold
          <span class="info-icon" @mouseenter="showTooltip($event, 'Filter interaction types by their conservation within each pair. Only interaction types present in at least this percentage of frames (for a given pair) will be displayed.')" @mouseleave="hideTooltip">ⓘ</span>
        </label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="conservation-slider"
              type="range"
              min="0.5"
              max="1.0"
              step="0.1"
              :value="dataStore.typeConservationThreshold"
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
              :value="Math.round(dataStore.typeConservationThreshold * 100)"
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
      <div class="atom-change-selector">
        <label class="selector-label">
          <span class="label-icon">●</span>
          Atom Change Detection Mode
        </label>
        <div class="selector-wrapper">
          <select 
            v-model="atomChangeMode" 
            @change="updateChart"
            class="mode-select"
          >
            <option 
              v-for="option in atomChangeModeOptions" 
              :key="option.value" 
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
          <span class="select-arrow">▼</span>
        </div>
        <p class="selector-description">
          {{ atomChangeModeOptions.find(o => o.value === atomChangeMode)?.description }}
        </p>
      </div>
    </div>
    
    <!-- Global Tooltip for slider info icons -->
    <Teleport to="body">
      <div 
        v-if="activeTooltip.visible" 
        class="global-tooltip"
        :style="{ top: activeTooltip.y + 'px', left: activeTooltip.x + 'px' }"
      >
        {{ activeTooltip.text }}
      </div>
    </Teleport>
    
    
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
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import HeatmapModule from 'highcharts/modules/heatmap'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor, matchesSelectedTypes, formatResiduePairFromIds, formatPairKey, parseResidueId } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'
import api from '../../services/api'
import InteractionTrajectoryModal from '../analysis/InteractionTrajectoryModal.vue'

HeatmapModule(Highcharts)

// Initialize heatmap module
if (typeof Highcharts === 'object') {
  HeatmapModule(Highcharts)
}

const dataStore = useDataStore()
const chartContainer = ref(null)
const chartLoading = ref(false)
let chart = null
const distanceData = ref(null)
const atomPairDataByPair = ref(new Map()) // Map<pairKey, atomPairData>
// Type conservation threshold now uses dataStore.typeConservationThreshold (shared across charts)
// pairConservationThreshold now uses dataStore.currentThreshold (shared with ConservationAnalysis)
const showTrajectoryModal = ref(false)
const selectedInteraction = ref(null)
  const hiddenTypes = ref(new Set()) // Track hidden interaction types from legend clicks
  const atomChangeMode = ref('previous') // 'previous' | 'dominant' | 'first'


// Global tooltip state
const activeTooltip = ref({
  visible: false,
  text: '',
  x: 0,
  y: 0
})

// Show tooltip at cursor position
const showTooltip = (event, text) => {
  const x = event.clientX + 12
  const y = event.clientY - 8
  activeTooltip.value = {
    visible: true,
    text: text,
    x: Math.min(x, window.innerWidth - 340),
    y: y
  }
}

// Hide tooltip
const hideTooltip = () => {
  activeTooltip.value.visible = false
}

// Tooltip descriptions for each metric
const residueTooltips = computed(() => ({
  cr: `Count of unique residue pairs present in ≥${Math.round(dataStore.currentThreshold * 100)}% of trajectory frames`,
  count: 'Total number of conservation score samples from all qualifying pairs',
  mean: 'Average pair conservation across all interactions meeting the threshold',
  median: 'Middle value of sorted conservation scores; half above, half below',
  q1: '25% of pairs have conservation below this value',
  q3: '75% of pairs have conservation below this value',
  min: 'Lowest conservation value among pairs meeting the threshold',
  max: 'Highest conservation value among pairs meeting the threshold',
  stdDev: 'Spread of values around the mean; higher means more variability',
  mostConserved: 'Pair(s) with highest average conservation across all interaction types',
  leastConserved: 'Pair(s) with lowest average conservation among qualifying pairs',
  longestStretch: 'Maximum consecutive frames where the pair maintains any interaction'
}))

const atomicTooltips = computed(() => ({
  ca: `Count of pair-type combinations (residue pair + interaction type) with ≥${Math.round(dataStore.typeConservationThreshold * 100)}% type conservation`,
  count: 'Total number of type conservation score samples meeting the threshold',
  mean: 'Average type conservation across all qualifying pair-type combinations',
  median: 'Middle value of sorted type conservation scores',
  q1: '25% of interaction types have conservation below this value',
  q3: '75% of interaction types have conservation below this value',
  min: 'Lowest type conservation among qualifying pair-type combinations',
  max: 'Highest type conservation among qualifying pair-type combinations',
  stdDev: 'Spread of type conservation values; higher means more variability',
  mostConserved: 'Interaction type(s) with highest average conservation, with their specific pairs',
  leastConserved: 'Interaction type(s) with lowest conservation among those meeting threshold',
  longestStretch: 'Maximum consecutive frames where a specific interaction type persists'
}))

// Atom change comparison mode options
const atomChangeModeOptions = [
  { value: 'previous', label: 'Previous Frame', description: 'Compare with the immediately preceding frame' },
  { value: 'dominant', label: 'Most Dominant Atom Pair', description: 'Compare with the most frequently occurring atom pair' },
  { value: 'first', label: 'First Frame', description: 'Compare with the first frame where interaction appears' }
]

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

const pairConservationTicks = computed(() => {
  const ticks = []
  for (let value = 0; value <= 1.0 + 0.0001; value += 0.1) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

const updateThreshold = (event) => {
  dataStore.setTypeConservationThreshold(parseFloat(event.target.value))
  updateChart()
}

// Pair conservation threshold functions — write to shared store
const updatePairThreshold = (event) => {
  dataStore.setThreshold(parseFloat(event.target.value))
  updateChart()
}

const updatePairThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    dataStore.setThreshold(value / 100)
    updateChart()
  }
}

const validatePairThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = Math.round(dataStore.currentThreshold * 100)
    return
  }
  // Clamp value between 0 and 100
  value = Math.max(0, Math.min(100, value))
  event.target.value = value
  dataStore.setThreshold(value / 100)
  updateChart()
}

const updateThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 50 && value <= 100) {
    dataStore.setTypeConservationThreshold(value / 100)
    updateChart()
  }
}

const validateThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = Math.round(dataStore.typeConservationThreshold * 100)
    return
  }
  // Clamp value between 50 and 100
  value = Math.max(50, Math.min(100, value))
  event.target.value = value
  dataStore.setTypeConservationThreshold(value / 100)
  updateChart()
}

const handleOpenAtomPairExplorer = (data) => {
  showTrajectoryModal.value = false
  console.log('Open atom pair explorer for:', data)
}


// Helper to check if a type is hidden (handles naming variations using keyword matching)
const isTypeHidden = (typeName) => {
  // Direct match first
  if (hiddenTypes.value.has(typeName)) return true
  
  const typeNameLower = typeName.toLowerCase()
  
  // Check if any hidden type matches via keywords
  for (const hiddenType of hiddenTypes.value) {
    const hiddenTypeLower = hiddenType.toLowerCase()
    
    // Direct match (case-insensitive)
    if (typeNameLower === hiddenTypeLower) return true
    
    // Check via INTERACTION_TYPES keywords
    for (const interactionType of INTERACTION_TYPES) {
      const keywords = interactionType.keywords || []
      const labelLower = interactionType.label.toLowerCase()
      
      // If hidden type matches this INTERACTION_TYPE
      const hiddenMatchesType = hiddenTypeLower === labelLower || 
        keywords.some(kw => hiddenTypeLower.includes(kw.toLowerCase()))
      
      // If current type also matches this INTERACTION_TYPE
      const typeMatchesType = typeNameLower === labelLower || 
        keywords.some(kw => typeNameLower.includes(kw.toLowerCase()))
      
      // If both match the same INTERACTION_TYPE, the type is hidden
      if (hiddenMatchesType && typeMatchesType) return true
    }
  }
  
  return false
}

const updateChart = async () => {
  if (!chartContainer.value) return

  chartLoading.value = true
  try {
  // Load atom pair data for all pairs first (if not already loaded)
  await loadAtomPairDataForAllPairs()

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

  // LEVEL 1: Filter pairs by overall conservation (using pairConservationThreshold)
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= dataStore.currentThreshold)

  if (stablePairs.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No pairs found with ≥${Math.round(dataStore.currentThreshold * 100)}% conservation.</div>`
    return
  }

  // Create unique residue pairs and sort them
  const pairMap = new Map()
  stablePairs.forEach(interaction => {
    const pairKey = formatResiduePairFromIds(interaction.id1, interaction.id2)
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
        if (typeConservation < dataStore.typeConservationThreshold) {
          return
        }
        
        // Check if type matches selected interaction types filter
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return // Skip this type if it doesn't match filter
          }
        }
        
        // Check if type is hidden via legend click
        if (isTypeHidden(type)) {
          return // Skip hidden types
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
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interaction types meet the ${Math.round(dataStore.typeConservationThreshold * 100)}% conservation threshold in stable pairs.</div>`
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
        if (typeConservation < dataStore.typeConservationThreshold) {
          return // Skip this interaction type
        }
        
        // LEVEL 3 FILTER: Only show if type matches selected interaction types
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return // Skip this type if it doesn't match filter
          }
        }
        
        // LEVEL 4 FILTER: Skip if hidden via legend click
        if (isTypeHidden(type)) {
          return
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
        
        const pairKey = formatPairKey(interaction.id1, interaction.id2)
        const framesSet = new Set(framesForType)
        
        // Create a cell for EACH frame (colored if present, will be filtered by heatmap)
        for (let frameNum = 1; frameNum <= totalFrames; frameNum++) {
          const isPresent = framesSet.has(frameNum)
          
          if (isPresent) {
            // Get distance for this frame
            const distances = distanceData.value?.distances?.[pairKey]
            const distance = distances?.[frameNum]?.[type] || null
            
            seriesMap.get(type).push({
              x: frameNum,  // Frame number (1-indexed)
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

  // Create labels for Y-axis: just the pair
  const pairTypeLabels = pairTypeCombinations.map(pt => pt.pair)
  
  // Count unique pairs for the chart title
  const uniquePairCount = new Set(pairTypeCombinations.map(pt => pt.pair)).size
  

  // Create separate heatmap series for each interaction type (like TimePairMatrix)
  // This allows legend click to show/hide each type
  const series = []
  const allDataPoints = [] // For atom change detection
  
  // Track which types have data in seriesMap
  const typesWithData = new Set(seriesMap.keys())
  
  // Create series for types with data
  Array.from(seriesMap.entries()).sort((a, b) => a[0].localeCompare(b[0])).forEach(([type, dataPoints]) => {
    const seriesData = dataPoints.map(point => {
      const dataPoint = {
        x: point.x,
        y: point.y,
        value: 1,
        custom: point.custom,
        pair: point.pair,
        type: point.type,
        frame: point.frame,
        pairConsistency: point.pairConsistency,
        typeConservation: point.typeConservation,
        distance: point.distance
      }
      allDataPoints.push(dataPoint)
      return dataPoint
    })
    
    series.push({
      type: 'heatmap',
      name: type,
      data: seriesData,
      color: getInteractionBaseColor(type),
      borderWidth: 1,
      borderColor: '#e8e8ed',
      nullColor: 'transparent',
      colsize: 1,
      rowsize: 1,
      dataLabels: {
        enabled: false
      },
      showInLegend: true,
      visible: true,
      _hasData: true
    })
  })
  
  // Track which type labels are already in series (to avoid duplicates)
  const existingSeriesNames = new Set(series.map(s => s.name.toLowerCase()))
  
  // Helper to check if an INTERACTION_TYPE matches the selected filter
  const typeMatchesFilter = (interactionType) => {
    if (dataStore.selectedInteractionTypes.size === 0) return true
    return dataStore.selectedInteractionTypes.has(interactionType.id)
  }
  
  // Helper to check if type already exists in series (using keyword matching)
  const typeExistsInSeries = (interactionType) => {
    const keywords = interactionType.keywords || []
    for (const seriesName of existingSeriesNames) {
      if (seriesName === interactionType.label.toLowerCase()) return true
      if (keywords.some(kw => seriesName.includes(kw.toLowerCase()))) return true
    }
    return false
  }
  
  // Add ALL interaction types to legend (those without data get empty array and _hasData: false)
  INTERACTION_TYPES.forEach(interactionType => {
    // Only add if it matches the selected filter
    if (!typeMatchesFilter(interactionType)) return
    
    // Only add if not already in series
    if (typeExistsInSeries(interactionType)) return
    
    const typeName = interactionType.label
    
    series.push({
      type: 'heatmap',
      name: typeName,
      data: [],
      color: getInteractionBaseColor(typeName),
      borderWidth: 1,
      borderColor: '#e8e8ed',
      nullColor: 'transparent',
      colsize: 1,
      rowsize: 1,
      dataLabels: {
        enabled: false
      },
      showInLegend: true,
      _hasData: false
    })
  })
  
  // Collect data points where atoms change
  const atomChangeData = []
  allDataPoints.forEach(point => {
    const pairString = point.custom?.pair || point.pair || ''
    const pairParts = pairString.split(' ↔ ')
    const pairKey = pairParts.length === 2
      ? formatPairKey(pairParts[0], pairParts[1])
      : pairString
    
    // Skip if frame is 1 (no previous frame to compare)
    const frame = point.custom?.frame || point.frame
    if (frame <= 1) return
    
    const type = point.custom?.type || point.type
    
    if (hasAtomChange(pairKey, frame, type)) {
      atomChangeData.push({
        x: point.x,
        y: point.y,
        pair: pairString,
        type: type,
        frame: frame,
        // Include all data needed for the modal
        pairConsistency: point.custom?.pairConsistency || point.pairConsistency,
        typeConservation: point.custom?.typeConservation || point.typeConservation,
        distance: point.custom?.distance || point.distance,
        custom: {
          pair: pairString,
          type: type,
          frame: frame,
          pairConsistency: point.custom?.pairConsistency || point.pairConsistency,
          typeConservation: point.custom?.typeConservation || point.typeConservation,
          distance: point.custom?.distance || point.distance,
          allFrames: point.custom?.allFrames || []
        }
      })
    }
  })
  
  // Add scatter series for atom change indicators
  if (atomChangeData.length > 0) {
    series.push({
      type: 'scatter',
      name: 'Atom Changes',
      color: '#FF9500', // Distinct orange color
      data: atomChangeData,
      marker: {
        symbol: 'circle',
        radius: 4,
        fillColor: '#FF9500',
        lineColor: '#FFFFFF',
        lineWidth: 1
      },
      showInLegend: true,
      enableMouseTracking: true,
      cursor: 'pointer',
      zIndex: 10 // Above heatmap
    })
  }

  if (chart) {
    chart.destroy()
  }

  const chartOptions = {
    chart: {
      type: 'heatmap',
      backgroundColor: 'transparent',
      height: Math.max(600, pairTypeCombinations.length * 25 + 200),
      marginLeft: 250,
      marginRight: 200
    },
    title: {
      text: `${dataStore.currentSystem?.name || 'System'} - Interaction Conservation Timeline (${pairTypeCombinations.length} pair-type combinations, ${uniquePairCount} unique pairs)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: null
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
      min: 0.5,
      max: totalFrames + 0.5,
      tickInterval: Math.max(1, Math.floor(totalFrames / 20)),
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#6e6e73'
        },
        formatter: function() {
          return Math.round(this.value)
        }
      },
      gridLineWidth: 0,  // Disable default grid lines
      lineWidth: 1,
      lineColor: '#d2d2d7',
      tickWidth: 1,
      tickColor: '#d2d2d7',
      plotLines: Array.from({ length: totalFrames + 1 }, (_, i) => ({
        value: i + 0.5,
        color: '#e8e8ed',
        width: 1,
        zIndex: 1
      }))
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
    plotOptions: {
      heatmap: {
        cursor: 'pointer',
        borderWidth: 1,
        borderColor: '#e8e8ed',
        events: {
          legendItemClick: function() {
            const typeName = this.name
            // Toggle hidden state using keyword matching
            if (isTypeHidden(typeName)) {
              // Un-hide: remove all related type names from hiddenTypes
              const toRemove = []
              for (const hiddenType of hiddenTypes.value) {
                // Check if hiddenType is related to clicked typeName
                const hiddenLower = hiddenType.toLowerCase()
                const clickedLower = typeName.toLowerCase()
                
                // Direct match
                if (hiddenLower === clickedLower) {
                  toRemove.push(hiddenType)
                  continue
                }
                
                // Check via INTERACTION_TYPES keywords
                for (const interactionType of INTERACTION_TYPES) {
                  const keywords = interactionType.keywords || []
                  const labelLower = interactionType.label.toLowerCase()
                  
                  const hiddenMatchesType = hiddenLower === labelLower || 
                    keywords.some(kw => hiddenLower.includes(kw.toLowerCase()))
                  const clickedMatchesType = clickedLower === labelLower || 
                    keywords.some(kw => clickedLower.includes(kw.toLowerCase()))
                  
                  if (hiddenMatchesType && clickedMatchesType) {
                    toRemove.push(hiddenType)
                    break
                  }
                }
              }
              toRemove.forEach(t => hiddenTypes.value.delete(t))
            } else {
              // Hide: add the clicked type name
              hiddenTypes.value.add(typeName)
            }
            // Rebuild chart with updated visibility
            setTimeout(() => updateChart(), 10)
            // Prevent default Highcharts behavior (we handle it ourselves)
            return false
          }
        },
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
      },
      scatter: {
        cursor: 'pointer',
        events: {
          legendItemClick: function() {
            const typeName = this.name
            // Don't handle "Atom Changes" series - let it use default behavior
            if (typeName === 'Atom Changes') {
              return true
            }
            // Toggle hidden state using keyword matching
            if (isTypeHidden(typeName)) {
              // Un-hide: remove all related type names from hiddenTypes
              const toRemove = []
              for (const hiddenType of hiddenTypes.value) {
                const hiddenLower = hiddenType.toLowerCase()
                const clickedLower = typeName.toLowerCase()
                
                if (hiddenLower === clickedLower) {
                  toRemove.push(hiddenType)
                  continue
                }
                
                for (const interactionType of INTERACTION_TYPES) {
                  const keywords = interactionType.keywords || []
                  const labelLower = interactionType.label.toLowerCase()
                  
                  const hiddenMatchesType = hiddenLower === labelLower || 
                    keywords.some(kw => hiddenLower.includes(kw.toLowerCase()))
                  const clickedMatchesType = clickedLower === labelLower || 
                    keywords.some(kw => clickedLower.includes(kw.toLowerCase()))
                  
                  if (hiddenMatchesType && clickedMatchesType) {
                    toRemove.push(hiddenType)
                    break
                  }
                }
              }
              toRemove.forEach(t => hiddenTypes.value.delete(t))
            } else {
              hiddenTypes.value.add(typeName)
            }
            // Rebuild chart with updated visibility
            setTimeout(() => updateChart(), 10)
            return false
          }
        },
        point: {
          events: {
            click: function() {
              const point = this
              // Open trajectory modal for atom change dots
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
            }
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
      y: 60,
      useHTML: true,
      labelFormatter: function() {
        const hasData = this.options._hasData
        if (hasData) {
          return `<span style="font-weight: 700; font-size: 12px;">${this.name}</span>`
        } else {
          return `<span style="color: #9ca3af; font-weight: 400; font-size: 12px;">${this.name}</span>`
        }
      },
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
    series: series,
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      formatter: function() {
        const point = this.point
        const series = this.series
        
        // Handle atom change scatter series
        if (series.name === 'Atom Changes') {
          return `
            <div style="padding: 10px;">
              <div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">
                ${point.pair || 'Unknown'}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #1d1d1f; font-weight: 600;">Frame: </span>
                <span style="color: #6e6e73;">${point.frame}</span>
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #1d1d1f; font-weight: 600;">Interaction Type: </span>
                <span style="color: #6e6e73;">${point.type || 'N/A'}</span>
              </div>
              <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e8e8ed; font-size: 12px; color: #FF9500; font-weight: 600;">
                ⚠️ Atom pairs changed in this frame
              </div>
            </div>
          `
        }
        
        // Handle heatmap series
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
  }

  const systemName = dataStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `interaction-conservation-matrix-${systemName}`)
  if (!chartContainer.value) return
  chart = Highcharts.chart(chartContainer.value, exportOptions)
  } finally {
    chartLoading.value = false
  }
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

// Load atom pair data for a specific residue pair
const loadAtomPairDataForPair = async (pairKey, id1, id2) => {
  if (!dataStore.currentSystem) return null
  
  // Check if already loaded
  if (atomPairDataByPair.value.has(pairKey)) {
    return atomPairDataByPair.value.get(pairKey)
  }
  
  try {
    const res1 = parseResidueId(id1)
    const res2 = parseResidueId(id2)
    
    if (!res1 || !res2) {
      return null
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
    atomPairDataByPair.value.set(pairKey, response)
    return response
  } catch (error) {
    console.error(`Error loading atom pair data for ${pairKey}:`, error)
    return null
  }
}

// Load atom pair data for all unique pairs in the current filtered interactions (BATCH)
const loadAtomPairDataForAllPairs = async () => {
  if (!dataStore.currentSystem) return
  
  const allInteractions = dataStore.filteredInteractions
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= dataStore.currentThreshold)
  
  if (stablePairs.length === 0) return
  
  // Get unique pairs that haven't been loaded yet
  const pairsToLoad = []
  const uniquePairs = new Map()
  
  stablePairs.forEach(interaction => {
    const pairKey = formatPairKey(interaction.id1, interaction.id2)
    if (!uniquePairs.has(pairKey) && !atomPairDataByPair.value.has(pairKey)) {
      const res1 = parseResidueId(interaction.id1)
      const res2 = parseResidueId(interaction.id2)
      
      if (res1 && res2) {
        uniquePairs.set(pairKey, true)
        pairsToLoad.push({
          resName1: res1.resName,
          resNum1: res1.resNum,
          chain1: res1.chain,
          resName2: res2.resName,
          resNum2: res2.resNum,
          chain2: res2.chain,
          pairKey: pairKey
        })
      }
    }
  })
  
  // If nothing to load, return early
  if (pairsToLoad.length === 0) return
  
  try {
    // Make a single batch API call
    const batchResult = await api.getAtomPairsBatch(dataStore.currentSystem.id, pairsToLoad)
    
    // Store results in the cache, mapping the returned keys to our expected keys
    pairsToLoad.forEach(pair => {
      // The backend returns keys in format: "chain1-resName1resNum1_chain2-resName2resNum2"
      const backendKey = `${pair.chain1}-${pair.resName1}${pair.resNum1}_${pair.chain2}-${pair.resName2}${pair.resNum2}`
      
      if (batchResult[backendKey]) {
        atomPairDataByPair.value.set(pair.pairKey, batchResult[backendKey])
      }
    })
  } catch (error) {
    console.error('Error loading atom pair data batch:', error)
    // Fallback: load individually (slower but works)
    for (const pair of pairsToLoad) {
      await loadAtomPairDataForPair(pair.pairKey, 
        `${pair.chain1}-${pair.resName1}${pair.resNum1}`, 
        `${pair.chain2}-${pair.resName2}${pair.resNum2}`)
    }
  }
}

// Get atom pairs for a specific frame (returns array of atomPair strings)
const getAtomPairsForFrame = (atomPairData, frame) => {
  if (!atomPairData || !atomPairData.atomPairsByFrame) return []
  const frameKey = String(frame)
  const frameData = atomPairData.atomPairsByFrame[frameKey] || []
  // Return unique atom pair strings
  return [...new Set(frameData.map(entry => entry.atomPair))]
}

// Get atom pairs for a specific frame and type
const getAtomPairsForFrameAndType = (atomPairData, frame, type) => {
  if (!atomPairData || !atomPairData.atomPairsByFrame) return []
  const frameKey = String(frame)
  const frameData = atomPairData.atomPairsByFrame[frameKey] || []
  const typePairs = frameData
    .filter(entry => entry.interactionType === type)
    .map(entry => entry.atomPair)
  return [...new Set(typePairs)].sort()
}

// Get the most dominant (most frequent) atom pair set for a given type
const getDominantAtomPairs = (atomPairData, type) => {
  if (!atomPairData || !atomPairData.atomPairsByFrame) return []
  
  // Count frequency of each unique atom pair combination
  const combinationCounts = new Map()
  
  Object.keys(atomPairData.atomPairsByFrame).forEach(frameKey => {
    const frameData = atomPairData.atomPairsByFrame[frameKey] || []
    const typePairs = frameData
      .filter(entry => entry.interactionType === type)
      .map(entry => entry.atomPair)
    const uniqueSorted = [...new Set(typePairs)].sort()
    
    if (uniqueSorted.length > 0) {
      const key = uniqueSorted.join('|')
      combinationCounts.set(key, (combinationCounts.get(key) || 0) + 1)
    }
  })
  
  // Find the most frequent combination
  let maxCount = 0
  let dominantKey = ''
  combinationCounts.forEach((count, key) => {
    if (count > maxCount) {
      maxCount = count
      dominantKey = key
    }
  })
  
  return dominantKey ? dominantKey.split('|') : []
}

// Get the first frame where this interaction type appears
const getFirstFrameAtomPairs = (atomPairData, type) => {
  if (!atomPairData || !atomPairData.atomPairsByFrame) return []
  
  // Get all frame numbers and sort them
  const frameNumbers = Object.keys(atomPairData.atomPairsByFrame)
    .map(k => parseInt(k))
    .sort((a, b) => a - b)
  
  // Find the first frame with this interaction type
  for (const frameNum of frameNumbers) {
    const pairs = getAtomPairsForFrameAndType(atomPairData, frameNum, type)
    if (pairs.length > 0) {
      return pairs
    }
  }
  
  return []
}

// Check if two atom pair sets have ANY overlap (at least one common pair)
// Uses Set for O(n) performance instead of O(n*m)
const hasOverlap = (set1, set2) => {
  // Use smaller set for lookup creation (optimization)
  const [smaller, larger] = set1.length <= set2.length ? [set1, set2] : [set2, set1]
  const lookupSet = new Set(smaller)
  
  for (const pair of larger) {
    if (lookupSet.has(pair)) return true
  }
  return false
}

// Check if two sorted atom pair arrays are exactly equal
const atomPairSetsEqual = (set1, set2) => {
  if (set1.length !== set2.length) return false
  for (let i = 0; i < set1.length; i++) {
    if (set1[i] !== set2[i]) return false
  }
  return true
}

// Check if atoms changed based on selected comparison mode
// Returns true ONLY for TRUE CHANGES: when ALL atom pairs were replaced (no overlap)
// Does NOT flag additions (new pairs added) or deletions (pairs removed but others remain)
// Rationale: Additions/deletions are rare and don't provide biological insight
const hasAtomChange = (pairKey, frame, type) => {
  // pairKey format: "A-LYS8_B-ASP45" (from loadAtomPairDataForPair)
  const atomPairData = atomPairDataByPair.value.get(pairKey)
  if (!atomPairData) return false
  
  // Get current frame's atom pairs
  const currentPairs = getAtomPairsForFrameAndType(atomPairData, frame, type)
  
  // If current frame has no atoms for this type, not a change (it's a deletion)
  if (currentPairs.length === 0) return false
  
  let referencePairs = []
  
  switch (atomChangeMode.value) {
    case 'previous':
      // Compare with previous frame
      if (frame <= 1) return false // No previous frame
      referencePairs = getAtomPairsForFrameAndType(atomPairData, frame - 1, type)
      // If previous frame had no atoms, this is a new appearance (addition), not a change
      if (referencePairs.length === 0) return false
      break
      
    case 'dominant':
      // Compare with most frequent atom pair combination
      referencePairs = getDominantAtomPairs(atomPairData, type)
      // If no dominant pair found, no comparison possible
      if (referencePairs.length === 0) return false
      break
      
    case 'first':
      // Compare with first frame where this type appears
      referencePairs = getFirstFrameAtomPairs(atomPairData, type)
      // If no first frame found, no comparison possible
      if (referencePairs.length === 0) return false
      // If this IS the first frame (identical), no change
      if (atomPairSetsEqual(currentPairs, referencePairs)) return false
      break
      
    default:
      return false
  }
  
  // TRUE CHANGE detection: only flag if there is NO overlap between reference and current
  // - If ANY reference pair still exists in current → not a true change (could be addition/partial deletion)
  // - Only if ALL reference pairs were replaced with completely different pairs → true change
  return !hasOverlap(referencePairs, currentPairs)
}

onMounted(async () => {
  await loadDistanceData()
  await updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.interactions.length,
  () => dataStore.totalFrames,
  () => dataStore.currentSystem?.id,
  () => dataStore.selectedInteractionTypes.size,
  () => dataStore.currentThreshold,
  () => dataStore.typeConservationThreshold
], async () => {
  if (dataStore.currentChartType === 'interactionConservationMatrix') {
    if (dataStore.currentSystem?.id && !distanceData.value) {
      await loadDistanceData()
    }
    // Clear atom pair cache when system changes
    if (dataStore.currentSystem?.id) {
      atomPairDataByPair.value.clear()
    }
    await updateChart()
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
  padding: 20px 32px 0;
  margin-top: 8px;
  border-top: 1px solid #e8e8ed;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slider-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 0;
  letter-spacing: -0.022em;
}

.slider-label .info-icon {
  font-size: 14px;
  color: #8e8e93;
  cursor: pointer;
  transition: color 0.15s ease;
}

.slider-label .info-icon:hover {
  color: #3B6EF5;
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
  border-radius: 3px;
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

.slider-description {
  margin: 0;
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
  font-style: italic;
}

.atom-change-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e8e8ed;
}

.selector-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.022em;
}

.label-icon {
  color: #FF9500;
  font-size: 12px;
}

.selector-wrapper {
  position: relative;
  display: inline-flex;
  max-width: 320px;
}

.mode-select {
  appearance: none;
  -webkit-appearance: none;
  width: 100%;
  padding: 10px 40px 10px 14px;
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
  background: #f5f5f7;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.mode-select:hover {
  border-color: #b4b4bb;
  background: #f0f0f2;
}

.mode-select:focus {
  outline: none;
  border-color: #1d1d1f;
}

.select-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  color: #6e6e73;
  pointer-events: none;
}

.selector-description {
  margin: 0;
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
  font-style: italic;
}

.chart-area {
  position: relative;
  width: 100%;
  min-height: 400px;
}

.chart-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
  border-radius: 10px;
}

.chart-loading-overlay p {
  margin: 12px 0 0;
  font-size: 15px;
  font-weight: 500;
  color: #6e6e73;
}

.chart-loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e8e8ed;
  border-top-color: #007aff;
  border-radius: 50%;
  animation: chartSpin 0.9s linear infinite;
}

@keyframes chartSpin {
  to { transform: rotate(360deg); }
}

.chart-container {
  width: 100%;
  height: 100%;
}

/* Global tooltip - teleported to body to avoid clipping */
.global-tooltip {
  position: fixed;
  padding: 10px 14px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  white-space: normal;
  max-width: 320px;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  z-index: 100000;
  pointer-events: none;
  text-align: left;
  animation: tooltipFadeIn 0.15s ease;
}

@keyframes tooltipFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

</style>

