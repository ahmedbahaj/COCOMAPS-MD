<template>
  <div>
    <div class="chart-toolbar">
      <div class="toggle-group">
        <span>Show Residue Labels</span>
        <label class="switch">
          <input type="checkbox" v-model="showFullLabels">
          <span class="slider"></span>
        </label>
      </div>
    </div>
    <div ref="chartContainer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import HeatmapModule from 'highcharts/modules/heatmap'
import { useDataStore } from '../../stores/dataStore'
import { matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

HeatmapModule(Highcharts)

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
const showFullLabels = ref(true) // Default to showing full labels

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

  const chainAResidues = new Set()
  const chainBResidues = new Set()

  filteredData.forEach(interaction => {
    chainAResidues.add(interaction.id1)
    chainBResidues.add(interaction.id2)
  })

  const chainAArray = Array.from(chainAResidues).sort((a, b) => {
    const numA = parseInt(a.match(/\d+/)?.[0] || '0')
    const numB = parseInt(b.match(/\d+/)?.[0] || '0')
    return numA - numB
  })

  const chainBArray = Array.from(chainBResidues).sort((a, b) => {
    const numA = parseInt(a.match(/\d+/)?.[0] || '0')
    const numB = parseInt(b.match(/\d+/)?.[0] || '0')
    return numA - numB
  })

  // Use full residue labels or just numbers based on toggle
  const chainACategories = showFullLabels.value 
    ? chainAArray 
    : chainAArray.map(id => id.match(/\d+/)?.[0] || id)
  const chainBCategories = showFullLabels.value 
    ? chainBArray 
    : chainBArray.map(id => id.match(/\d+/)?.[0] || id)

  const heatmapData = []
  filteredData.forEach(interaction => {
    const xIndex = chainAArray.indexOf(interaction.id1)
    const yIndex = chainBArray.indexOf(interaction.id2)

    if (xIndex !== -1 && yIndex !== -1) {
      heatmapData.push({
        x: xIndex,
        y: yIndex,
        value: interaction.consistency,
        name: `${interaction.id1} ↔ ${interaction.id2}`,
        types: interaction.typesArray.join('; '),
        typesArray: interaction.typesArray,
        frameCount: interaction.frameCount,
        consistency: interaction.consistency,
        typePersistence: interaction.typePersistence || {}
      })
    }
  })

  if (chart) {
    chart.destroy()
  }

  const chartOptions = {
    chart: {
      type: 'heatmap',
      backgroundColor: 'transparent',
      height: 800
    },
    title: {
      text: `Residue Interaction Heatmap (${heatmapData.length} interactions)`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Chain A (X-axis) ↔ Chain B (Y-axis) | Threshold: ${Math.round(dataStore.currentThreshold * 100)}% | Color intensity = Conservation`,
      style: {
        fontSize: '17px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    xAxis: {
      categories: chainACategories,
      title: {
        text: 'Chain A Residues',
        style: {
          fontSize: '18px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        rotation: -45,
        style: {
          fontSize: '11px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      }
    },
    yAxis: {
      categories: chainBCategories,
      title: {
        text: 'Chain B Residues',
        style: {
          fontSize: '18px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '11px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      },
      reversed: true
    },
    colorAxis: {
      min: 0,
      max: 1,
      reversed: false,
      stops: [
        [0, '#f5f5f7'],
        [0.3, '#90CAF9'],
        [0.5, '#42A5F5'],
        [0.7, '#1E88E5'],
        [1, '#0D47A1']
      ],
      labels: {
        formatter: function() {
          return Math.round(this.value * 100) + '%'
        },
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      }
    },
    legend: {
      align: 'right',
      layout: 'vertical',
      verticalAlign: 'middle',
      symbolHeight: 300,
      symbolWidth: 20,
      reversed: false,
      title: {
        text: 'Conservation',
        style: {
          fontSize: '14px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      }
    },
    series: [{
      name: 'Interaction Conservation',
      data: heatmapData,
      turboThreshold: 10000
    }],
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      formatter: function() {
        const persistencePercent = Math.round(this.point.consistency * 100)
        const typesList = this.point.typesArray || []
        const typePersistence = this.point.typePersistence || {}
        
        // Use per-type persistence if available, otherwise fall back to overall conservation
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
              ${this.point.name}
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #1d1d1f; font-weight: 600;">Overall Conservation: ${persistencePercent}%</span>
            </div>
            <div style="margin-bottom: 4px;">
              <span style="color: #6e6e73;">Frames: ${this.point.frameCount} / ${dataStore.totalFrames}</span>
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
    }
  }

  const systemName = dataStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `filtered-heatmap-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.currentThreshold,
  () => dataStore.filteredInteractions.length,
  () => dataStore.selectedInteractionTypes.size,
  () => showFullLabels.value
], () => {
  if (dataStore.currentChartType === 'filteredHeatmap') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
div {
  width: 100%;
  height: 100%;
}

.chart-toolbar {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 4px 0;
  gap: 12px;
}

.toggle-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 200px;
  font-size: 16px;
  font-weight: 500;
  color: #1d1d1f;
}

.switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 22px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #d2d2d7;
  transition: .2s;
  border-radius: 22px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .2s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

input:checked + .slider {
  background-color: #3B6EF5;
}

input:checked + .slider:before {
  transform: translateX(20px);
}
</style>

