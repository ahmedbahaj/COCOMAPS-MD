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
import SankeyModule from 'highcharts/modules/sankey'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionColor } from '../../utils/chartHelpers'
import AtomPairExplorer from '../AtomPairExplorer.vue'

SankeyModule(Highcharts)

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
  
  // Collect all unique node IDs and separate by chain
  const chainAIds = new Set()
  const chainBIds = new Set()
  
  filteredData.forEach(interaction => {
    if (isChainA(interaction.id1)) chainAIds.add(interaction.id1)
    else chainBIds.add(interaction.id1)
    if (isChainA(interaction.id2)) chainAIds.add(interaction.id2)
    else chainBIds.add(interaction.id2)
  })
  
  // Sort each chain numerically
  const chainA = Array.from(chainAIds).sort(sortNumeric)
  const chainB = Array.from(chainBIds).sort(sortNumeric)
  
  // Build nodes with explicit column and order for Sankey
  // Column 0 = Chain A (left), Column 1 = Chain B (right)
  const nodes = new Map()
  
  // Add Chain A nodes (column 0, ordered top to bottom)
  chainA.forEach((id, index) => {
    nodes.set(id, {
      id: id,
      name: id,
      color: '#3B6EF5',
      column: 0,
      order: index
    })
  })
  
  // Add Chain B nodes (column 1, ordered top to bottom)
  chainB.forEach((id, index) => {
    nodes.set(id, {
      id: id,
      name: id,
      color: '#FF8A4C',
      column: 1,
      order: index
    })
  })
  
  // Build links from filtered data
  const links = filteredData.map(interaction => {
    const frames = Array.isArray(interaction.frames) ? interaction.frames : []
    const typePersistence = interaction.typePersistence || {}
    const typesArray = interaction.typesArray || []
    const dominantType = getDominantType(typesArray, typePersistence, interaction.consistency)

    // Ensure from is always Chain A and to is always Chain B for consistent flow direction
    const fromId = isChainA(interaction.id1) ? interaction.id1 : interaction.id2
    const toId = isChainA(interaction.id1) ? interaction.id2 : interaction.id1

    return {
      from: fromId,
      to: toId,
      weight: interaction.frameCount,
      consistency: interaction.consistency,
      types: interaction.typesArray.join('; '),
      typesArray,
      typePersistence,
      frames,
      dominantType,
      color: getInteractionColor(dominantType || interaction.typesArray.join('; '), interaction.consistency),
      // Store original IDs for click handler
      originalId1: interaction.id1,
      originalId2: interaction.id2
    }
  })

  const nodesArray = Array.from(nodes.values())
  
  // Debug logging
  console.log('=== SANKEY DIAGRAM DEBUG ===')
  console.log('Chain A count:', chainA.length, 'Chain B count:', chainB.length)
  console.log('Chain A nodes (first 5):', chainA.slice(0, 5))
  console.log('Chain B nodes (first 5):', chainB.slice(0, 5))

  if (chart) {
    chart.destroy()
  }

  // Calculate dynamic height based on number of nodes
  const maxNodes = Math.max(chainA.length, chainB.length)
  const dynamicHeight = Math.max(600, Math.min(1500, maxNodes * 35 + 200))

  const chartOptions = {
    chart: {
      type: 'sankey',
      backgroundColor: 'transparent',
      height: dynamicHeight,
      marginTop: 80
    },
    title: {
      text: `Residue Interaction Flow (${filteredData.length} interactions)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Chain A → Chain B | Threshold: ${Math.round(dataStore.currentThreshold * 100)}%`,
      style: {
        fontSize: '17px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    plotOptions: {
      sankey: {
        curveFactor: 0.5,
        colorByPoint: false,
        nodeWidth: 20,
        nodePadding: 8,
        minLinkWidth: 2,
        borderWidth: 0,
        dataLabels: {
          enabled: true,
          style: {
            fontSize: '11px',
            fontWeight: '600',
            textOutline: 'none',
            color: '#1d1d1f'
          },
          nodeFormat: '{point.name}',
          padding: 5
        },
        states: {
          hover: {
            brightness: 0.1
          }
        }
      }
    },
    series: [{
      keys: ['from', 'to', 'weight'],
      type: 'sankey',
      name: 'Interactions',
      data: links,
      nodes: nodesArray,
      point: {
        events: {
          click: function() {
            if (this.from && this.to) {
              selectedResiduePair.value = {
                id1: this.originalId1 || this.from,
                id2: this.originalId2 || this.to
              }
              showAtomExplorer.value = true
            }
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
      nodeFormatter: function() {
        const isA = this.id.endsWith('_A')
        return `
          <div style="padding: 8px;">
            <div style="font-size: 14px; font-weight: 600; color: ${isA ? '#3B6EF5' : '#FF8A4C'};">
              ${this.name}
            </div>
            <div style="color: #6e6e73; font-size: 12px; margin-top: 4px;">
              Chain ${isA ? 'A' : 'B'} • ${this.linksFrom?.length || 0} interactions
            </div>
          </div>
        `
      },
      pointFormatter: function() {
        const persistencePercent = Math.round(this.consistency * 100)
        const typesList = this.typesArray || []
        const typePersistence = this.typePersistence || {}
        const dominantType = this.dominantType || typesList[0] || null
        const sortedTypes = dominantType
          ? [dominantType, ...typesList.filter(type => type !== dominantType)]
          : typesList
        
        const frames = Array.isArray(this.frames) ? this.frames : []
        const totalFrames = dataStore.totalFrames
        
        // Create frame visualization
        const frameLineWidth = 280
        const frameLineHeight = 10
        const frameSet = new Set(frames)
        
        const gradientStops = []
        for (let i = 1; i <= totalFrames; i++) {
          const position = ((i - 1) / totalFrames) * 100
          const hasInteraction = frameSet.has(i)
          const color = hasInteraction ? '#42A5F5' : '#e8e8ed'
          gradientStops.push(`${color} ${position}%`)
          gradientStops.push(`${color} ${(i / totalFrames) * 100}%`)
        }
        
        const frameLineStyle = `width: ${frameLineWidth}px; height: ${frameLineHeight}px; background: linear-gradient(to right, ${gradientStops.join(', ')}); border-radius: 2px;`
        
        const typesHtml = sortedTypes.map(type => {
          const typePersist = typePersistence[type] !== undefined 
            ? typePersistence[type] 
            : this.consistency
          const typePercent = Math.round(typePersist * 100)
          return `<div style="margin-bottom: 3px;">
            <span style="color: #1d1d1f; font-weight: 500;">${type}:</span>
            <span style="color: #6e6e73; margin-left: 6px;">${typePercent}%</span>
          </div>`
        }).join('')
        
        return `
          <div style="padding: 10px;">
            <div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">
              ${this.from} → ${this.to}
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Overall Conservation: ${persistencePercent}%</span>
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #6e6e73;">Frames: ${this.weight} / ${totalFrames}</span>
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
    }
  }

  const systemName = dataStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `sankey-diagram-${systemName}`)
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
  if (dataStore.currentChartType === 'sankey') {
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
