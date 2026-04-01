<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
    <div class="chart-toolbar">
      <div class="slider-group">
        <label for="type-conservation-slider" class="slider-label">
          Interaction Type Conservation Threshold
          <span class="info-icon" @mouseenter="showTooltip($event, 'Filter interaction types by their conservation across frames. Only types present in at least this percentage of frames will be shown.')" @mouseleave="hideTooltip">ⓘ</span>
        </label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="type-conservation-slider"
              type="range"
              min="0.5"
              max="1.0"
              step="0.1"
              :value="dataStore.typeConservationThreshold"
              @input="updateTypeThreshold"
            />
            <div class="slider-ticks">
              <span
                v-for="tick in conservationTicks"
                :key="tick.value"
                class="slider-tick"
              >
                <span class="slider-tick-label">{{ tick.label }}</span>
              </span>
            </div>
          </div>
          <div class="slider-value-input">
            <input
              type="number"
              :value="Math.round(dataStore.typeConservationThreshold * 100)"
              @input="updateTypeThresholdFromInput"
              @blur="validateTypeThresholdInput"
              min="50"
              max="100"
              step="1"
              class="value-input"
            />
            <span class="percent-symbol">%</span>
          </div>
        </div>
        <p class="slider-description">Show types present in at least {{ Math.round(dataStore.typeConservationThreshold * 100) }}% of frames</p>
      </div>
    </div>

    <Teleport to="body">
      <div 
        v-if="activeTooltip.visible" 
        class="global-tooltip"
        :style="{ top: activeTooltip.y + 'px', left: activeTooltip.x + 'px' }"
      >
        {{ activeTooltip.text }}
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import { useDataStore } from '../../stores/dataStore'
import { INTERACTION_TYPES } from '../../utils/constants'
import { getInteractionBaseColor } from '../../utils/chartHelpers'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
let lastHoveredSeriesName = null

const activeTooltip = ref({
  visible: false,
  text: '',
  x: 0,
  y: 0
})

const showTooltip = (event, text) => {
  const x = event.clientX + 12
  const y = event.clientY - 8
  activeTooltip.value = {
    visible: true,
    text: text,
    x: Math.min(x, window.innerWidth - 340),
    y: y
  }
}

const hideTooltip = () => {
  activeTooltip.value.visible = false
}

const conservationTicks = computed(() => {
  const ticks = []
  for (let value = 0.5; value <= 1.0 + 0.0001; value += 0.1) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

const updateTypeThreshold = (event) => {
  dataStore.setTypeConservationThreshold(parseFloat(event.target.value))
  updateChart()
}

const updateTypeThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 50 && value <= 100) {
    dataStore.setTypeConservationThreshold(value / 100)
    updateChart()
  }
}

const validateTypeThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = Math.round(dataStore.typeConservationThreshold * 100)
    return
  }
  value = Math.max(50, Math.min(100, value))
  event.target.value = value
  dataStore.setTypeConservationThreshold(value / 100)
  updateChart()
}

const buildSeries = (frameCount) => {
  const useLogScale = dataStore.useLogScale
  const typeThreshold = dataStore.typeConservationThreshold
  
  const series = INTERACTION_TYPES.map((type) => {
    const trendKey = type.trendLabel || type.label
    const trendData = dataStore.trends?.[trendKey]
    const hasTrendData = Array.isArray(trendData) && trendData.length > 0
    const hasNonZero = hasTrendData ? trendData.some(value => value > 0) : false

    // Apply type conservation threshold: only show types present in >= N% of frames
    let meetsThreshold = hasNonZero
    if (hasNonZero && frameCount > 0) {
      const nonZeroCount = trendData.filter(value => value > 0).length
      const presence = nonZeroCount / frameCount
      meetsThreshold = presence >= typeThreshold
    }

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
      data: meetsThreshold ? paddedData : [],
      color: baseColor,
      lineWidth: 2,
      marker: {
        enabled: meetsThreshold,
        radius: 2.5,
        lineWidth: 1,
        lineColor: '#ffffff'
      },
      enableMouseTracking: meetsThreshold,
      showInLegend: true,
      _hasData: meetsThreshold,
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
      text: `${dataStore.currentSystem?.name || 'System'} - Interaction Type Trends Across Frames`,
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
  () => dataStore.timeUnit,
  () => dataStore.typeConservationThreshold
], () => {
  if (dataStore.currentChartType === 'line') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
  height: 100%;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.chart-toolbar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 32px 0;
  margin-top: 8px;
  border-top: 1px solid #e8e8ed;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slider-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 0;
  letter-spacing: -0.022em;
}

.slider-label .info-icon {
  font-size: 14px;
  color: #8e8e93;
  cursor: pointer;
  transition: color 0.15s ease;
}

.slider-label .info-icon:hover {
  color: #3B6EF5;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-control {
  position: relative;
  flex: 1;
}

.slider-ticks {
  position: absolute;
  left: 14px;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}

.slider-tick {
  position: relative;
  width: 2px;
  height: 16px;
  background: #b4b4bb;
  opacity: 0.7;
}

.slider-tick-label {
  position: absolute;
  top: -24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 600;
  color: #6e6e73;
}

input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  position: relative;
  z-index: 2;
  width: 100%;
  height: 4px;
  border-radius: 3px;
  background: #d2d2d7;
  outline: none;
  flex: 1;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.15s ease;
}

input[type="range"]::-webkit-slider-thumb:hover {
  background: #000000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
  transform: scale(1.05);
}

input[type="range"]::-moz-range-thumb {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.15s ease;
}

input[type="range"]::-moz-range-thumb:hover {
  background: #000000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
  transform: scale(1.05);
}

.slider-value-input {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 80px;
}

.value-input {
  width: 60px;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  text-align: right;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  padding: 6px 8px;
  background: #ffffff;
  font-variant-numeric: tabular-nums;
  transition: all 0.15s ease;
  font-family: inherit;
}

.value-input:focus {
  outline: none;
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, 0.1);
}

.value-input::-webkit-inner-spin-button,
.value-input::-webkit-outer-spin-button {
  opacity: 1;
  cursor: pointer;
}

.percent-symbol {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.slider-description {
  margin: 0;
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
  font-style: italic;
}

.global-tooltip {
  position: fixed;
  padding: 10px 14px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  white-space: normal;
  max-width: 320px;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  z-index: 100000;
  pointer-events: none;
  text-align: left;
  animation: tooltipFadeIn 0.15s ease;
}

@keyframes tooltipFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

