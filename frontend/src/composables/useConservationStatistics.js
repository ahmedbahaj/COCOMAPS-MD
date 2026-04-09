/**
 * Shared conservation statistics (Most Conserved Pairs, etc.) from filtered interactions.
 * Used by ConservationAnalysis and 3D Visualization (ConservedIslandsList).
 */
import { ref, watch, computed, unref } from 'vue'
import { useAnalysisStore } from '../stores/analysisStore'
import { useChartUiStore } from '../stores/chartUiStore'
import { useSystemsStore } from '../stores/systemsStore'
import { formatResiduePairFromIds, formatPairKey, matchesSelectedTypes } from '../utils/chartHelpers'
import { INTERACTION_TYPES } from '../utils/constants'

function calculateQuartile(sortedArray, q) {
  if (sortedArray.length === 0) return 0
  const pos = (sortedArray.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  if (sortedArray[base + 1] !== undefined) {
    return sortedArray[base] + rest * (sortedArray[base + 1] - sortedArray[base])
  }
  return sortedArray[base]
}

function calculateStatistics(values) {
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

function assignRanks(sortedItems, valueKey) {
  let currentRank = 1
  return sortedItems.map((item, idx) => {
    if (idx > 0 && item[valueKey] < sortedItems[idx - 1][valueKey]) {
      currentRank++
    }
    return { ...item, rank: currentRank }
  })
}

/**
 * @param {Object} [options]
 * @param {import('vue').Ref<number>} [options.pairThreshold] - Override pair conservation threshold (default: chart UI store currentThreshold)
 * @param {import('vue').Ref<number>} [options.typeThreshold] - Override type conservation threshold (default: 0.5)
 * @returns {{ statistics: import('vue').Ref<Object|null> }}
 */
export function useConservationStatistics(options = {}) {
  const analysisStore = useAnalysisStore()
  const chartUiStore = useChartUiStore()
  const systemsStore = useSystemsStore()
  const statistics = ref(null)

  const effectivePairThreshold = computed(() => {
    const t = unref(options.pairThreshold)
    return t !== undefined && t !== null ? t : chartUiStore.currentThreshold
  })
  const effectiveTypeThreshold = computed(() => {
    const t = unref(options.typeThreshold)
    return t !== undefined && t !== null ? t : 0.5
  })

  function computeStatistics() {
    const allInteractions = analysisStore.filteredInteractions
    if (allInteractions.length === 0) {
      statistics.value = null
      return
    }

    const stablePairs = allInteractions.filter(
      (interaction) => interaction.consistency >= effectivePairThreshold.value
    )
    if (stablePairs.length === 0) {
      statistics.value = null
      return
    }

    const pairMap = new Map()
    stablePairs.forEach((interaction) => {
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
    let pairTypeCombCount = 0

    sortedPairs.forEach((pairData) => {
      pairData.interactions.forEach((interaction) => {
        if (
          interaction.consistency !== undefined &&
          interaction.consistency !== null &&
          interaction.consistency >= effectivePairThreshold.value
        ) {
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

        const typePersistence = interaction.typePersistence || {}
        const typeFrames = interaction.typeFrames || {}
        const pairLabel = formatResiduePairFromIds(interaction.id1, interaction.id2)

        interaction.typesArray.forEach((type) => {
          const typeConservation = typePersistence[type]
          if (typeConservation !== undefined && typeConservation !== null) {
            if (!allPairToTypesMap.has(pairLabel)) {
              allPairToTypesMap.set(pairLabel, new Map())
            }
            allPairToTypesMap.get(pairLabel).set(type, typeConservation)
          }
          if (
            typeConservation === undefined ||
            typeConservation === null ||
            typeConservation < effectiveTypeThreshold.value
          ) {
            return
          }
          if (chartUiStore.selectedInteractionTypes.size > 0) {
            if (
              !matchesSelectedTypes(type, chartUiStore.selectedInteractionTypes, INTERACTION_TYPES)
            ) {
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
              pairTypeFramesMap.set(pairTypeKey, { pair: pairLabel, type, frames: [] })
            }
            pairTypeFramesMap.get(pairTypeKey).frames.push(...framesForType)
          }
        })
      })
    })

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
    allPairsWithConservation.sort((a, b) => b.frameCount - a.frameCount)

    const allPairsWithStretch = []
    pairFramesMap.forEach((allFrames, pairLabel) => {
      const uniqueFrames = [...new Set(allFrames)].sort((a, b) => a - b)
      if (uniqueFrames.length === 0) return
      let currentStretch = 1
      let maxStretch = 1
      let maxStretchStart = uniqueFrames[0]
      let maxStretchEnd = uniqueFrames[0]
      let currentStart = uniqueFrames[0]
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

    const allTypesWithConservation = []
    typeConservationMap.forEach((scores, type) => {
      const avgConservation = scores.reduce((sum, val) => sum + val, 0) / scores.length
      const pairs = typeToPairsMap.get(type) ? Array.from(typeToPairsMap.get(type)) : []
      allTypesWithConservation.push({
        type,
        conservation: avgConservation,
        pairs: pairs.sort()
      })
    })
    allTypesWithConservation.sort((a, b) => b.conservation - a.conservation)

    const rankedPairs = assignRanks(allPairsWithConservation, 'frameCount')
    const mostConservedPairsWithTypes = rankedPairs.map((item) => {
      const typesMap = allPairToTypesMap.get(item.pair) || new Map()
      return {
        pair: item.pair,
        frameCount: item.frameCount,
        rank: item.rank,
        types: Array.from(typesMap.entries())
          .map(([type, conservation]) => ({ type, conservation }))
          .sort((a, b) => b.conservation - a.conservation)
      }
    })

    const rankedStretches = assignRanks(allPairsWithStretch, 'stretchLength')
    const longestStretchList = rankedStretches.map((item) => {
      const typesMap = allPairToTypesMap.get(item.pair) || new Map()
      return {
        pair: item.pair,
        stretchLength: item.stretchLength,
        stretchInfo: item.stretchInfo,
        rank: item.rank,
        types: Array.from(typesMap.entries())
          .map(([type, conservation]) => ({ type, conservation }))
          .sort((a, b) => b.conservation - a.conservation)
      }
    })

    const rankedTypes = assignRanks(allTypesWithConservation, 'conservation')

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

  watch(
    [
      () => analysisStore.filteredInteractions,
      () => systemsStore.totalFrames,
      () => [...chartUiStore.selectedInteractionTypes],
      effectivePairThreshold,
      effectiveTypeThreshold
    ],
    () => computeStatistics(),
    { immediate: true, deep: true }
  )

  return { statistics }
}
