<template>
  <div ref="chartContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from 'highcharts'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor } from '../../utils/chartHelpers'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
let lastHoveredSeriesName = null

const updateChart = () => {
  if (!chartContainer.value || !dataStore.trends || Object.keys(dataStore.trends).length === 0) return

  const categories = Array.from({ length: dataStore.totalFrames }, (_, i) => `Frame ${i + 1}`)
  const series = []
  for (const [type, data] of Object.entries(dataStore.trends)) {
    const hasNonZero = data.some(value => value > 0)
    if (hasNonZero) {
      const baseColor = getInteractionBaseColor(type)
      series.push({
        name: type,
        data: data,
        color: baseColor,
        lineWidth: 3,
        marker: {
          radius: 5,
          lineWidth: 2,
          lineColor: '#ffffff'
        },
        point: {
          events: {
            mouseOver: function() {
              lastHoveredSeriesName = this.series.name
            }
          }
        }
      })
    }
  }

  if (chart) {
    chart.destroy()
  }

  chart = Highcharts.chart(chartContainer.value, {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      height: 650
    },
    title: {
      text: 'Interaction Type Trends Across Frames',
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: `Number of Interactions vs Time${dataStore.useLogScale ? ' - Logarithmic Scale' : ''}`,
      style: {
        fontSize: '17px',
        color: '#6e6e73'
      }
    },
    credits: {
      enabled: false
    },
    xAxis: {
      categories: categories,
      title: {
        text: 'Time (Frames)',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      }
    },
    yAxis: {
      type: dataStore.useLogScale ? 'logarithmic' : 'linear',
      title: {
        text: `Number of Interactions${dataStore.useLogScale ? ' - Log Scale' : ''}`,
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      },
      min: dataStore.useLogScale ? 0.1 : 0
    },
    legend: {
      align: 'right',
      verticalAlign: 'middle',
      layout: 'vertical',
      itemStyle: {
        fontSize: '13px',
        fontWeight: '500',
        color: '#1d1d1f'
      }
    },
    plotOptions: {
      line: {
        lineWidth: 3,
        states: {
          hover: {
            lineWidth: 4
          }
        },
        marker: {
          enabled: true
        }
      }
    },
    series: series,
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      shared: true,
      useHTML: true,
      formatter: function() {
        let html = `<div style="padding: 10px;">`
        html += `<div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">${this.x}</div>`
        
        const hoveredPoint = this.points.find(point => point.series.name === lastHoveredSeriesName)
        const otherPoints = this.points
          .filter(point => point !== hoveredPoint)
          .sort((a, b) => b.y - a.y)

        const sortedPoints = hoveredPoint
          ? [hoveredPoint, ...otherPoints]
          : otherPoints

        sortedPoints.forEach(point => {
          if (point.y > 0) {
            html += `
              <div style="margin-bottom: 4px;">
                <span style="color: ${point.color}; font-weight: 600;">●</span>
                <span style="color: #1d1d1f;">${point.series.name}: </span>
                <span style="color: #1d1d1f; font-weight: 600;">${point.y}</span>
              </div>
            `
          }
        })
        html += '</div>'
        return html
      }
    }
  })
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.trends,
  () => dataStore.useLogScale
], () => {
  if (dataStore.currentChartType === 'line') {
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

