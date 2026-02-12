<template>
  <div v-if="statistics" class="conservation-analysis">
    <h3 class="statistics-title">Conservation Analysis</h3>
    
    <!-- Key Metrics -->
    <div class="key-metrics">
      <div class="metric-card">
        <div class="metric-value">{{ statistics.residue.cr50 }}</div>
        <div class="metric-label">
          CR<sub>{{ Math.round(effectivePairThreshold * 100) }}</sub>
          <span class="info-icon" @mouseenter="showTooltip($event, `Conserved Residue pairs: Number of unique pairs present in ≥${Math.round(effectivePairThreshold * 100)}% of trajectory frames`)" @mouseleave="hideTooltip">ⓘ</span>
        </div>
        <div class="metric-desc">Conserved pairs</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ statistics.atomic.ca }}</div>
        <div class="metric-label">
          CA<sub>{{ Math.round(effectiveTypeThreshold * 100) }}</sub>
          <span class="info-icon" @mouseenter="showTooltip($event, `Conserved Atomic interactions: Pair-type combinations with ≥${Math.round(effectiveTypeThreshold * 100)}% type conservation`)" @mouseleave="hideTooltip">ⓘ</span>
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
                @mouseenter="showTooltip($event, `${typeInfo.type} — ${formatPercent(typeInfo.conservation)} (${Math.round(typeInfo.conservation * dataStore.totalFrames)}/${dataStore.totalFrames} frames)`)"
                @mouseleave="hideTooltip"
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
                @mouseenter="showTooltip($event, `${typeInfo.type} — ${formatPercent(typeInfo.conservation)} (${Math.round(typeInfo.conservation * dataStore.totalFrames)}/${dataStore.totalFrames} frames)`)"
                @mouseleave="hideTooltip"
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
    
    <!-- Global Tooltip -->
    <Teleport to="body">
      <div 
        v-if="activeTooltip.visible" 
        class="ca-global-tooltip"
        :style="{ top: activeTooltip.y + 'px', left: activeTooltip.x + 'px' }"
      >
        {{ activeTooltip.text }}
      </div>
    </Teleport>
    
    <!-- List Modal for expanded items -->
    <Teleport to="body">
      <div v-if="listModal.visible" class="ca-list-modal-overlay" @click.self="closeListModal">
        <div class="ca-list-modal-panel">
          <div class="ca-list-modal-header">
            <h3>{{ listModal.title }}</h3>
            <span v-if="listModal.badge" class="ca-list-modal-badge">{{ listModal.badge }}</span>
            <button class="ca-list-modal-close" @click="closeListModal">×</button>
          </div>
          <div class="ca-list-modal-content">
            <!-- Type list (for Most Conserved Types) -->
            <div v-if="listModal.isTypeList" class="ca-list-modal-items">
              <div v-for="(item, idx) in listModal.items" :key="idx" class="ca-list-modal-type-item">
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
            <div v-else-if="listModal.isPairList" class="ca-list-modal-items pair-list">
              <div v-for="(item, idx) in listModal.items" :key="idx" class="ca-list-modal-pair-item">
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
                    @mouseenter="showTooltip($event, `${typeInfo.type} — ${formatPercent(typeInfo.conservation)} (${Math.round(typeInfo.conservation * dataStore.totalFrames)}/${dataStore.totalFrames} frames)`)"
                    @mouseleave="hideTooltip"
                  >{{ typeInfo.type }}</span>
                </div>
              </div>
            </div>
            <!-- Simple list (fallback) -->
            <div v-else class="ca-list-modal-items">
              <span v-for="(item, idx) in listModal.items" :key="idx" class="ca-list-modal-item">{{ item }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useDataStore } from '../stores/dataStore'
import { getInteractionBaseColor, matchesSelectedTypes, formatResiduePairFromIds, formatPairKey } from '../utils/chartHelpers'
import { INTERACTION_TYPES } from '../utils/constants'

