<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-surface"></div>
    <AtomPairExplorer 
      :visible="showAtomExplorer" 
      :residue-pair="selectedResiduePair"
      @close="closeAtomExplorer"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import DependencyWheelModule from 'highcharts/modules/dependency-wheel'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionColor } from '../../utils/chartHelpers'
import AtomPairExplorer from '../AtomPairExplorer.vue'

DependencyWheelModule(Highcharts)

// Function to reorder nodes in a dependency wheel series after chart load
const reorderDependencyWheelNodes = (chart) => {
  if (chart._reorderingInProgress) return
  
  const series = chart.series.find(s => s.type === 'dependencywheel')
  if (!series?.nodes?.length) return
  
  // Check if nodes have custom order
  const hasCustomOrder = series.nodes.some(n => n.options?.order !== undefined)
  if (!hasCustomOrder) return
  
  console.log('Reordering dependency wheel nodes...')
  console.log('Before sort:', series.nodes.map(n => n.id).slice(0, 10))
  
  // Sort nodes by our custom order
  series.nodes.sort((a, b) => (a.options?.order ?? 999) - (b.options?.order ?? 999))
  
  console.log('After sort:', series.nodes.map(n => n.id).slice(0, 10))
  
  // Recalculate angular positions based on new order
  const startAngle = (series.options.startAngle || 0) * Math.PI / 180
  const total = series.nodes.reduce((sum, n) => sum + (n.sum || 0), 0)
  const nodePadding = (series.options.nodePadding || 0) * Math.PI / 180
  const availableAngle = 2 * Math.PI - series.nodes.length * nodePadding
  
  let cumulative = startAngle
  
  series.nodes.forEach((node, i) => {
    node.index = i
    const nodeAngle = total > 0 ? (node.sum / total) * availableAngle : 0
    
    if (node.shapeArgs) {
      node.shapeArgs.start = cumulative
      node.shapeArgs.end = cumulative + nodeAngle
    }
    
    cumulative += nodeAngle + nodePadding
  })
  
  // Redraw to apply changes - prevent infinite loop
  chart._reorderingInProgress = true
  chart.redraw(false)
  chart._reorderingInProgress = false
}

const showAtomExplorer = ref(false)
const selectedResiduePair = ref(null)

const closeAtomExplorer = () => {
  showAtomExplorer.value = false
  selectedResiduePair.value = null
}

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null

