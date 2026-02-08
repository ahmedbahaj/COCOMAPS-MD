<template>
  <div ref="chartContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import { useDataStore } from '../../stores/dataStore'
import { INTERACTION_TYPES } from '../../utils/constants'
import { getInteractionBaseColor } from '../../utils/chartHelpers'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
let lastHoveredSeriesName = null

const buildSeries = (frameCount) => {
  const useLogScale = dataStore.useLogScale
  
  const series = INTERACTION_TYPES.map((type) => {
    const trendKey = type.trendLabel || type.label
    const trendData = dataStore.trends?.[trendKey]
    const hasTrendData = Array.isArray(trendData) && trendData.length > 0
    const hasNonZero = hasTrendData ? trendData.some(value => value > 0) : false

    // Build padded data - use null for missing/zero values when using log scale
    let paddedData
    if (hasTrendData) {
      const padding = Array(Math.max(0, frameCount - trendData.length)).fill(useLogScale ? null : 0)
      paddedData = trendData.concat(padding)
      
      // For log scale, convert zeros to null to avoid log(0) issues
      if (useLogScale) {
        paddedData = paddedData.map(value => value === 0 || value === null ? null : value)
      }
    } else {
      paddedData = Array(frameCount).fill(null)
    }

    const baseColor = getInteractionBaseColor(type.label)
    
    return {
      name: type.label,
      data: hasNonZero ? paddedData : [], // Empty data if no interactions
      color: baseColor, // Always use the real color for legend
      lineWidth: 2,
      marker: {
        enabled: hasNonZero,
        radius: 2.5,
        lineWidth: 1,
        lineColor: '#ffffff'
      },
      enableMouseTracking: hasNonZero,
      showInLegend: true,
      _hasData: hasNonZero,
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

  // Use actual frame numbers from backend if available
  const frameNumbers = dataStore.trendFrameNumbers || []
  const trendValues = Object.values(dataStore.trends || {})
  const maxTrendLength = trendValues.reduce((max, series) => {
    if (Array.isArray(series)) {
      return Math.max(max, series.length)
    }
    return max
  }, 0)
  
  // Determine frame count and categories
  let frameCount, categories
  if (frameNumbers.length > 0) {
    // Use actual frame numbers from backend
    frameCount = frameNumbers.length
    categories = frameNumbers.map(n => `${n}`)
  } else {
    // Fallback to sequential numbering
    frameCount = Math.max(dataStore.totalFrames || 0, maxTrendLength)
    categories = Array.from({ length: frameCount }, (_, i) => `${i + 1}`)
  }
  
  if (frameCount === 0) return

  const series = buildSeries(frameCount)

  if (chart) {
    chart.destroy()
  }

  const chartOptions = {
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
      text: null
    },
    credits: {
      enabled: false
    },
    xAxis: {
      categories: categories,
      title: {
        text: dataStore.timeUnit ? `Time (${dataStore.timeUnit})` : 'Frame',
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
      min: dataStore.useLogScale ? 0.1 : 0,
      // Ensure proper handling of small values in log scale
      allowDecimals: true
    },
    legend: {
      align: 'right',
      verticalAlign: 'middle',
      layout: 'vertical',
      useHTML: true,
      labelFormatter: function() {
        const hasData = this.options._hasData
        if (hasData) {
          return `<span style="font-weight: 700; font-size: 13px;">${this.name}</span>`
        } else {
          return `<span style="color: #9ca3af; font-weight: 400; font-size: 13px;">${this.name}</span>`
        }
      },
      itemStyle: {
        fontSize: '13px',
        fontWeight: '500',
        color: '#1d1d1f'
      }
    },
    plotOptions: {
      line: {
        lineWidth: 2,
        states: {
          hover: {
            lineWidth: 3
          }
        },
        marker: {
          enabled: true,
          radius: 2.5
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
  }

  const systemName = dataStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `interaction-trends-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.trends,
  () => dataStore.useLogScale,
  () => dataStore.totalFrames,
  () => dataStore.trendFrameNumbers,
  () => dataStore.timeUnit
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

