<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <!-- Pair Conservation Threshold (like FilteredHeatmap) -->
      <div class="slider-group">
        <label for="pair-conservation-slider" class="slider-label">
          Pair Conservation Threshold
        </label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="pair-conservation-slider"
              type="range"
              min="0"
              max="1.0"
              step="0.1"
              :value="pairConservationThreshold"
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
              :value="Math.round(pairConservationThreshold * 100)"
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
        <p class="slider-description">Show pairs present in at least {{ Math.round(pairConservationThreshold * 100) }}% of frames</p>
      </div>
      
      <!-- Type Conservation Threshold -->
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
      
      <div class="info-notice">
        <strong>Interaction Timeline View:</strong> Click on a segment for trajectory analysis.
      </div>
    </div>
    
    <div ref="chartContainer" class="chart-container"></div>
    
    <!-- Statistics Cards Section -->
    <div v-if="statistics" class="statistics-section">
      <h3 class="statistics-title">Conservation Analysis</h3>
      
      <!-- Key Metrics -->
      <div class="key-metrics">
        <div class="metric-card">
          <div class="metric-value">{{ statistics.residue.cr50 }}</div>
          <div class="metric-label">
            CR<sub>{{ Math.round(pairConservationThreshold * 100) }}</sub>
            <span class="info-icon" @mouseenter="showTooltip($event, `Conserved Residue pairs: Number of unique pairs present in ≥${Math.round(pairConservationThreshold * 100)}% of trajectory frames`)" @mouseleave="hideTooltip">ⓘ</span>
          </div>
          <div class="metric-desc">Conserved pairs</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ statistics.atomic.ca }}</div>
          <div class="metric-label">
            CA<sub>{{ Math.round(conservationThreshold * 100) }}</sub>
            <span class="info-icon" @mouseenter="showTooltip($event, `Conserved Atomic interactions: Pair-type combinations with ≥${Math.round(conservationThreshold * 100)}% type conservation`)" @mouseleave="hideTooltip">ⓘ</span>
          </div>
          <div class="metric-desc">Conserved interactions</div>
        </div>
      </div>
      
      <!-- Key Insights Grid -->
      <div class="insights-grid">
        <!-- Most Conserved Pairs -->
        <div class="insight-card" v-if="statistics.residue.mostConservedList && statistics.residue.mostConservedList.length > 0">
          <div class="insight-header">
            <span class="insight-title">Most Conserved Pairs</span>
            <span class="info-icon" @mouseenter="showTooltip($event, 'Residue pairs with the highest average conservation across all their interaction types')" @mouseleave="hideTooltip">ⓘ</span>
          </div>
          <div class="insight-pairs-list">
            <div v-for="(item, idx) in statistics.residue.mostConservedList.slice(0, 3)" :key="idx" class="pair-with-types">
              <div class="pair-rank-row">
                <span class="rank-text">{{ getOrdinal(item.rank) }}.</span>
                <span class="pair-name">{{ item.pair }}</span>
                <span class="frame-count">({{ item.frameCount }}/{{ dataStore.totalFrames }} frames)</span>
              </div>
              <div class="type-tags">
                <span 
                  v-for="(typeInfo, tIdx) in item.types.slice(0, 4)" 
                  :key="tIdx" 
                  class="type-tag"
                  :style="{ backgroundColor: getInteractionBaseColor(typeInfo.type), color: getTextColorForBg(typeInfo.type) }"
                  :title="`${typeInfo.type}: ${formatPercent(typeInfo.conservation)}`"
                >{{ typeInfo.type }}</span>
                <span v-if="item.types.length > 4" class="type-tag more-types">+{{ item.types.length - 4 }}</span>
              </div>
            </div>
            <button 
              v-if="statistics.residue.mostConservedList.length > 3" 
              class="insight-more-btn"
              @click="openPairListModal('Most Conserved Pairs', statistics.residue.mostConservedList, '')"
            >
              +{{ statistics.residue.mostConservedList.length - 3 }} more pairs
            </button>
          </div>
        </div>
        

        
        <!-- Longest Conserved Stretch -->
        <div class="insight-card" v-if="statistics.residue.longestStretchList && statistics.residue.longestStretchList.length > 0">
          <div class="insight-header">
            <span class="insight-title">Longest Conserved Stretch</span>
            <span class="info-icon" @mouseenter="showTooltip($event, 'Maximum consecutive frames where the pair maintains any interaction type')" @mouseleave="hideTooltip">ⓘ</span>
          </div>
          <div class="insight-pairs-list">
            <div v-for="(item, idx) in statistics.residue.longestStretchList.slice(0, 3)" :key="idx" class="pair-with-types">
              <div class="pair-rank-row">
                <span class="rank-text">{{ getOrdinal(item.rank) }}.</span>
                <span class="pair-name">{{ item.pair }}</span>
                <span class="frame-count">{{ item.stretchInfo }}</span>
              </div>
              <div v-if="item.types && item.types.length > 0" class="type-tags">
                <span 
                  v-for="(typeInfo, tIdx) in item.types.slice(0, 4)" 
                  :key="tIdx" 
                  class="type-tag"
                  :style="{ backgroundColor: getInteractionBaseColor(typeInfo.type), color: getTextColorForBg(typeInfo.type) }"
                  :title="`${typeInfo.type}: ${formatPercent(typeInfo.conservation)}`"
                >{{ typeInfo.type }}</span>
              </div>
            </div>
            <button 
              v-if="statistics.residue.longestStretchList.length > 3" 
              class="insight-more-btn"
              @click="openPairListModal('Longest Conserved Stretch', statistics.residue.longestStretchList, '')"
            >
              +{{ statistics.residue.longestStretchList.length - 3 }} more pairs
            </button>
          </div>
        </div>
        
        <!-- Most Conserved Types -->
        <div class="insight-card" v-if="statistics.atomic.mostConservedList && statistics.atomic.mostConservedList.length > 0">
          <div class="insight-header">
            <span class="insight-title">Most Conserved Types</span>
            <span class="info-icon" @mouseenter="showTooltip($event, 'Interaction types with highest average conservation across all pairs')" @mouseleave="hideTooltip">ⓘ</span>
          </div>
          <div class="insight-pairs-list">
            <div v-for="(item, idx) in statistics.atomic.mostConservedList.slice(0, 3)" :key="idx" class="pair-with-types">
              <div class="pair-rank-row">
                <span class="rank-text">{{ getOrdinal(item.rank) }}.</span>
                <span 
                  class="type-tag large"
                  :style="{ backgroundColor: getInteractionBaseColor(item.type), color: getTextColorForBg(item.type) }"
                >{{ item.type }}</span>
              </div>
              <div v-if="item.pairs && item.pairs.length > 0" class="type-pairs-preview">
                <span class="pairs-label">Pairs:</span>
                <span v-for="(pair, pIdx) in item.pairs.slice(0, 3)" :key="pIdx" class="pair-mini-tag">{{ pair }}</span>
                <span v-if="item.pairs.length > 3" class="pair-mini-tag more">+{{ item.pairs.length - 3 }}</span>
              </div>
            </div>
            <button 
              v-if="statistics.atomic.mostConservedList.length > 3" 
              class="insight-more-btn"
              @click="openTypeListModal('Most Conserved Types', statistics.atomic.mostConservedList, '')"
            >
              +{{ statistics.atomic.mostConservedList.length - 3 }} more
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Global Tooltip -->
    <Teleport to="body">
      <div 
        v-if="activeTooltip.visible" 
        class="global-tooltip"
        :style="{ top: activeTooltip.y + 'px', left: activeTooltip.x + 'px' }"
      >
        {{ activeTooltip.text }}
      </div>
    </Teleport>
    
    <!-- List Modal for expanded items -->
    <Teleport to="body">
      <div v-if="listModal.visible" class="list-modal-overlay" @click.self="closeListModal">
        <div class="list-modal-panel">
          <div class="list-modal-header">
            <h3>{{ listModal.title }}</h3>
            <span v-if="listModal.badge" class="list-modal-badge">{{ listModal.badge }}</span>
            <button class="list-modal-close" @click="closeListModal">×</button>
          </div>
          <div class="list-modal-content">
            <!-- Type list (for Most Conserved Types) -->
            <div v-if="listModal.isTypeList" class="list-modal-items">
              <div v-for="(item, idx) in listModal.items" :key="idx" class="list-modal-type-item">
                <div class="pair-rank-row">
                  <span class="rank-text">{{ getOrdinal(item.rank) }}.</span>
                  <span 
                    class="type-tag large" 
                    :style="{ backgroundColor: getInteractionBaseColor(item.type), color: getTextColorForBg(item.type) }"
                  >{{ item.type }}</span>
                </div>
                <div v-if="item.pairs && item.pairs.length > 0" class="type-pairs-list">
                  <span class="pairs-label">Pairs:</span>
                  <span v-for="(pair, pairIdx) in item.pairs.slice(0, 5)" :key="pairIdx" class="pair-mini-tag">{{ pair }}</span>
                  <span v-if="item.pairs.length > 5" class="pair-mini-tag more">+{{ item.pairs.length - 5 }}</span>
                </div>
              </div>
            </div>
            <!-- Pair list with types (for Most/Least Conserved Pairs and Longest Stretch) -->
            <div v-else-if="listModal.isPairList" class="list-modal-items pair-list">
              <div v-for="(item, idx) in listModal.items" :key="idx" class="list-modal-pair-item">
                <div class="pair-rank-row">
                  <span class="rank-text">{{ getOrdinal(item.rank) }}.</span>
                  <span class="pair-name">{{ item.pair }}</span>
                  <span v-if="item.frameCount !== undefined" class="frame-count">({{ item.frameCount }}/{{ dataStore.totalFrames }} frames)</span>
                  <span v-else-if="item.stretchInfo" class="frame-count">{{ item.stretchInfo }}</span>
                </div>
                <div class="type-tags">
                  <span 
                    v-for="(typeInfo, tIdx) in item.types" 
                    :key="tIdx" 
                    class="type-tag"
                    :style="{ backgroundColor: getInteractionBaseColor(typeInfo.type), color: getTextColorForBg(typeInfo.type) }"
                    :title="`${formatPercent(typeInfo.conservation)}`"
                  >{{ typeInfo.type }}</span>
                </div>
              </div>
            </div>
            <!-- Simple list (fallback) -->
            <div v-else class="list-modal-items">
              <span v-for="(item, idx) in listModal.items" :key="idx" class="list-modal-item">{{ item }}</span>
            </div>
          </div>
        </div>
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
import InteractionTrajectoryModal from '../InteractionTrajectoryModal.vue'

