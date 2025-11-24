<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-surface"></div>
    <InteractionLegend title="Interaction Color Legend" />
    <AtomPairExplorer 
      :visible="showAtomExplorer" 
      :residue-pair="selectedResiduePair"
      @close="closeAtomExplorer"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from 'highcharts'
import DependencyWheelModule from 'highcharts/modules/dependency-wheel'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionColor } from '../../utils/chartHelpers'
import InteractionLegend from '../InteractionLegend.vue'
import AtomPairExplorer from '../AtomPairExplorer.vue'

DependencyWheelModule(Highcharts)

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

  const nodes = new Map()
  const links = filteredData.map(interaction => {
    const frames = Array.isArray(interaction.frames) ? interaction.frames : []
    const typePersistence = interaction.typePersistence || {}
    const typesArray = interaction.typesArray || []
    const dominantType = getDominantType(typesArray, typePersistence, interaction.consistency)

    if (!nodes.has(interaction.id1)) {
      nodes.set(interaction.id1, {
        id: interaction.id1,
        name: interaction.id1,
        color: '#3B6EF5',
        marker: {
          radius: 8,
          symbol: 'circle',
          fillColor: '#3B6EF5',
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
    }
    if (!nodes.has(interaction.id2)) {
      nodes.set(interaction.id2, {
        id: interaction.id2,
        name: interaction.id2,
        color: '#FF8A4C',
        marker: {
          radius: 8,
          symbol: 'circle',
          fillColor: '#FF8A4C',
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
    }

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

  const nodesArray = Array.from(nodes.values()).sort((a, b) => {
    if (a.id.startsWith('A-') && !b.id.startsWith('A-')) return -1
    if (!a.id.startsWith('A-') && b.id.startsWith('A-')) return 1
    const numA = parseInt(a.id.match(/\d+/)?.[0] || '0')
    const numB = parseInt(b.id.match(/\d+/)?.[0] || '0')
    return numA - numB
  })

  if (chart) {
    chart.destroy()
  }

  chart = Highcharts.chart(chartContainer.value, {
    chart: {
      type: 'dependencywheel',
      backgroundColor: 'transparent',
      height: 850,
      marginTop: 80
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
          
          // Use per-type persistence if available, otherwise fall back to overall consistency
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
                <span style="color: #1d1d1f; font-weight: 600;">Overall Consistency: ${persistencePercent}%</span>
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
  })
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

