<template>
  <div ref="chartContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from 'highcharts'
import ArcDiagramModule from 'highcharts/modules/arc-diagram'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionColor } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

ArcDiagramModule(Highcharts)

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null

const updateChart = () => {
  if (!chartContainer.value) return

  const filteredData = dataStore.filteredInteractions

  if (filteredData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    // Show empty state message
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try adjusting the threshold or interaction type filters.</div>'
    return
  }

  // Prepare data for arc diagram
  const nodes = new Set()
  const links = []

  filteredData.forEach(interaction => {
    nodes.add(interaction.id1)
    nodes.add(interaction.id2)

    // Ensure frames is an array - check both frames and fallback to empty array
    const frames = Array.isArray(interaction.frames) ? interaction.frames : []

    links.push({
      from: interaction.id1,
      to: interaction.id2,
      weight: interaction.frameCount,
      consistency: interaction.consistency,
      types: interaction.typesArray.join('; '),
      typesArray: interaction.typesArray,
      typePersistence: interaction.typePersistence || {},
      frames: frames
    })
  })

  // Create nodes array
  const nodesArray = Array.from(nodes).map(id => ({
    id: id,
    name: id,
    color: id.startsWith('A-') ? '#3B6EF5' : '#FF8A4C',
    dataLabels: {
      enabled: false
    }
  }))

  // Sort nodes
  nodesArray.sort((a, b) => {
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
      type: 'arcdiagram',
      backgroundColor: 'transparent',
      height: 850,
      marginBottom: 140,
      marginTop: 80
    },
    title: {
      text: `Residue Interaction Network (${filteredData.length} interactions)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Chain A (blue) ↔ Chain B (orange) | Threshold: ${Math.round(dataStore.currentThreshold * 100)}%`,
      style: {
        fontSize: '17px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    plotOptions: {
      arcdiagram: {
        linkWeight: 2,
        centeredLinks: true,
        reversed: false,
        marker: {
          fillOpacity: 1,
          lineWidth: 3,
          lineColor: '#ffffff',
          radius: 18,
          states: {
            hover: {
              radius: 22,
              lineWidth: 3
            }
          }
        },
        states: {
          hover: {
            linkOpacity: 1,
            opacity: 1
          }
        }
      }
    },
    series: [{
      keys: ['from', 'to', 'weight'],
      type: 'arcdiagram',
      name: 'Interactions',
      nodes: nodesArray,
      data: links.map(link => ({
        from: link.from,
        to: link.to,
        weight: link.weight,
        color: getInteractionColor(link.types, link.consistency),
        consistency: link.consistency,
        types: link.types,
        typesArray: link.typesArray,
        typePersistence: link.typePersistence,
        frames: link.frames
      })),
      linkOpacity: 0.75,
      offset: '100%',
      dataLabels: {
        enabled: false
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
          const typesHtml = typesList.map(type => {
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
  if (dataStore.currentChartType === 'arc') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
div {
  width: 100%;
  height: 100%;
}
</style>