HeatmapModule(Highcharts)

// Initialize heatmap module
if (typeof Highcharts === 'object') {
  HeatmapModule(Highcharts)
}

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
const distanceData = ref(null)
const atomPairDataByPair = ref(new Map()) // Map<pairKey, atomPairData>
const conservationThreshold = ref(0.5) // Default 50% for type conservation
const pairConservationThreshold = ref(0.5) // Default 50% for pair conservation (like FilteredHeatmap)
const showTrajectoryModal = ref(false)
const selectedInteraction = ref(null)
  const statistics = ref(null)
  const hiddenTypes = ref(new Set()) // Track hidden interaction types from legend clicks
  const atomChangeMode = ref('previous') // 'previous' | 'dominant' | 'first'
  const expandedDetails = ref({
    residueMostConserved: false,
    residueLeastConserved: false,
    atomicMostConserved: false,
    atomicLeastConserved: false,
    atomicLongestStretch: false
  })

// List modal state for expanded items
const listModal = ref({
  visible: false,
  title: '',
  items: [],
  badge: '',
  isTypeList: false,
  isPairList: false
})

const openListModal = (title, items, badge = '') => {
  listModal.value = {
    visible: true,
    title,
    items,
    badge,
    isTypeList: false
  }
}

const openTypeListModal = (title, items, badge = '') => {
  listModal.value = {
    visible: true,
    title,
    items,
    badge,
    isTypeList: true,
    isPairList: false
  }
}