const getDominantType = (typesArray = [], typePersistence = {}, fallback = 0) => {
  if (!typesArray.length) return null
  let dominant = typesArray[0]
  let dominantValue = typePersistence[dominant] ?? fallback
  typesArray.forEach(type => {
    const value = typePersistence[type] ?? fallback
    if (value > dominantValue) {
      dominant = type
      dominantValue = value
    }
  })
  return dominant
}

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

  // Helper to check if a residue ID belongs to Chain A (format: RES123_A)
  const isChainA = (id) => id && id.endsWith('_A')
  
  // Sort numerically by residue number
  const sortNumeric = (a, b) => {
    const numA = parseInt(a.match(/\d+/)?.[0] || '0')
    const numB = parseInt(b.match(/\d+/)?.[0] || '0')
    return numA - numB
  }
  
  // First: collect all unique node IDs and separate by chain
  const chainAIds = new Set()
  const chainBIds = new Set()
  
  filteredData.forEach(interaction => {
    if (isChainA(interaction.id1)) chainAIds.add(interaction.id1)
    else chainBIds.add(interaction.id1)
    if (isChainA(interaction.id2)) chainAIds.add(interaction.id2)
    else chainBIds.add(interaction.id2)
  })
  
  const chainA = Array.from(chainAIds).sort(sortNumeric)
  const chainB = Array.from(chainBIds).sort(sortNumeric)
  
  // Create TRUE interleaved order: A, B, A, B, A, B...
  // If lengths differ, distribute extras evenly
  const createInterleavedOrder = () => {
    if (chainA.length === 0) return [...chainB]
    if (chainB.length === 0) return [...chainA]
    
    const result = []
    const total = chainA.length + chainB.length
    let aIdx = 0, bIdx = 0
    
    for (let i = 0; i < total; i++) {
      // Calculate ideal ratio position for each chain
      const aIdeal = (chainA.length / total) * (i + 1)
      const bIdeal = (chainB.length / total) * (i + 1)
      
      // Pick from whichever chain is more "behind" its ideal position
      const aBehind = aIdx < aIdeal && aIdx < chainA.length
      const bBehind = bIdx < bIdeal && bIdx < chainB.length
      
      if (aBehind && (!bBehind || (aIdeal - aIdx) >= (bIdeal - bIdx))) {
        result.push(chainA[aIdx++])
      } else if (bIdx < chainB.length) {
        result.push(chainB[bIdx++])
      } else if (aIdx < chainA.length) {
        result.push(chainA[aIdx++])
      }
    }
    return result
  }
  
  const interleavedOrder = createInterleavedOrder()
  
  // Create a map for quick position lookup
  const nodePositionMap = new Map(interleavedOrder.map((id, idx) => [id, idx]))
  
  // Build nodes in interleaved order with explicit order property
  // The order property is crucial - Highcharts will use it to position nodes
  const nodes = new Map()
  interleavedOrder.forEach((id, index) => {
    const color = isChainA(id) ? '#3B6EF5' : '#FF8A4C'
    nodes.set(id, {
      id: id,
      name: id,
      color: color,
      order: index, // Explicit order for Highcharts positioning
      marker: {
        radius: 8,
        symbol: 'circle',
        fillColor: color,
        lineWidth: 2,
        lineColor: '#ffffff',
        states: {
          hover: {
            radius: 10,
            lineWidth: 3
          }
        }
      }
    })
  })
  
  // Build links from filtered data, sorted to introduce nodes in our desired order
  // Highcharts creates nodes as it encounters them in links - order matters!
  const rawLinks = filteredData.map(interaction => {
    const frames = Array.isArray(interaction.frames) ? interaction.frames : []
    const typePersistence = interaction.typePersistence || {}
    const typesArray = interaction.typesArray || []
    const dominantType = getDominantType(typesArray, typePersistence, interaction.consistency)

    return {
      from: interaction.id1,
      to: interaction.id2,
      weight: interaction.frameCount,
      consistency: interaction.consistency,
      types: interaction.typesArray.join('; '),
      typesArray,
      typePersistence,
      frames,
      dominantType,
      color: getInteractionColor(dominantType || interaction.typesArray.join('; '), interaction.consistency)
    }
  })
  
  // Sort links so that nodes are "discovered" in our interleaved order
  // Priority: links that introduce nodes earlier in our order should come first
  const discoveredNodes = new Set()
  const sortedLinks = []
  const remainingLinks = [...rawLinks]
  
  // Process links in order of which introduces the earliest undiscovered node
  while (remainingLinks.length > 0) {
    let bestIndex = 0
    let bestScore = Infinity
    
    for (let i = 0; i < remainingLinks.length; i++) {
      const link = remainingLinks[i]
      const fromPos = nodePositionMap.get(link.from) ?? Infinity
      const toPos = nodePositionMap.get(link.to) ?? Infinity
      
      // Score based on the earliest undiscovered node this link would introduce
      let score = Infinity
      if (!discoveredNodes.has(link.from)) score = Math.min(score, fromPos)
      if (!discoveredNodes.has(link.to)) score = Math.min(score, toPos)
      
      // If this link introduces an earlier node, prefer it
      if (score < bestScore) {
        bestScore = score
        bestIndex = i
      }
    }
    
    const selectedLink = remainingLinks.splice(bestIndex, 1)[0]
    sortedLinks.push(selectedLink)
    discoveredNodes.add(selectedLink.from)
    discoveredNodes.add(selectedLink.to)
  }
  
  const links = sortedLinks

  // nodesArray is already in interleaved order since we built it that way
  const nodesArray = interleavedOrder.map(id => nodes.get(id))
  
  // Debug: log the node order to verify interleaving
  console.log('=== CHORD DIAGRAM DEBUG ===')
  console.log('Chain A count:', chainA.length, 'Chain B count:', chainB.length)
  console.log('Interleaved order (first 10):', interleavedOrder.slice(0, 10))
  console.log('First 5 links introduce nodes:', links.slice(0, 5).map(l => `${l.from} -> ${l.to}`))
  console.log('Node order passed to Highcharts:', nodesArray.map(n => `${n.id}(order:${n.order})`).slice(0, 10))

  if (chart) {
    chart.destroy()
  }

  const chartOptions = {
    chart: {
      type: 'dependencywheel',
      backgroundColor: 'transparent',
      height: 850,
      marginTop: 80,
      events: {
        load: function() {
          // Reorder nodes after chart is fully loaded
          setTimeout(() => reorderDependencyWheelNodes(this), 100)
        }
      }
    },
    title: {
      text: `Residue Interaction Chord (${filteredData.length} interactions)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Chain A ↔ Chain B | Threshold: ${Math.round(dataStore.currentThreshold * 100)}%`,
      style: {
        fontSize: '17px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    plotOptions: {
      dependencywheel: {
        curveFactor: 0.55,
        colorByPoint: false,
        borderWidth: 2,
        borderColor: '#ffffff',
        nodeWidth: 20,
        nodePadding: 2,
        dataLabels: {
          style: {
            fontSize: '11px',
            fontWeight: '600',
            textOutline: 'none'
          }
        },
        states: {
          hover: {
            brightness: 0.1,
            borderWidth: 3
          }
        }
      }
    },
    series: [{
      keys: ['from', 'to', 'weight'],
      type: 'dependencywheel',
      name: 'Interactions',
      data: links,
      nodes: nodesArray,
      point: {
        events: {
          click: function() {
            selectedResiduePair.value = {
              id1: this.from,
              id2: this.to
            }
            showAtomExplorer.value = true
          }
        }
      }
    }],
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      formatter: function() {
        if (this.point.from) {
          const persistencePercent = Math.round(this.point.consistency * 100)
          const typesList = this.point.typesArray || []
          const typePersistence = this.point.typePersistence || {}
          const dominantType = this.point.dominantType || typesList[0] || null
          const sortedTypes = dominantType
            ? [dominantType, ...typesList.filter(type => type !== dominantType)]
            : typesList
          // Get frames - check both point.frames and ensure it's an array
          const frames = Array.isArray(this.point.frames) ? this.point.frames : (this.point.frames ? [this.point.frames] : [])
          const totalFrames = dataStore.totalFrames
          
          // Create simple frame line - compact visualization
          const frameLineWidth = 280
          const frameLineHeight = 10
          const frameSet = new Set(frames)
          
          // Create background pattern using linear gradient stops
          const gradientStops = []
          for (let i = 1; i <= totalFrames; i++) {
            const position = ((i - 1) / totalFrames) * 100
            const hasInteraction = frameSet.has(i)
            const color = hasInteraction ? '#42A5F5' : '#e8e8ed'
            gradientStops.push(`${color} ${position}%`)
            gradientStops.push(`${color} ${(i / totalFrames) * 100}%`)
          }
          
          const frameLineStyle = `width: ${frameLineWidth}px; height: ${frameLineHeight}px; background: linear-gradient(to right, ${gradientStops.join(', ')}); border-radius: 2px;`
          
          // Use per-type persistence if available, otherwise fall back to overall conservation
          const typesHtml = sortedTypes.map(type => {
            const typePersist = typePersistence[type] !== undefined 
              ? typePersistence[type] 
              : this.point.consistency
            const typePercent = Math.round(typePersist * 100)
            return `<div style="margin-bottom: 3px;">
              <span style="color: #1d1d1f; font-weight: 500;">${type}:</span>
              <span style="color: #6e6e73; margin-left: 6px;">${typePercent}%</span>
            </div>`
          }).join('')
          
          return `
            <div style="padding: 10px;">
              <div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">
                ${this.point.from} ↔ ${this.point.to}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #1d1d1f; font-weight: 600;">Overall Conservation: ${persistencePercent}%</span>
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #6e6e73;">Frames: ${this.point.weight} / ${totalFrames}</span>
              </div>
              <div style="margin-top: 8px; margin-bottom: 8px; padding-top: 8px; border-top: 1px solid #e8e8ed;">
                <div style="color: #1d1d1f; font-weight: 600; font-size: 12px; margin-bottom: 6px;">Frame Occurrence:</div>
                <div style="${frameLineStyle}"></div>
              </div>
              <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e8e8ed;">
                <div style="color: #1d1d1f; font-weight: 600; font-size: 12px; margin-bottom: 6px;">Interaction Types:</div>
                <div style="color: #6e6e73; font-size: 12px;">
                  ${typesHtml}
                </div>
              </div>
              <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e8e8ed;">
                <div style="color: #3B6EF5; font-size: 11px; font-weight: 500;">
                  💡 Click to view atom pair details
                </div>
              </div>
            </div>
          `
        }
        return false
      }
    }
  }

  const systemName = dataStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `chord-diagram-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.currentThreshold,
  () => dataStore.filteredInteractions.length,
  () => dataStore.selectedInteractionTypes.size
], () => {
  if (dataStore.currentChartType === 'chord') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
}

.chart-surface {
  width: 100%;
  height: 100%;
}
</style>

