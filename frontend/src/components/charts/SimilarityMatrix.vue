<template>
  <div ref="chartContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import Highcharts from 'highcharts'
import HeatmapModule from 'highcharts/modules/heatmap'
import { useDataStore } from '../../stores/dataStore'
import api from '../../services/api'

HeatmapModule(Highcharts)

const dataStore = useDataStore()
const chartContainer = ref(null)
let chart = null
let similarityData = null
let loading = false

const updateChart = async () => {
  if (!chartContainer.value || !dataStore.currentSystem) return

  // Show loading state
  if (loading) return
  loading = true

  try {
    // Fetch similarity matrix from API
    const response = await api.getSimilarityMatrix(dataStore.currentSystem.id)
    similarityData = response

    if (!similarityData || !similarityData.matrix || similarityData.matrix.length === 0) {
      if (chart) {
        chart.destroy()
        chart = null
      }
      chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No similarity data available.</div>'
      return
    }

    const matrix = similarityData.matrix
    const totalFrames = similarityData.totalFrames
    const frameLabels = similarityData.frameLabels || Array.from({ length: totalFrames }, (_, i) => i + 1)

    // Convert matrix to heatmap data format
    const heatmapData = []
    for (let i = 0; i < matrix.length; i++) {
      for (let j = 0; j < matrix[i].length; j++) {
        heatmapData.push({
          x: j,
          y: i,
          value: matrix[i][j],
          frameI: frameLabels[i],
          frameJ: frameLabels[j]
        })
      }
    }

    // Find min and max for color scale
    const allValues = matrix.flat()
    const minValue = Math.min(...allValues)
    const maxValue = Math.max(...allValues)

    if (chart) {
      chart.destroy()
    }

    chart = Highcharts.chart(chartContainer.value, {
      chart: {
        type: 'heatmap',
        backgroundColor: 'transparent',
        height: 850,
        marginBottom: 100,
        marginTop: 80,
        marginLeft: 100
      },
      title: {
        text: `Conformational Similarity Matrix (${totalFrames} frames)`,
        style: {
          fontSize: '24px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      subtitle: {
        text: 'Tanimoto Similarity Coefficient | Red = High Similarity, Blue = Low Similarity',
        style: {
          fontSize: '17px',
          color: '#6e6e73'
        }
      },
      credits: {
        enabled: false
      },
      xAxis: {
        categories: frameLabels.map(f => String(f)),
        title: {
          text: 'Frame (j)',
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
        categories: frameLabels.map(f => String(f)),
        title: {
          text: 'Frame (i)',
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
        reversed: false
      },
      colorAxis: {
        min: minValue,
        max: maxValue,
        stops: [
          [0, '#000033'],      // Very dark blue (low similarity)
          [0.2, '#000066'],    // Dark blue
          [0.4, '#0033CC'],    // Blue
          [0.5, '#0066FF'],    // Light blue
          [0.6, '#3399FF'],    // Lighter blue
          [0.7, '#66CCFF'],   // Very light blue
          [0.8, '#FFCC99'],   // Light orange
          [0.9, '#FF9966'],   // Orange
          [1, '#FF3300']       // Red (high similarity)
        ],
        labels: {
          formatter: function() {
            return this.value.toFixed(2)
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
        symbolHeight: 400,
        symbolWidth: 20,
        title: {
          text: 'Tanimoto<br>Similarity',
          style: {
            fontSize: '14px',
            fontWeight: '600',
            color: '#1d1d1f'
          }
        }
      },
      series: [{
        name: 'Frame Similarity',
        data: heatmapData,
        turboThreshold: 10000,
        borderWidth: 0,
        nullColor: '#f5f5f7'
      }],
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#d2d2d7',
        useHTML: true,
        formatter: function() {
          const similarity = this.point.value
          const similarityPercent = (similarity * 100).toFixed(1)
          return `
            <div style="padding: 10px;">
              <div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">
                Frame ${this.point.frameI} ↔ Frame ${this.point.frameJ}
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #1d1d1f; font-weight: 600;">Tanimoto Similarity: ${similarity.toFixed(4)}</span>
              </div>
              <div style="margin-bottom: 4px;">
                <span style="color: #6e6e73;">Similarity: ${similarityPercent}%</span>
              </div>
              <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e8e8ed; color: #6e6e73; font-size: 12px;">
                ${similarity > 0.8 ? 'High similarity: Similar binding conformations' : 
                  similarity > 0.5 ? 'Moderate similarity: Related conformations' : 
                  'Low similarity: Different binding states'}
              </div>
            </div>
          `
        }
      }
    })
  } catch (error) {
    console.error('Error loading similarity matrix:', error)
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = `<div style="text-align: center; padding: 100px 20px; color: #ff3b30; font-size: 19px;">Error loading similarity matrix: ${error.message}</div>`
  } finally {
    loading = false
  }
}

onMounted(() => {
  updateChart()
})

watch([
  () => dataStore.currentSystem?.id,
  () => dataStore.currentChartType
], () => {
  if (dataStore.currentChartType === 'similarity') {
    updateChart()
  }
})

onBeforeUnmount(() => {
  if (chart) {
    chart.destroy()
    chart = null
  }
})
</script>

<style scoped>
div {
  width: 100%;
  height: 100%;
}
</style>

