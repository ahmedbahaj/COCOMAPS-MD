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
        <strong>Interaction Timeline View:</strong> Click on a segment for trajectory analysis.
      </div>
    </div>
    
    <div ref="chartContainer" class="chart-container"></div>
    
    <!-- Statistics Table -->
    <div v-if="statistics" class="statistics-section">
      <h3 class="statistics-title">Conservation Statistics</h3>
      <p class="statistics-description">
        Statistics based on current filters: ≥50% pair conservation, ≥{{ Math.round(conservationThreshold * 100) }}% type conservation{{ dataStore.selectedInteractionTypes.size > 0 ? ', filtered interaction types' : '' }}
      </p>
      <div class="statistics-tables">
        <div class="statistics-table-wrapper">
          <h4 class="table-subtitle">Residue Level (Pair Conservation)</h4>
          <table class="statistics-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr class="highlight-row">
                <td>CR50</td>
                <td>{{ statistics.residue.cr50 }} pairs</td>
              </tr>
              <tr>
                <td>Count</td>
                <td>{{ statistics.residue.count }}</td>
              </tr>
              <tr>
                <td>Mean</td>
                <td>{{ formatPercent(statistics.residue.mean) }}</td>
              </tr>
              <tr>
                <td>Median (Q2)</td>
                <td>{{ formatPercent(statistics.residue.median) }}</td>
              </tr>
              <tr>
                <td>Q1 (25th percentile)</td>
                <td>{{ formatPercent(statistics.residue.q1) }}</td>
              </tr>
              <tr>
                <td>Q3 (75th percentile)</td>
                <td>{{ formatPercent(statistics.residue.q3) }}</td>
              </tr>
              <tr>
                <td>Min</td>
                <td>{{ formatPercent(statistics.residue.min) }}</td>
              </tr>
              <tr>
                <td>Max</td>
                <td>{{ formatPercent(statistics.residue.max) }}</td>
              </tr>
              <tr>
                <td>Std Dev</td>
                <td>{{ formatPercent(statistics.residue.stdDev) }}</td>
              </tr>
              <tr class="info-row">
                <td>Most Conserved Pair(s)</td>
                <td>{{ statistics.residue.mostConserved }} ({{ formatPercent(statistics.residue.mostConservedValue) }})</td>
              </tr>
              <tr class="info-row">
                <td>Least Conserved Pair(s)</td>
                <td>{{ statistics.residue.leastConserved }} ({{ formatPercent(statistics.residue.leastConservedValue) }})</td>
              </tr>
              <tr class="info-row">
                <td>Longest Conserved Stretch</td>
                <td>{{ statistics.residue.longestStretchPair }}: {{ statistics.residue.longestStretchInfo }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="statistics-table-wrapper">
          <h4 class="table-subtitle">Atomic Level (Type Conservation)</h4>
          <table class="statistics-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr class="highlight-row">
                <td>CA{{ Math.round(conservationThreshold * 100) }}</td>
                <td>{{ statistics.atomic.ca }} pair-type combinations</td>
              </tr>
              <tr>
                <td>Count</td>
                <td>{{ statistics.atomic.count }}</td>
              </tr>
              <tr>
                <td>Mean</td>
                <td>{{ formatPercent(statistics.atomic.mean) }}</td>
              </tr>
              <tr>
                <td>Median (Q2)</td>
                <td>{{ formatPercent(statistics.atomic.median) }}</td>
              </tr>
              <tr>
                <td>Q1 (25th percentile)</td>
                <td>{{ formatPercent(statistics.atomic.q1) }}</td>
              </tr>
              <tr>
                <td>Q3 (75th percentile)</td>
                <td>{{ formatPercent(statistics.atomic.q3) }}</td>
              </tr>
              <tr>
                <td>Min</td>
                <td>{{ formatPercent(statistics.atomic.min) }}</td>
              </tr>
              <tr>
                <td>Max</td>
                <td>{{ formatPercent(statistics.atomic.max) }}</td>
              </tr>
              <tr>
                <td>Std Dev</td>
                <td>{{ formatPercent(statistics.atomic.stdDev) }}</td>
              </tr>
              <tr class="info-row">
                <td>Most Conserved Type(s)</td>
                <td>{{ statistics.atomic.mostConserved }} ({{ formatPercent(statistics.atomic.mostConservedValue) }})</td>
              </tr>
              <tr class="info-row">
                <td>Least Conserved Type(s)</td>
                <td>{{ statistics.atomic.leastConserved }} ({{ formatPercent(statistics.atomic.leastConservedValue) }})</td>
              </tr>
              <tr class="info-row">
                <td>Longest Conserved Stretch</td>
                <td>{{ statistics.atomic.longestStretchType }}: {{ statistics.atomic.longestStretchInfo }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
      </div>
    </div>
    
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
const atomPairDataByPair = ref(new Map()) // Map<pairKey, atomPairData>
const conservationThreshold = ref(0.5) // Default 50%
const showTrajectoryModal = ref(false)
const selectedInteraction = ref(null)
const statistics = ref(null)
const hiddenTypes = ref(new Set()) // Track hidden interaction types from legend clicks

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

// Helper function to calculate quartiles
const calculateQuartile = (sortedArray, q) => {
  if (sortedArray.length === 0) return 0
  const pos = (sortedArray.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  if (sortedArray[base + 1] !== undefined) {
    return sortedArray[base] + rest * (sortedArray[base + 1] - sortedArray[base])
  } else {
    return sortedArray[base]
  }
}

// Helper function to calculate statistics
const calculateStatistics = (values) => {
  if (values.length === 0) {
    return {
      count: 0,
      mean: 0,
      median: 0,
      q1: 0,
      q3: 0,
      min: 0,
      max: 0,
      stdDev: 0
    }
  }

  const sorted = [...values].sort((a, b) => a - b)
  const count = sorted.length
  const sum = sorted.reduce((acc, val) => acc + val, 0)
  const mean = sum / count
  
  const variance = sorted.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / count
  const stdDev = Math.sqrt(variance)
  
  return {
    count,
    mean,
    median: calculateQuartile(sorted, 0.5),
    q1: calculateQuartile(sorted, 0.25),
    q3: calculateQuartile(sorted, 0.75),
    min: sorted[0],
    max: sorted[sorted.length - 1],
    stdDev
  }
}

// Format percentage value
const formatPercent = (value) => {
  return `${(value * 100).toFixed(2)}%`
}

const updateChart = async () => {
  if (!chartContainer.value) return

  // Load atom pair data for all pairs first (if not already loaded)
  await loadAtomPairDataForAllPairs()

  // Use filteredInteractions which already applies the interaction type filter
  const allInteractions = dataStore.filteredInteractions

  if (allInteractions.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    statistics.value = null
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
    statistics.value = null
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
        
        // Check if type is hidden via legend click
        if (hiddenTypes.value.has(type)) {
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
    statistics.value = null
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
        
        // LEVEL 4 FILTER: Skip if hidden via legend click
        if (hiddenTypes.value.has(type)) {
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

  // Create labels for Y-axis: just the pair
  const pairTypeLabels = pairTypeCombinations.map(pt => pt.pair)
  
  // Count unique pairs for the chart title
  const uniquePairCount = new Set(pairTypeCombinations.map(pt => pt.pair)).size
  
  // Calculate statistics for residue level (pair conservation) and atomic level (type conservation)
  // Only include data that meets the current threshold and filter criteria
  const residueScores = []
  const atomicScores = []
  const uniquePairs = new Set() // Track unique pairs for CR50
  const typeConservationMap = new Map() // Track conservation scores by type
  const typeFramesMap = new Map() // Track all frames by type for longest stretch calculation
  const pairConservationMap = new Map() // Track conservation by pair
  const pairFramesMap = new Map() // Track frames by pair
  
  sortedPairs.forEach((pairData) => {
    pairData.interactions.forEach(interaction => {
      // Residue level: pair consistency (only if ≥50%)
      if (interaction.consistency !== undefined && interaction.consistency !== null && interaction.consistency >= 0.50) {
        residueScores.push(interaction.consistency)
        // Track unique pairs for CR50 count
        const pairKey = `${interaction.id1}_${interaction.id2}`
        uniquePairs.add(pairKey)
        
        // Track conservation by pair
        const pairLabel = `${interaction.id1} ↔ ${interaction.id2}`
        if (!pairConservationMap.has(pairLabel)) {
          pairConservationMap.set(pairLabel, [])
        }
        pairConservationMap.get(pairLabel).push(interaction.consistency)
        
        // Track frames for this pair (combine all interaction types)
        if (!pairFramesMap.has(pairLabel)) {
          pairFramesMap.set(pairLabel, [])
        }
        // Collect all frames where ANY interaction type is present
        const typeFrames = interaction.typeFrames || {}
        Object.values(typeFrames).forEach(frames => {
          if (Array.isArray(frames)) {
            pairFramesMap.get(pairLabel).push(...frames)
          }
        })
      }
      
      // Atomic level: type conservation (only if meets threshold and filter)
      const typePersistence = interaction.typePersistence || {}
      const typeFrames = interaction.typeFrames || {}
      
      interaction.typesArray.forEach((type) => {
        const typeConservation = typePersistence[type]
        
        // Check if type conservation meets threshold
        if (typeConservation === undefined || typeConservation === null || typeConservation < conservationThreshold.value) {
          return
        }
        
        // Check if type matches selected interaction types filter
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return // Skip this type if it doesn't match filter
          }
        }
        
        atomicScores.push(typeConservation)
        
        // Track conservation scores by type
        if (!typeConservationMap.has(type)) {
          typeConservationMap.set(type, [])
        }
        typeConservationMap.get(type).push(typeConservation)
        
        // Track frames for this type for longest stretch calculation
        const framesForType = typeFrames[type] || []
        if (framesForType.length > 0) {
          if (!typeFramesMap.has(type)) {
            typeFramesMap.set(type, [])
          }
          typeFramesMap.get(type).push(...framesForType)
        }
      })
    })
  })
  
  // Calculate most and least conserved pairs at residue level
  let mostConservedPairs = []
  let leastConservedPairs = []
  let maxPairConservation = -1
  let minPairConservation = 2
  
  pairConservationMap.forEach((scores, pairLabel) => {
    const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
    
    if (avgConservation > maxPairConservation) {
      maxPairConservation = avgConservation
      mostConservedPairs = [pairLabel]
    } else if (avgConservation === maxPairConservation) {
      mostConservedPairs.push(pairLabel)
    }
    
    if (avgConservation < minPairConservation) {
      minPairConservation = avgConservation
      leastConservedPairs = [pairLabel]
    } else if (avgConservation === minPairConservation) {
      leastConservedPairs.push(pairLabel)
    }
  })
  
  // Calculate longest conserved pair stretch (without breaking in frames)
  let longestPairStretch = 0
  let longestPairStretchLabel = ''
  let longestPairStretchInfo = ''
  
  pairFramesMap.forEach((allFrames, pairLabel) => {
    // Get unique sorted frames for this pair
    const uniqueFrames = [...new Set(allFrames)].sort((a, b) => a - b)
    
    if (uniqueFrames.length === 0) return
    
    // Find longest consecutive stretch
    let currentStretch = 1
    let maxStretch = 1
    let maxStretchStart = uniqueFrames[0]
    let maxStretchEnd = uniqueFrames[0]
    let currentStart = uniqueFrames[0]
    
    for (let i = 1; i < uniqueFrames.length; i++) {
      if (uniqueFrames[i] === uniqueFrames[i - 1] + 1) {
        // Consecutive frame
        currentStretch++
        if (currentStretch > maxStretch) {
          maxStretch = currentStretch
          maxStretchStart = currentStart
          maxStretchEnd = uniqueFrames[i]
        }
      } else {
        // Break in continuity
        currentStretch = 1
        currentStart = uniqueFrames[i]
      }
    }
    
    if (maxStretch > longestPairStretch) {
      longestPairStretch = maxStretch
      longestPairStretchLabel = pairLabel
      longestPairStretchInfo = `${maxStretch} frames (${maxStretchStart}-${maxStretchEnd})`
    }
  })
  
  // Calculate most and least conserved interaction types
  let mostConservedTypes = []
  let leastConservedTypes = []
  let maxConservation = -1
  let minConservation = 2
  
  typeConservationMap.forEach((scores, type) => {
    const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
    
    if (avgConservation > maxConservation) {
      maxConservation = avgConservation
      mostConservedTypes = [type]
    } else if (avgConservation === maxConservation) {
      mostConservedTypes.push(type)
    }
    
    if (avgConservation < minConservation) {
      minConservation = avgConservation
      leastConservedTypes = [type]
    } else if (avgConservation === minConservation) {
      leastConservedTypes.push(type)
    }
  })
  
  // Calculate longest conserved stretch (without breaking in frames)
  let longestStretch = 0
  let longestStretchType = ''
  let longestStretchInfo = ''
  
  typeFramesMap.forEach((allFrames, type) => {
    // Get unique sorted frames for this type
    const uniqueFrames = [...new Set(allFrames)].sort((a, b) => a - b)
    
    if (uniqueFrames.length === 0) return
    
    // Find longest consecutive stretch
    let currentStretch = 1
    let maxStretch = 1
    let maxStretchStart = uniqueFrames[0]
    let maxStretchEnd = uniqueFrames[0]
    let currentStart = uniqueFrames[0]
    
    for (let i = 1; i < uniqueFrames.length; i++) {
      if (uniqueFrames[i] === uniqueFrames[i - 1] + 1) {
        // Consecutive frame
        currentStretch++
        if (currentStretch > maxStretch) {
          maxStretch = currentStretch
          maxStretchStart = currentStart
          maxStretchEnd = uniqueFrames[i]
        }
      } else {
        // Break in continuity
        currentStretch = 1
        currentStart = uniqueFrames[i]
      }
    }
    
    if (maxStretch > longestStretch) {
      longestStretch = maxStretch
      longestStretchType = type
      longestStretchInfo = `${maxStretch} frames (${maxStretchStart}-${maxStretchEnd})`
    }
  })
  
  // Calculate statistics
  const residueStats = calculateStatistics(residueScores)
  residueStats.cr50 = uniquePairs.size // CR50: count of unique pairs with ≥50% conservation
  residueStats.mostConserved = mostConservedPairs.length > 0 ? (mostConservedPairs.length > 2 ? `${mostConservedPairs.slice(0, 2).join(', ')} (+${mostConservedPairs.length - 2} more)` : mostConservedPairs.join(', ')) : 'N/A'
  residueStats.mostConservedValue = maxPairConservation >= 0 ? maxPairConservation : 0
  residueStats.leastConserved = leastConservedPairs.length > 0 ? (leastConservedPairs.length > 2 ? `${leastConservedPairs.slice(0, 2).join(', ')} (+${leastConservedPairs.length - 2} more)` : leastConservedPairs.join(', ')) : 'N/A'
  residueStats.leastConservedValue = minPairConservation < 2 ? minPairConservation : 0
  residueStats.longestStretchPair = longestPairStretchLabel || 'N/A'
  residueStats.longestStretchInfo = longestPairStretchInfo || 'N/A'
  
  const atomicStats = calculateStatistics(atomicScores)
  atomicStats.ca = pairTypeCombinations.length // CA: count of pair-type combinations meeting threshold
  atomicStats.mostConserved = mostConservedTypes.length > 0 ? mostConservedTypes.join(', ') : 'N/A'
  atomicStats.mostConservedValue = maxConservation >= 0 ? maxConservation : 0
  atomicStats.leastConserved = leastConservedTypes.length > 0 ? leastConservedTypes.join(', ') : 'N/A'
  atomicStats.leastConservedValue = minConservation < 2 ? minConservation : 0
  atomicStats.longestStretchType = longestStretchType || 'N/A'
  atomicStats.longestStretchInfo = longestStretchInfo || 'N/A'
  
  statistics.value = {
    residue: residueStats,
    atomic: atomicStats
  }

  // Create separate heatmap series for each interaction type (like TimePairMatrix)
  // This allows legend click to show/hide each type
  const series = []
  const allDataPoints = [] // For atom change detection
  
  // Collect all available interaction types (including hidden ones) for legend
  const allAvailableTypes = new Set()
  stablePairs.forEach(interaction => {
    const typePersistence = interaction.typePersistence || {}
    interaction.typesArray.forEach(type => {
      const typeConservation = typePersistence[type] || 0
      if (typeConservation >= conservationThreshold.value) {
        if (dataStore.selectedInteractionTypes.size === 0 || 
            matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
          allAvailableTypes.add(type)
        }
      }
    })
  })
  
  // Create series for visible types (with data)
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
      visible: true
    })
  })
  
  // Add hidden types to legend (with empty data, visually grayed out)
  Array.from(hiddenTypes.value).sort().forEach(type => {
    // Only add if it's a valid available type
    if (allAvailableTypes.has(type)) {
      series.push({
        type: 'heatmap',
        name: type,
        data: [],
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
        visible: false // This makes it appear grayed out in legend
      })
    }
  })
  
  // Collect data points where atoms change
  const atomChangeData = []
  allDataPoints.forEach(point => {
    const pairString = point.custom?.pair || point.pair || ''
    // Convert "A-LYS8 ↔ B-ASP45" to "A-LYS8_B-ASP45" for pairKey (storage format)
    const pairKey = pairString.includes(' ↔ ') 
      ? pairString.replace(' ↔ ', '_')
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
      text: `Interaction Conservation Timeline (${pairTypeCombinations.length} pair-type combinations, ${uniquePairCount} unique pairs)`,
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
    plotOptions: {
      heatmap: {
        cursor: 'pointer',
        borderWidth: 1,
        borderColor: '#e8e8ed',
        events: {
          legendItemClick: function() {
            const typeName = this.name
            // Toggle hidden state
            if (hiddenTypes.value.has(typeName)) {
              hiddenTypes.value.delete(typeName)
            } else {
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
            // Toggle hidden state for interaction types
            if (hiddenTypes.value.has(typeName)) {
              hiddenTypes.value.delete(typeName)
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

// Parse residue ID (format: "A-LYS8")
const parseResidueId = (id) => {
  const match = id.match(/^([A-Z])-(.+?)(\d+)$/)
  if (match) {
    return { chain: match[1], name: match[2], num: match[3] }
  }
  return null
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
      resName1: res1.name,
      resNum1: res1.num,
      chain1: res1.chain,
      resName2: res2.name,
      resNum2: res2.num,
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

// Load atom pair data for all unique pairs in the current filtered interactions
const loadAtomPairDataForAllPairs = async () => {
  if (!dataStore.currentSystem) return
  
  const allInteractions = dataStore.filteredInteractions
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= 0.50)
  
  if (stablePairs.length === 0) return
  
  // Get unique pairs
  const uniquePairs = new Map()
  stablePairs.forEach(interaction => {
    const pairKey = `${interaction.id1}_${interaction.id2}`
    if (!uniquePairs.has(pairKey)) {
      uniquePairs.set(pairKey, {
        pairKey,
        id1: interaction.id1,
        id2: interaction.id2
      })
    }
  })
  
  // Load atom pair data for all unique pairs in parallel
  const loadPromises = Array.from(uniquePairs.values()).map(pair => 
    loadAtomPairDataForPair(pair.pairKey, pair.id1, pair.id2)
  )
  
  await Promise.all(loadPromises)
}

// Get atom pairs for a specific frame (returns array of atomPair strings)
const getAtomPairsForFrame = (atomPairData, frame) => {
  if (!atomPairData || !atomPairData.atomPairsByFrame) return []
  const frameKey = String(frame)
  const frameData = atomPairData.atomPairsByFrame[frameKey] || []
  // Return unique atom pair strings
  return [...new Set(frameData.map(entry => entry.atomPair))]
}

// Check if atoms changed between frames
// Returns true if atom pairs for the given interaction type are different between current and previous frame
const hasAtomChange = (pairKey, frame, type) => {
  // pairKey format: "A-LYS8_B-ASP45" (from loadAtomPairDataForPair)
  const atomPairData = atomPairDataByPair.value.get(pairKey)
  if (!atomPairData) return false
  
  // Can't compare if frame is 1 (no previous frame)
  if (frame <= 1) return false
  
  const currentFrame = frame
  const previousFrame = frame - 1
  
  // Get frame data (keys are strings in the response)
  const frameKey = String(currentFrame)
  const prevFrameKey = String(previousFrame)
  const currentFrameData = atomPairData.atomPairsByFrame[frameKey] || []
  const prevFrameData = atomPairData.atomPairsByFrame[prevFrameKey] || []
  
  // Filter atom pairs by interaction type and get unique sorted sets
  const currentTypePairs = currentFrameData
    .filter(entry => entry.interactionType === type)
    .map(entry => entry.atomPair)
  const prevTypePairs = prevFrameData
    .filter(entry => entry.interactionType === type)
    .map(entry => entry.atomPair)
  
  // Remove duplicates and sort for comparison
  const currentUnique = [...new Set(currentTypePairs)].sort()
  const prevUnique = [...new Set(prevTypePairs)].sort()
  
  // If both frames have no atoms for this type, no change
  if (currentUnique.length === 0 && prevUnique.length === 0) {
    return false
  }
  
  // If previous frame had no atoms but current frame has atoms, this is NOT a change
  // (it's a new interaction appearing, not atoms changing)
  if (prevUnique.length === 0 && currentUnique.length > 0) {
    return false
  }
  
  // If current frame has no atoms but previous frame had atoms, this IS a change
  // (atoms disappeared)
  if (currentUnique.length === 0 && prevUnique.length > 0) {
    return true
  }
  
  // Both frames have atoms - compare the sets
  // If different lengths, definitely changed
  if (currentUnique.length !== prevUnique.length) {
    return true
  }
  
  // Same length - check if the sets are identical
  for (let i = 0; i < currentUnique.length; i++) {
    if (currentUnique[i] !== prevUnique[i]) {
      return true // Different atom pairs found
    }
  }
  
  // Sets are identical - no change
  return false
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
  () => dataStore.selectedInteractionTypes.size
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

.statistics-section {
  margin-bottom: 32px;
  padding: 24px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}

.statistics-title {
  font-size: 21px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0 0 8px 0;
  letter-spacing: -0.022em;
}

.statistics-description {
  font-size: 14px;
  color: #6e6e73;
  margin: 0 0 20px 0;
  font-weight: 500;
}

.statistics-tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.statistics-table-wrapper {
  background: #f5f5f7;
  border-radius: 8px;
  padding: 16px;
}

.table-subtitle {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px 0;
  letter-spacing: -0.022em;
}

.statistics-table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.statistics-table thead {
  background: #1d1d1f;
}

.statistics-table thead th {
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.statistics-table tbody tr {
  border-bottom: 1px solid #e8e8ed;
  transition: background-color 0.15s ease;
}

.statistics-table tbody tr:last-child {
  border-bottom: none;
}

.statistics-table tbody tr:hover {
  background-color: #f9f9fb;
}

.statistics-table tbody tr.highlight-row {
  background-color: #e3f2ff;
  font-weight: 700;
}

.statistics-table tbody tr.highlight-row:hover {
  background-color: #d1e8ff;
}

.statistics-table tbody tr.highlight-row td {
  color: #0066cc;
  font-weight: 700;
}

.statistics-table tbody tr.info-row {
  background-color: #f9f9fb;
  border-top: 2px solid #d2d2d7;
}

.statistics-table tbody tr.info-row:hover {
  background-color: #f0f0f5;
}

.statistics-table tbody tr.info-row td:first-child {
  font-weight: 600;
  color: #1d1d1f;
  font-style: italic;
}

.statistics-table tbody tr.info-row td:last-child {
  color: #3B6EF5;
  font-weight: 500;
}

.statistics-table tbody td {
  padding: 10px 16px;
  font-size: 14px;
}

.statistics-table tbody td:first-child {
  font-weight: 600;
  color: #1d1d1f;
}

.statistics-table tbody td:last-child {
  color: #6e6e73;
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
