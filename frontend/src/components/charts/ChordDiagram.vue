<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-surface"></div>
    <InteractionLegend title="Interaction Color Legend" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from 'highcharts'
import DependencyWheelModule from 'highcharts/modules/dependency-wheel'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionColor } from '../../utils/chartHelpers'
import InteractionLegend from '../InteractionLegend.vue'

DependencyWheelModule(Highcharts)

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
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try adjusting the threshold or interaction type filters.</div>'
    return
  }

  const nodes = new Map()
  const links = filteredData.map(interaction => {
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
      color: getInteractionColor(interaction.typesArray.join('; '), interaction.consistency)
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
      tooltip: {
        pointFormatter: function() {
          return `
            <div style="padding: 10px;">
              <div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">
                ${this.from} ↔ ${this.to}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #1d1d1f; font-weight: 600;">Consistency: ${Math.round(this.consistency * 100)}%</span>
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #6e6e73;">Frames: ${this.weight} / ${dataStore.totalFrames}</span>
              </div>
              <div style="color: #6e6e73; font-size: 12px; margin-top: 6px; padding-top: 6px; border-top: 1px solid #e8e8ed;">
                ${this.types}
              </div>
            </div>
          `
        }
      }
    }]
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

