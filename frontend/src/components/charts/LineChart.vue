<template>
  <div ref="chartContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from 'highcharts'
import { useDataStore } from '../../stores/dataStore'
import { INTERACTION_TYPES } from '../../utils/constants'
import { getInteractionBaseColor } from '../../utils/chartHelpers'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
let lastHoveredSeriesName = null

const buildSeries = (frameCount) => {
  const series = INTERACTION_TYPES.map((type) => {
    const trendKey = type.trendLabel || type.label
    const trendData = dataStore.trends?.[trendKey]
    const hasTrendData = Array.isArray(trendData) && trendData.length > 0
    const hasNonZero = hasTrendData ? trendData.some(value => value > 0) : false

    const paddedData = hasTrendData
      ? trendData.concat(Array(Math.max(0, frameCount - trendData.length)).fill(0))
      : Array(frameCount).fill(null)

    return {
      name: type.label,
      data: paddedData,
      color: hasNonZero ? getInteractionBaseColor(type.label) : '#c7c7cc',
      lineWidth: hasNonZero ? 3 : 2,
      dashStyle: hasNonZero ? 'Solid' : 'ShortDot',
      marker: {
        radius: hasNonZero ? 5 : 3,
        lineWidth: hasNonZero ? 2 : 1,
        lineColor: hasNonZero ? '#ffffff' : '#dcdce0'
      },
      enableMouseTracking: hasNonZero,
      point: {
        events: {
          mouseOver: function() {
            lastHoveredSeriesName = this.series.name
          }
        }
      }
    }
  })

  return series.sort((a, b) => {
    const aActive = a.data.some(value => value && value > 0)
    const bActive = b.data.some(value => value && value > 0)
    if (aActive === bActive) return 0
    return aActive ? -1 : 1
  })
}

const updateChart = () => {
  if (!chartContainer.value) return

  const trendValues = Object.values(dataStore.trends || {})
  const maxTrendLength = trendValues.reduce((max, series) => {
    if (Array.isArray(series)) {
      return Math.max(max, series.length)
    }
    return max
  }, 0)
  const frameCount = Math.max(dataStore.totalFrames || 0, maxTrendLength)
  if (frameCount === 0) return

  const categories = Array.from({ length: frameCount }, (_, i) => `Frame ${i + 1}`)
  const series = buildSeries(frameCount)

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
  () => dataStore.useLogScale,
  () => dataStore.totalFrames
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