const props = defineProps({
  pairThreshold: {
    type: Number,
    default: null
  },
  typeThreshold: {
    type: Number,
    default: null
  }
})

const dataStore = useDataStore()
const statistics = ref(null)

// Effective thresholds: use prop if provided, otherwise fall back to the global slider value
const effectivePairThreshold = computed(() => props.pairThreshold ?? dataStore.currentThreshold)
const effectiveTypeThreshold = computed(() => props.typeThreshold ?? 0.5)

// Tooltip state
const activeTooltip = ref({
  visible: false,
  text: '',
  x: 0,
  y: 0
})

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

const hideTooltip = () => {
  activeTooltip.value.visible = false
}

// List modal state
const listModal = ref({
  visible: false,
  title: '',
  items: [],
  badge: '',
  isTypeList: false,
  isPairList: false
})

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

// Helper: get text color for background
const getTextColorForBg = (typeLabel) => {
  const colorStr = getInteractionBaseColor(typeLabel)
  const match = colorStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
  if (!match) return '#ffffff'
  const r = parseInt(match[1])
  const g = parseInt(match[2])
  const b = parseInt(match[3])
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#1d1d1f' : '#ffffff'
}

// Helper: format percentage
const formatPercent = (value) => {
  return `${(value * 100).toFixed(2)}%`
}

