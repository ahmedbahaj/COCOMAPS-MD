<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="toggle-group">
        <span>Mean ± Std Dev</span>
        <label class="switch">
          <input type="checkbox" v-model="showStats">
          <span class="slider"></span>
        </label>
      </div>
      <div class="toggle-group">
        <span>Show Percentages</span>
        <label class="switch">
          <input type="checkbox" v-model="showPercentages">
          <span class="slider"></span>
        </label>
      </div>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import HighchartsMore from 'highcharts/highcharts-more'
import { useDataStore } from '../../stores/dataStore'

HighchartsMore(Highcharts)

const showStats = ref(true)
const showPercentages = ref(false)
const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
let hasAnimated = false

const PERCENT_FIELD_MAP = {
  'Total BSA': 'totalPercent',
  'Total POLAR Buried Area': 'polarPercent',
  'Total NON POLAR Buried Area': 'nonPolarPercent'
}

const calculateStats = (data) => {
  if (!data.length) {
    return { mean: 0, stdDev: 0, lower: 0, upper: 0 }
  }
  const mean = data.reduce((sum, value) => sum + value, 0) / data.length
  const variance = data.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / data.length
  const stdDev = Math.sqrt(variance)
  return {
    mean,
    stdDev,
    lower: Math.max(0, mean - stdDev),
    upper: mean + stdDev
  }
}

const updateChart = () => {
  if (!chartContainer.value) return

  if (!dataStore.areaData || dataStore.areaData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No area data available for this system.</div>'
    return
  }

  const sortedAreaData = [...dataStore.areaData].sort((a, b) => a.frame - b.frame) //prevents lexicographic order

  const categories = sortedAreaData.map(d => `${d.frame}`)
  const totalBSAData = sortedAreaData.map(d => d.totalBSA)
  const polarBSAData = sortedAreaData.map(d => d.polarBSA)
  const nonPolarBSAData = sortedAreaData.map(d => d.nonPolarBSA)

  if (chart) {
    chart.destroy()
  }

  const totalStats = calculateStats(totalBSAData)
  const polarStats = calculateStats(polarBSAData)
  const nonPolarStats = calculateStats(nonPolarBSAData)

  const buildRangeSeries = (id, color, stats, baseData) => {
    if (!stats.stdDev || stats.stdDev === 0) return null
    const areaData = baseData.map((_, index) => [index, stats.lower, stats.upper])
    return {
      type: 'arearange',
      linkedTo: id,
      data: areaData,
      color,
      fillOpacity: 0.12,
      lineWidth: 0,
      enableMouseTracking: false,
      showInLegend: false,
      zIndex: 0,
      marker: {
        enabled: false
      }
    }
  }

  const chartOptions = {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      height: 650
    },
    title: {
      text: 'Total Buried Surface Area Across Frames',
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: 'Total, POLAR, and NON POLAR Buried Surface Area (Å²)',
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
      title: {
        text: 'Total Buried Surface Area (Å²)',
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
    legend: {
      align: 'center',
      verticalAlign: 'top',
      layout: 'horizontal',
      itemStyle: {
        fontSize: '14px',
        fontWeight: '500',
        color: '#1d1d1f'
      }
    },
    plotOptions: {
      line: {
        animation: hasAnimated ? false : { duration: 800 },
        lineWidth: 2,
        marker: {
          enabled: true,
          radius: 3,
          lineWidth: 1,
          lineColor: '#ffffff'
        },
        states: {
          hover: {
            lineWidth: 3
          }
        }
      }
    },
    series: [{
      id: 'total-bsa-line',
      name: 'Total BSA',
      data: totalBSAData,
      color: '#3B6EF5',
      dashStyle: 'Solid',
      zIndex: 2,
      marker: {
        symbol: 'circle'
      }
    }, {
      id: 'polar-bsa-line',
      name: 'Total POLAR Buried Area',
      data: polarBSAData,
      color: '#FF3B30',
      dashStyle: 'Dash',
      zIndex: 2,
      marker: {
        symbol: 'square'
      }
    }, {
      id: 'nonpolar-bsa-line',
      name: 'Total NON POLAR Buried Area',
      data: nonPolarBSAData,
      color: '#34C759',
      dashStyle: 'Dot',
      zIndex: 2,
      marker: {
        symbol: 'triangle'
      }
    }].concat(
      showStats.value
        ? [buildRangeSeries('total-bsa-line', '#3B6EF5', totalStats, totalBSAData),
           buildRangeSeries('polar-bsa-line', '#FF3B30', polarStats, polarBSAData),
           buildRangeSeries('nonpolar-bsa-line', '#34C759', nonPolarStats, nonPolarBSAData)
          ].filter(Boolean)
        : []
    ),
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
        
        const sortedPoints = [...this.points].sort((a, b) => b.y - a.y)
        sortedPoints.forEach(point => {
          const frameIndex = point.point?.index ?? 0
          const frameData = sortedAreaData[frameIndex]
          const percentField = PERCENT_FIELD_MAP[point.series.name]
          const percentValue = showPercentages.value && frameData && percentField ? frameData[percentField] : null
          const percentText = percentValue !== null && percentValue !== undefined
            ? ` (${percentValue.toFixed(2)}%)`
            : ''

          html += `
            <div style="margin-bottom: 4px;">
              <span style="color: ${point.color}; font-weight: 600;">●</span>
              <span style="color: #1d1d1f;">${point.series.name}: </span>
              <span style="color: #1d1d1f; font-weight: 600;">${point.y.toFixed(2)} Å²${percentText}</span>
            </div>
          `
        })
        html += '</div>'
        return html
      }
    }
  }

  const systemName = dataStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `buried-surface-area-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
  hasAnimated = true
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.areaData.length,
  () => showStats.value,
  () => showPercentages.value,
  () => dataStore.timeUnit
], () => {
  if (dataStore.currentChartType === 'area') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  display: flex;
  flex-direction: column;
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

.chart-container {
  flex: 1;
  width: 100%;
  height: calc(100% - 40px);
}
</style>

