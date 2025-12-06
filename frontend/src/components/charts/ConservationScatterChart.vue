<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="slider-group">
        <label for="conservation-slider" class="slider-label">
          Minimum Conservation Threshold
        </label>
        <div class="slider-container">
          <div class="slider-control">
            <input
              id="conservation-slider"
              type="range"
              min="0.5"
              max="1.0"
              step="0.05"
              :value="minConservationThreshold"
              @input="updateThreshold"
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
              :value="Math.round(minConservationThreshold * 100)"
              @input="updateThresholdFromInput"
              @blur="validateThresholdInput"
              min="50"
              max="100"
              step="1"
              class="value-input"
            />
            <span class="percent-symbol">%</span>
          </div>
        </div>
      </div>
      <div class="info-notice">
        <strong>2D Conservation Plot:</strong> Lines show interaction type counts at different CA thresholds. Each line represents a specific CR level. Use the global interaction type filter in the sidebar to filter types.
      </div>
    </div>
    
    <div ref="chartContainer" class="chart-container"></div>
    
    <!-- Statistics Summary -->
    <div v-if="statistics" class="statistics-section">
      <h3 class="statistics-title">Conservation Distribution Summary</h3>
      <p class="statistics-description">
        Counts represent how many interaction type instances meet both CA (X-axis) and CR thresholds
      </p>
      <div class="statistics-grid">
        <div class="stat-card">
          <div class="stat-label">Total Interaction Type Instances</div>
          <div class="stat-value">{{ statistics.totalPoints }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Unique Interaction Types</div>
          <div class="stat-value">{{ statistics.uniqueTypes }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">At ≥{{ Math.round(minConservationThreshold * 100) }}% CA & CR</div>
          <div class="stat-value">{{ statistics.totalAtMinThreshold }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Maximum Count</div>
          <div class="stat-value">{{ statistics.maxCount }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import Highcharts from 'highcharts'
import { useDataStore } from '../../stores/dataStore'
import { getInteractionBaseColor, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
const minConservationThreshold = ref(0.5) // Default 50%
const statistics = ref(null)

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

const updateThreshold = (event) => {
  minConservationThreshold.value = parseFloat(event.target.value)
  updateChart()
}

const updateThresholdFromInput = (event) => {
  const value = parseInt(event.target.value)
  if (!isNaN(value)) {
    minConservationThreshold.value = Math.max(0.5, Math.min(1.0, value / 100))
    updateChart()
  }
}

const validateThresholdInput = (event) => {
  const value = parseInt(event.target.value)
  if (isNaN(value) || value < 50 || value > 100) {
    event.target.value = Math.round(minConservationThreshold.value * 100)
  }
}

const formatPercent = (value) => {
  if (value === undefined || value === null) return 'N/A'
  return `${(value * 100).toFixed(1)}%`
}

const updateChart = () => {
  if (!chartContainer.value) return

  const allInteractions = dataStore.filteredInteractions

  if (allInteractions.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    statistics.value = null
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try adjusting the threshold or interaction type filters.</div>'
    return
  }

  // Collect all interaction type instances with their conservation values
  const allDataPoints = []
  
  allInteractions.forEach(interaction => {
    const pairConsistency = interaction.consistency // CR (residue level)
    const typePersistence = interaction.typePersistence || {}
    
    if (interaction.typesArray && Array.isArray(interaction.typesArray)) {
      interaction.typesArray.forEach(type => {
        const typeConservation = typePersistence[type] || 0 // CA (atomic level)
        
        // Check if type matches selected interaction types filter
        if (dataStore.selectedInteractionTypes.size > 0) {
          if (!matchesSelectedTypes(type, dataStore.selectedInteractionTypes, INTERACTION_TYPES)) {
            return
          }
        }
        
        allDataPoints.push({
          type: type,
          ca: typeConservation,
          cr: pairConsistency,
          pair: `${interaction.id1} ↔ ${interaction.id2}`,
          color: getInteractionBaseColor(type)
        })
      })
    }
  })

  if (allDataPoints.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    statistics.value = null
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No interactions found. Try adjusting the threshold or interaction type filters.</div>'
    return
  }

  // Define threshold levels from 50% to 100% in 5% increments
  const thresholds = []
  for (let i = 0.50; i <= 1.0; i += 0.05) {
    thresholds.push(parseFloat(i.toFixed(2)))
  }

  // Calculate counts for each interaction type at different CR and CA threshold combinations
  // We'll create one series per (interaction type, CR level) combination
  const seriesData = []
  
  // Get unique interaction types
  const uniqueTypes = new Set(allDataPoints.map(p => p.type))
  
  uniqueTypes.forEach(type => {
    const typePoints = allDataPoints.filter(p => p.type === type)
    
    // For each CR threshold level, create a line showing how count decreases with CA threshold
    thresholds.forEach(crThreshold => {
      const lineData = []
      
      // For each CA threshold, count instances that meet both CR and CA thresholds
      thresholds.forEach(caThreshold => {
        const count = typePoints.filter(p => 
          p.ca >= caThreshold && p.cr >= crThreshold
        ).length
        
        if (count > 0) {
          lineData.push({
            x: caThreshold * 100,  // CA threshold as percentage
            y: count,              // Count of instances
            crThreshold: crThreshold * 100
          })
        }
      })
      
      if (lineData.length > 0) {
        seriesData.push({
          type: type,
          crLevel: crThreshold,
          data: lineData
        })
      }
    })
  })

  if (seriesData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    statistics.value = null
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No data to display.</div>'
    return
  }

  // Calculate statistics
  const totalAtMinThreshold = allDataPoints.filter(p => 
    p.ca >= minConservationThreshold.value && p.cr >= minConservationThreshold.value
  ).length
  
  const maxCount = Math.max(...seriesData.flatMap(s => s.data.map(p => p.y)))
  const uniqueTypesCount = new Set(seriesData.map(s => s.type)).size
  
  statistics.value = {
    totalPoints: allDataPoints.length,
    uniqueTypes: uniqueTypesCount,
    totalAtMinThreshold: totalAtMinThreshold,
    maxCount: maxCount
  }

  // Create series array - one series per (interaction type, CR level) combination
  const series = []
  
  seriesData.forEach(seriesItem => {
    const baseColor = getInteractionBaseColor(seriesItem.type)
    const crPercent = Math.round(seriesItem.crLevel * 100)
    
    series.push({
      type: 'area',
      name: `${seriesItem.type} (CR${crPercent})`,
      data: seriesItem.data.map(point => [point.x, point.y]),
      color: baseColor,
      fillOpacity: 0.2,
      lineWidth: 2,
      marker: {
        enabled: true,
        radius: 3,
        symbol: 'circle'
      },
      tooltip: {
        headerFormat: '<div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">{series.name}</div>',
        pointFormat: `
          <div style="padding: 4px 0;">
            <strong>Count:</strong> {point.y}<br/>
            <strong>CA Threshold:</strong> ≥{point.x:.0f}%
          </div>
        `
      }
    })
  })

  // Create or update chart
  const chartOptions = {
    chart: {
      type: 'area',
      zoomType: 'xy',
      backgroundColor: 'transparent',
      style: {
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      },
      height: 700
    },
    title: {
      text: '2D Conservation Area Plot',
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: 'Count of interaction types at different CA thresholds (lines show different CR levels)',
      style: {
        fontSize: '15px',
        color: '#6e6e73'
      }
    },
    xAxis: {
      title: {
        text: 'Type Conservation Threshold - CA (%)',
        style: {
          fontSize: '14px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: 50,
      max: 100,
      gridLineWidth: 1,
      gridLineColor: '#e8e8ed',
      lineColor: '#d2d2d7',
      tickColor: '#d2d2d7',
      labels: {
        style: {
          fontSize: '13px',
          color: '#6e6e73'
        },
        format: '{value}%'
      }
    },
    yAxis: {
      title: {
        text: 'Count of Interaction Type Instances',
        style: {
          fontSize: '14px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: 0,
      gridLineWidth: 1,
      gridLineColor: '#e8e8ed',
      lineColor: '#d2d2d7',
      tickColor: '#d2d2d7',
      labels: {
        style: {
          fontSize: '13px',
          color: '#6e6e73'
        }
      }
    },
    legend: {
      enabled: true,
      align: 'right',
      verticalAlign: 'middle',
      layout: 'vertical',
      itemStyle: {
        fontSize: '13px',
        fontWeight: '400',
        color: '#1d1d1f'
      },
      itemHoverStyle: {
        color: '#0066cc'
      },
      maxHeight: 600
    },
    plotOptions: {
      area: {
        stacking: undefined,
        lineWidth: 2,
        marker: {
          enabled: true,
          states: {
            hover: {
              enabled: true,
              lineColor: '#1d1d1f',
              lineWidth: 2,
              radius: 6
            }
          }
        },
        states: {
          hover: {
            enabled: true,
            lineWidthPlus: 1
          }
        }
      },
      series: {
        animation: {
          duration: 750
        },
        connectNulls: false
      }
    },
    tooltip: {
      useHTML: true,
      backgroundColor: '#ffffff',
      borderColor: '#e8e8ed',
      borderRadius: 12,
      borderWidth: 1,
      shadow: {
        color: 'rgba(0, 0, 0, 0.08)',
        offsetX: 0,
        offsetY: 2,
        opacity: 1,
        width: 8
      },
      style: {
        fontSize: '13px',
        color: '#1d1d1f'
      },
      padding: 12
    },
    credits: {
      enabled: false
    },
    series: series
  }

  if (chart) {
    chart.destroy()
  }
  chart = Highcharts.chart(chartContainer.value, chartOptions)
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentChartType,
  () => dataStore.currentThreshold,
  () => dataStore.filteredInteractions,
  () => dataStore.selectedInteractionTypes
], () => {
  if (dataStore.currentChartType === 'conservationScatter') {
    updateChart()
  }
})
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
}

.chart-toolbar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
  padding: 20px;
  background: #f5f5f7;
  border-radius: 12px;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slider-label {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-control {
  flex: 1;
  position: relative;
}

input[type="range"] {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #d2d2d7;
  outline: none;
  -webkit-appearance: none;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  transition: transform 0.2s ease;
}

input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

input[type="range"]::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  border: none;
  transition: transform 0.2s ease;
}

input[type="range"]::-moz-range-thumb:hover {
  transform: scale(1.2);
}

.slider-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  padding: 0 10px;
}

.slider-tick {
  flex: 1;
  display: flex;
  justify-content: center;
}

.slider-tick-label {
  font-size: 12px;
  color: #86868b;
  font-weight: 500;
}

.slider-value-input {
  display: flex;
  align-items: center;
  gap: 4px;
  background: white;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 4px 12px;
}

.value-input {
  width: 50px;
  border: none;
  outline: none;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  text-align: right;
}

.percent-symbol {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.info-notice {
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  font-size: 14px;
  color: #6e6e73;
  border-left: 3px solid #0066cc;
}

.info-notice strong {
  color: #1d1d1f;
}

.chart-container {
  min-height: 700px;
  width: 100%;
}

.statistics-section {
  margin-top: 32px;
  padding: 24px;
  background: #f5f5f7;
  border-radius: 12px;
}

.statistics-title {
  font-size: 21px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.statistics-description {
  font-size: 14px;
  color: #6e6e73;
  margin: 0 0 20px 0;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.stat-label {
  font-size: 13px;
  color: #6e6e73;
  margin-bottom: 8px;
  font-weight: 500;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
}
</style>