// Helper: ordinal
const getOrdinal = (n) => {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

// Helper: calculate quartiles
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

// Helper: calculate statistics
const calculateStatistics = (values) => {
  if (values.length === 0) {
    return { count: 0, mean: 0, median: 0, q1: 0, q3: 0, min: 0, max: 0, stdDev: 0 }
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

// Helper: assign dense ranks
const assignRanks = (sortedItems, valueKey) => {
  let currentRank = 1
  return sortedItems.map((item, idx) => {
    if (idx > 0 && item[valueKey] < sortedItems[idx - 1][valueKey]) {
      currentRank++
    }
    return { ...item, rank: currentRank }
  })
}

// Main statistics computation
const computeStatistics = () => {
  const allInteractions = dataStore.filteredInteractions
  if (allInteractions.length === 0) {
    statistics.value = null
    return
  }

  // Filter pairs by pair conservation threshold
  const stablePairs = allInteractions.filter(interaction => interaction.consistency >= effectivePairThreshold.value)
  if (stablePairs.length === 0) {
    statistics.value = null
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

  const sortedPairs = Array.from(pairMap.values()).sort((a, b) => {
    const numA1 = parseInt(a.id1.match(/\d+/)?.[0] || '0')
    const numA2 = parseInt(a.id2.match(/\d+/)?.[0] || '0')
    const numB1 = parseInt(b.id1.match(/\d+/)?.[0] || '0')
    const numB2 = parseInt(b.id2.match(/\d+/)?.[0] || '0')
    if (numA1 !== numB1) return numA1 - numB1
    return numA2 - numB2
  })

  // Collect data for statistics
  const residueScores = []
  const atomicScores = []
  const uniquePairs = new Set()
  const typeConservationMap = new Map()
  const typeFramesMap = new Map()
  const pairConservationMap = new Map()
  const pairFramesMap = new Map()
  const typeToPairsMap = new Map()
  const pairToTypesMap = new Map()
  const allPairToTypesMap = new Map()
  const pairTypeFramesMap = new Map()
  const typeToPairConservationMap = new Map()

  // Count pair-type combinations meeting threshold (for CA metric)
  let pairTypeCombCount = 0

  sortedPairs.forEach((pairData) => {
    pairData.interactions.forEach(interaction => {
      // Residue level
      if (interaction.consistency !== undefined && interaction.consistency !== null && interaction.consistency >= effectivePairThreshold.value) {
        residueScores.push(interaction.consistency)
        const pairKey = formatPairKey(interaction.id1, interaction.id2)
        uniquePairs.add(pairKey)

        const pairLabel = formatResiduePairFromIds(interaction.id1, interaction.id2)
        if (!pairConservationMap.has(pairLabel)) {
          pairConservationMap.set(pairLabel, [])
        }
        pairConservationMap.get(pairLabel).push(interaction.consistency)

        if (!pairFramesMap.has(pairLabel)) {
          pairFramesMap.set(pairLabel, [])
        }
        if (interaction.frames && Array.isArray(interaction.frames)) {
          pairFramesMap.get(pairLabel).push(...interaction.frames)
        }
      }

      // Atomic level
      const typePersistence = interaction.typePersistence || {}
      const typeFrames = interaction.typeFrames || {}
      const pairLabel = formatResiduePairFromIds(interaction.id1, interaction.id2)

      interaction.typesArray.forEach((type) => {
        const typeConservation = typePersistence[type]

        // Track ALL types for each pair (for stats cards display)
        if (typeConservation !== undefined && typeConservation !== null) {
          if (!allPairToTypesMap.has(pairLabel)) {
            allPairToTypesMap.set(pairLabel, new Map())
          }
          allPairToTypesMap.get(pairLabel).set(type, typeConservation)
        }

        // Check threshold
        if (typeConservation === undefined || typeConservation === null || typeConservation < effectiveTypeThreshold.value) {
          return
        }

        // Check interaction type filter
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return
          }
        }

        pairTypeCombCount++
        atomicScores.push(typeConservation)

        if (!typeConservationMap.has(type)) {
          typeConservationMap.set(type, [])
        }
        typeConservationMap.get(type).push(typeConservation)

        if (!typeToPairsMap.has(type)) {
          typeToPairsMap.set(type, new Set())
        }
        typeToPairsMap.get(type).add(pairLabel)

        if (!pairToTypesMap.has(pairLabel)) {
          pairToTypesMap.set(pairLabel, new Map())
        }
        pairToTypesMap.get(pairLabel).set(type, typeConservation)

        if (!typeToPairConservationMap.has(type)) {
          typeToPairConservationMap.set(type, new Map())
        }
        typeToPairConservationMap.get(type).set(pairLabel, typeConservation)

        const framesForType = typeFrames[type] || []
        if (framesForType.length > 0) {
          if (!typeFramesMap.has(type)) {
            typeFramesMap.set(type, [])
          }
          typeFramesMap.get(type).push(...framesForType)

          const pairTypeKey = `${pairLabel}_${type}`
          if (!pairTypeFramesMap.has(pairTypeKey)) {
            pairTypeFramesMap.set(pairTypeKey, { pair: pairLabel, type: type, frames: [] })
          }
          pairTypeFramesMap.get(pairTypeKey).frames.push(...framesForType)
        }
      })
    })
  })

  // Most conserved pairs
  const allPairsWithConservation = []
  pairConservationMap.forEach((scores, pairLabel) => {
    const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
    const frames = pairFramesMap.get(pairLabel) || []
    const uniqueFrameCount = new Set(frames).size
    allPairsWithConservation.push({ pair: pairLabel, conservation: avgConservation, frameCount: uniqueFrameCount })
  })
  allPairsWithConservation.sort((a, b) => b.frameCount - a.frameCount)

  // Longest stretch per pair
  const allPairsWithStretch = []
  pairFramesMap.forEach((allFrames, pairLabel) => {
    const uniqueFrames = [...new Set(allFrames)].sort((a, b) => a - b)
    if (uniqueFrames.length === 0) return
    let currentStretch = 1, maxStretch = 1
    let maxStretchStart = uniqueFrames[0], maxStretchEnd = uniqueFrames[0], currentStart = uniqueFrames[0]
    for (let i = 1; i < uniqueFrames.length; i++) {
      if (uniqueFrames[i] === uniqueFrames[i - 1] + 1) {
        currentStretch++
        if (currentStretch > maxStretch) {
          maxStretch = currentStretch
          maxStretchStart = currentStart
          maxStretchEnd = uniqueFrames[i]
        }
      } else {
        currentStretch = 1
        currentStart = uniqueFrames[i]
      }
    }
    const typesMap = allPairToTypesMap.get(pairLabel) || new Map()
    allPairsWithStretch.push({
      pair: pairLabel,
      stretchLength: maxStretch,
      stretchInfo: `${maxStretch} frames (${maxStretchStart}-${maxStretchEnd})`,
      typeCount: typesMap.size
    })
  })
  allPairsWithStretch.sort((a, b) => {
    if (b.stretchLength !== a.stretchLength) return b.stretchLength - a.stretchLength
    return a.typeCount - b.typeCount
  })

  // Most conserved types
  const allTypesWithConservation = []
  typeConservationMap.forEach((scores, type) => {
    const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
    const pairs = typeToPairsMap.get(type) ? Array.from(typeToPairsMap.get(type)) : []
    allTypesWithConservation.push({ type, conservation: avgConservation, pairs: pairs.sort() })
  })
  allTypesWithConservation.sort((a, b) => b.conservation - a.conservation)

  // Build ranked lists
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

  const rankedTypes = assignRanks(allTypesWithConservation, 'conservation')

  // Build final statistics
  const residueStats = calculateStatistics(residueScores)
  residueStats.cr50 = uniquePairs.size
  residueStats.mostConservedList = mostConservedPairsWithTypes
  residueStats.longestStretchList = longestStretchList

  const atomicStats = calculateStatistics(atomicScores)
  atomicStats.ca = pairTypeCombCount
  atomicStats.mostConservedList = rankedTypes

  statistics.value = {
    residue: residueStats,
    atomic: atomicStats
  }
}

// Watch for data changes and recompute
watch(
  [
    () => dataStore.filteredInteractions,
    () => dataStore.totalFrames,
    () => [...dataStore.selectedInteractionTypes],
    effectivePairThreshold,
    effectiveTypeThreshold
  ],
  () => {
    computeStatistics()
  },
  { immediate: true, deep: true }
)
</script>

<style scoped>
.conservation-analysis {
  margin-top: 32px;
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

/* Key Metrics */
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

.insight-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  flex: 1;
}

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

.pair-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  min-width: 120px;
}

.frame-count {
  font-size: 12px;
  color: #6e6e73;
  font-weight: 500;
  margin-left: auto;
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
  cursor: help;
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

.type-pairs-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>

<style>
/* Global tooltip - teleported to body */
.ca-global-tooltip {
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
  animation: caTooltipFadeIn 0.15s ease;
}

@keyframes caTooltipFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* List Modal */
.ca-list-modal-overlay {
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
  animation: caFadeIn 0.2s ease;
}

@keyframes caFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.ca-list-modal-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  max-height: 80vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: caSlideUp 0.2s ease;
}

@keyframes caSlideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.ca-list-modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8ed;
}

.ca-list-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  flex: 1;
}

.ca-list-modal-badge {
  background: linear-gradient(135deg, #3B6EF5 0%, #2B5CE5 100%);
  color: white;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 14px;
}

.ca-list-modal-close {
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

.ca-list-modal-close:hover {
  background-color: #f5f5f7;
  color: #1d1d1f;
}

.ca-list-modal-content {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.ca-list-modal-items {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.ca-list-modal-items.pair-list {
  flex-direction: column;
}

.ca-list-modal-item {
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

.ca-list-modal-item:hover {
  background: #ebebf0;
  border-color: #d2d2d7;
}

.ca-list-modal-pair-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  background: #f9f9fb;
  border-radius: 8px;
  border: 1px solid #e8e8ed;
}

.ca-list-modal-pair-item .pair-rank-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ca-list-modal-pair-item .pair-name {
  min-width: 100px;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.ca-list-modal-type-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  background: #f9f9fb;
  border-radius: 10px;
  border: 1px solid #e8e8ed;
  margin-bottom: 2px;
}
</style>