const openPairListModal = (title, items, badge = '') => {
  listModal.value = {
    visible: true,
    title,
    items,
    badge,
    isTypeList: false,
    isPairList: true
  }
}

const closeListModal = () => {
  listModal.value.visible = false
}

// Helper function to get readable text color based on background color
const getTextColorForBg = (typeLabel) => {
  // Get the RGB color for this type
  const colorStr = getInteractionBaseColor(typeLabel)
  const match = colorStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
  if (!match) return '#ffffff'
  
  const r = parseInt(match[1])
  const g = parseInt(match[2])
  const b = parseInt(match[3])
  
  // Calculate relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  
  // Return white for dark backgrounds, dark for light backgrounds
  return luminance > 0.5 ? '#1d1d1f' : '#ffffff'
}

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
  cr: `Count of unique residue pairs present in ≥${Math.round(pairConservationThreshold.value * 100)}% of trajectory frames`,
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
  ca: `Count of pair-type combinations (residue pair + interaction type) with ≥${Math.round(conservationThreshold.value * 100)}% type conservation`,
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
  conservationThreshold.value = parseFloat(event.target.value)
  updateChart()
}

// Pair conservation threshold functions
const updatePairThreshold = (event) => {
  pairConservationThreshold.value = parseFloat(event.target.value)
  updateChart()
}

const updatePairThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    pairConservationThreshold.value = value / 100
    updateChart()
  }
}

const validatePairThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = Math.round(pairConservationThreshold.value * 100)
    return
  }
  // Clamp value between 0 and 100
  value = Math.max(0, Math.min(100, value))
  event.target.value = value
  pairConservationThreshold.value = value / 100
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

// Convert number to ordinal (1st, 2nd, 3rd, etc.)
const getOrdinal = (n) => {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
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

  // LEVEL 1: Filter pairs by overall conservation (using pairConservationThreshold)
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= pairConservationThreshold.value)

  if (stablePairs.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    statistics.value = null
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No pairs found with ≥${Math.round(pairConservationThreshold.value * 100)}% conservation.</div>`
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
  
  // Calculate statistics for residue level (pair conservation) and atomic level (type conservation)
  // Only include data that meets the current threshold and filter criteria
  const residueScores = []
  const atomicScores = []
  const uniquePairs = new Set() // Track unique pairs for CR50
  const typeConservationMap = new Map() // Track conservation scores by type
  const typeFramesMap = new Map() // Track all frames by type for longest stretch calculation
  const pairConservationMap = new Map() // Track conservation by pair
  const pairFramesMap = new Map() // Track frames by pair
  const typeToPairsMap = new Map() // Track which residue pairs each interaction type belongs to
  const pairToTypesMap = new Map() // Track which interaction types each pair has (filtered by threshold)
  const allPairToTypesMap = new Map() // Track ALL interaction types each pair has (for stats cards, no threshold filter)
  const pairTypeFramesMap = new Map() // Track frames for each pair-type combination for longest stretch calculation
  const typeToPairConservationMap = new Map() // Track pair conservation per type (type -> Map(pair -> conservation))
  
  sortedPairs.forEach((pairData) => {
    pairData.interactions.forEach(interaction => {
      // Residue level: pair consistency (only if meets pair threshold)
      if (interaction.consistency !== undefined && interaction.consistency !== null && interaction.consistency >= pairConservationThreshold.value) {
        residueScores.push(interaction.consistency)
        // Track unique pairs for CR50 count
        const pairKey = formatPairKey(interaction.id1, interaction.id2)
        uniquePairs.add(pairKey)
        
        // Track conservation by pair
        const pairLabel = formatResiduePairFromIds(interaction.id1, interaction.id2)
        if (!pairConservationMap.has(pairLabel)) {
          pairConservationMap.set(pairLabel, [])
        }
        pairConservationMap.get(pairLabel).push(interaction.consistency)
        
        // Track frames for this pair using the frames property (all frames where this pair interacts)
        if (!pairFramesMap.has(pairLabel)) {
          pairFramesMap.set(pairLabel, [])
        }
        // Use interaction.frames which contains ALL frame numbers where this pair has any interaction
        if (interaction.frames && Array.isArray(interaction.frames)) {
          pairFramesMap.get(pairLabel).push(...interaction.frames)
        }
      }
      
      // Atomic level: type conservation (only if meets threshold and filter)
      const typePersistence = interaction.typePersistence || {}
      const typeFrames = interaction.typeFrames || {}
      const pairLabel = formatResiduePairFromIds(interaction.id1, interaction.id2)
      
      interaction.typesArray.forEach((type) => {
        const typeConservation = typePersistence[type]
        
        // Always track ALL types for each pair (for stats cards display, regardless of threshold)
        if (typeConservation !== undefined && typeConservation !== null) {
          if (!allPairToTypesMap.has(pairLabel)) {
            allPairToTypesMap.set(pairLabel, new Map())
          }
          allPairToTypesMap.get(pairLabel).set(type, typeConservation)
        }
        
        // Check if type conservation meets threshold (for filtered statistics)
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
        
        // Track which residue pairs this type belongs to
        if (!typeToPairsMap.has(type)) {
          typeToPairsMap.set(type, new Set())
        }
        typeToPairsMap.get(type).add(pairLabel)
        
        // Track which types this pair has (reverse mapping)
        if (!pairToTypesMap.has(pairLabel)) {
          pairToTypesMap.set(pairLabel, new Map())
        }
        pairToTypesMap.get(pairLabel).set(type, typeConservation)
        
        // Track pair conservation for this type (for finding pairs with specific conservation values)
        if (!typeToPairConservationMap.has(type)) {
          typeToPairConservationMap.set(type, new Map())
        }
        typeToPairConservationMap.get(type).set(pairLabel, typeConservation)
        
        // Track frames for this type for longest stretch calculation
        const framesForType = typeFrames[type] || []
        if (framesForType.length > 0) {
          if (!typeFramesMap.has(type)) {
            typeFramesMap.set(type, [])
          }
          typeFramesMap.get(type).push(...framesForType)
          
          // Track frames for this specific pair-type combination
          const pairTypeKey = `${pairLabel}_${type}`
          if (!pairTypeFramesMap.has(pairTypeKey)) {
            pairTypeFramesMap.set(pairTypeKey, {
              pair: pairLabel,
              type: type,
              frames: []
            })
          }
          pairTypeFramesMap.get(pairTypeKey).frames.push(...framesForType)
        }
      })
    })
  })
  
  // Calculate most and least conserved pairs at residue level
  // Collect ALL pairs with their conservation scores for proper ranking
  const allPairsWithConservation = []
  
  pairConservationMap.forEach((scores, pairLabel) => {
    const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
    const frames = pairFramesMap.get(pairLabel) || []
    const uniqueFrameCount = new Set(frames).size
    allPairsWithConservation.push({
      pair: pairLabel,
      conservation: avgConservation,
      frameCount: uniqueFrameCount
    })
  })
  
  // Sort by conservation descending (most conserved first)
  allPairsWithConservation.sort((a, b) => b.frameCount - a.frameCount)
  
  // Calculate longest conserved pair stretch for ALL pairs (for proper ranking)
  const allPairsWithStretch = []
  
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
    
    // Get number of interaction types for this pair
    const typesMap = allPairToTypesMap.get(pairLabel) || new Map()
    const typeCount = typesMap.size
    
    allPairsWithStretch.push({
      pair: pairLabel,
      stretchLength: maxStretch,
      stretchInfo: `${maxStretch} frames (${maxStretchStart}-${maxStretchEnd})`,
      typeCount
    })
  })
  
  // Sort by: 1) stretch length descending, 2) fewer interaction types (ascending)
  allPairsWithStretch.sort((a, b) => {
    if (b.stretchLength !== a.stretchLength) {
      return b.stretchLength - a.stretchLength // Longer stretch first
    }
    return a.typeCount - b.typeCount // Fewer types preferred (ideally 1)
  })
  
  // Calculate conservation for ALL interaction types (for proper ranking)
  const allTypesWithConservation = []
  
  typeConservationMap.forEach((scores, type) => {
    const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
    // Get pairs associated with this type
    const pairs = typeToPairsMap.get(type) ? Array.from(typeToPairsMap.get(type)) : []
    allTypesWithConservation.push({
      type,
      conservation: avgConservation,
      pairs: pairs.sort()
    })
  })
  
  // Sort by conservation descending
  allTypesWithConservation.sort((a, b) => b.conservation - a.conservation)
  
  // Calculate longest conserved stretch (without breaking in frames)
  // Track per pair-type combination to find which specific pairs have the longest stretch
  let longestStretch = 0
  let longestStretchType = ''
  let longestStretchPairs = []
  let longestStretchInfo = ''
  
  pairTypeFramesMap.forEach((pairTypeData) => {
    const { pair, type, frames } = pairTypeData
    // Get unique sorted frames for this pair-type combination
    const uniqueFrames = [...new Set(frames)].sort((a, b) => a - b)
    
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
      // New longest stretch found - reset everything
      longestStretch = maxStretch
      longestStretchType = type
      longestStretchPairs = [pair]
      longestStretchInfo = `${maxStretch} frames (${maxStretchStart}-${maxStretchEnd})`
    } else if (maxStretch === longestStretch && type === longestStretchType) {
      // Same longest stretch length for the same type - add this pair
      if (!longestStretchPairs.includes(pair)) {
        longestStretchPairs.push(pair)
      }
    }
  })
  
  // Calculate statistics
  const residueStats = calculateStatistics(residueScores)
  residueStats.cr50 = uniquePairs.size // CR50: count of unique pairs with ≥50% conservation
  
  // Build ranked lists with tie handling
  // Helper function to assign ranks with ties using DENSE ranking (1,1,2 not 1,1,39)
  const assignRanks = (sortedItems, valueKey) => {
    let currentRank = 1
    return sortedItems.map((item, idx) => {
      if (idx > 0 && item[valueKey] < sortedItems[idx - 1][valueKey]) {
        currentRank++ // Dense ranking: just increment, don't skip
      }
      return { ...item, rank: currentRank }
    })
  }
  
  // Build most conserved pairs list with types and ranks
  const rankedPairs = assignRanks(allPairsWithConservation, 'frameCount')
  const mostConservedPairsWithTypes = rankedPairs.map(item => {
    const typesMap = allPairToTypesMap.get(item.pair) || new Map()
    return {
      pair: item.pair,
      frameCount: item.frameCount,
      rank: item.rank,
      types: Array.from(typesMap.entries()).map(([type, conservation]) => ({ type, conservation }))
        .sort((a, b) => b.conservation - a.conservation)
    }
  })
  
  // Build ranked longest stretch list with types
  const rankedStretches = assignRanks(allPairsWithStretch, 'stretchLength')
  const longestStretchList = rankedStretches.map(item => {
    const typesMap = allPairToTypesMap.get(item.pair) || new Map()
    return {
      pair: item.pair,
      stretchLength: item.stretchLength,
      stretchInfo: item.stretchInfo,
      rank: item.rank,
      types: Array.from(typesMap.entries()).map(([type, conservation]) => ({ type, conservation }))
        .sort((a, b) => b.conservation - a.conservation)
    }
  })
  
  // Build ranked types list
  const rankedTypes = assignRanks(allTypesWithConservation, 'conservation')
  
  residueStats.mostConservedList = mostConservedPairsWithTypes
  residueStats.longestStretchList = longestStretchList
  residueStats.longestStretchPair = longestStretchList[0]?.pair || 'N/A'
  residueStats.longestStretchInfo = longestStretchList[0]?.stretchInfo || 'N/A'
  residueStats.longestStretchTypes = longestStretchList[0]?.types || []
  
  const atomicStats = calculateStatistics(atomicScores)
  atomicStats.ca = pairTypeCombinations.length // CA: count of pair-type combinations meeting threshold
  
  // Use the ranked types list for atomic stats
  atomicStats.mostConservedList = rankedTypes
  
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
      zoomType: 'xy',
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
      y: 60,
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
  chart = Highcharts.chart(chartContainer.value, exportOptions)
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
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= pairConservationThreshold.value)
  
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
  () => pairConservationThreshold.value
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
  border-radius: 16px;
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
  margin: 0 0 24px 0;
  font-weight: 500;
}

/* Key Metrics - CR and CA cards */
.key-metrics {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  flex: 1;
  background: linear-gradient(135deg, #f5f5f7 0%, #ebebf0 100%);
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid #e8e8ed;
  text-align: center;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: #1d1d1f;
  line-height: 1;
  margin-bottom: 4px;
}

.metric-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #3B6EF5;
}

.metric-label sub {
  font-size: 11px;
  vertical-align: baseline;
  margin-left: -2px;
}

.metric-label .info-icon {
  font-size: 12px;
  color: #8e8e93;
  cursor: pointer;
}

.metric-label .info-icon:hover {
  color: #3B6EF5;
}

.metric-desc {
  font-size: 12px;
  color: #6e6e73;
  margin-top: 4px;
}

/* Stats Grid - Summary Cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #f5f5f7;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: all 0.2s ease;
}

.stat-card:hover {
  background: #ebebf0;
  transform: translateY(-2px);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
  margin-bottom: 4px;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 600;
  margin-bottom: 4px;
}

.stat-sublabel {
  font-size: 11px;
  color: #6e6e73;
  line-height: 1.3;
}

/* Insights Grid */
.insights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.insight-card {
  background: #f9f9fb;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e8e8ed;
  transition: all 0.2s ease;
}

.insight-card:hover {
  border-color: #d2d2d7;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.insight-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.insight-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.insight-indicator.high {
  background: #34c759;
}

.insight-indicator.low {
  background: #ff9500;
}

.insight-indicator.neutral {
  background: #3B6EF5;
}

.insight-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  flex: 1;
}

.insight-badge {
  background: linear-gradient(135deg, #34c759 0%, #30b350 100%);
  color: white;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 12px;
}

.insight-badge.secondary {
  background: linear-gradient(135deg, #ff9500 0%, #ff8000 100%);
}

.insight-content {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.insight-item {
  display: inline-block;
  background: #ffffff;
  border: 1px solid #e8e8ed;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.insight-item.type-item {
  background: #e3f2ff;
  border-color: #b8daff;
  color: #0066cc;
  font-family: inherit;
}

.insight-detail {
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
}

.insight-more-btn {
  background: none;
  border: 1px dashed #3B6EF5;
  color: #3B6EF5;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.insight-more-btn:hover {
  background: #3B6EF5;
  color: white;
  border-style: solid;
}

/* Pair with types layout */
.insight-pairs-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pair-with-types {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  background: #f9f9fb;
  border-radius: 8px;
  border: 1px solid #e8e8ed;
}

.pair-rank-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rank-text {
  font-size: 12px;
  color: #6e6e73;
  font-weight: 600;
  min-width: 28px;
}

.frame-count {
  font-size: 12px;
  color: #6e6e73;
  font-weight: 500;
  margin-left: auto;
}

.type-pairs-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.pairs-label {
  font-size: 11px;
  color: #8e8e93;
  font-weight: 500;
}

.pair-mini-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: #e8e8ed;
  color: #1d1d1f;
  border-radius: 4px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.pair-mini-tag.more {
  background: #d1d1d6;
  color: #6e6e73;
}

.pair-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  min-width: 120px;
}

.stretch-info {
  font-size: 12px;
  color: #6e6e73;
  font-weight: 500;
  margin-left: 8px;
}

.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.type-tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.type-tag.large {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 6px;
}

.type-tag.more-types {
  background: #e8e8ed;
  color: #6e6e73;
}

/* Info icon in insight header */
.insight-header .info-icon {
  margin-left: auto;
  font-size: 14px;
  color: #8e8e93;
  cursor: pointer;
  transition: color 0.15s ease;
}

.insight-header .info-icon:hover {
  color: #3B6EF5;
}

/* Modal pair item */
.list-modal-pair-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  background: #f9f9fb;
  border-radius: 8px;
  border: 1px solid #e8e8ed;
}

.list-modal-pair-item .pair-rank-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.list-modal-pair-item .pair-name {
  min-width: 100px;
  flex-shrink: 0;
}

.list-modal-type-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  background: #f9f9fb;
  border-radius: 8px;
  border: 1px solid #e8e8ed;
}

.list-modal-items.pair-list {
  flex-direction: column;
}

/* List Modal */
.list-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 20px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.list-modal-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  max-height: 80vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.2s ease;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.list-modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8ed;
}

.list-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  flex: 1;
}

.list-modal-badge {
  background: linear-gradient(135deg, #3B6EF5 0%, #2B5CE5 100%);
  color: white;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 14px;
}

.list-modal-close {
  background: none;
  border: none;
  font-size: 28px;
  color: #6e6e73;
  cursor: pointer;
  padding: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.list-modal-close:hover {
  background-color: #f5f5f7;
  color: #1d1d1f;
}

.list-modal-content {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.list-modal-items {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.list-modal-item {
  display: inline-block;
  background: #f5f5f7;
  border: 1px solid #e8e8ed;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  transition: all 0.15s ease;
}

.list-modal-item:hover {
  background: #ebebf0;
  border-color: #d2d2d7;
}

.list-modal-type-item {
  width: 100%;
  background: #f9f9fb;
  border: 1px solid #e8e8ed;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 2px;
}

.list-modal-type-item .type-name {
  font-size: 15px;
  font-weight: 600;
  color: #0066cc;
  margin-bottom: 8px;
}

.type-pairs-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pair-tag {
  display: inline-block;
  background: #ffffff;
  border: 1px solid #d2d2d7;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
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

