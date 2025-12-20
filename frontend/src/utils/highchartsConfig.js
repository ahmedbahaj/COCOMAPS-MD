import Highcharts from 'highcharts'
import ExportingModule from 'highcharts/modules/exporting'
import OfflineExportingModule from 'highcharts/modules/offline-exporting'
import ExportDataModule from 'highcharts/modules/export-data'

// Initialize Highcharts modules
ExportingModule(Highcharts)
OfflineExportingModule(Highcharts)
ExportDataModule(Highcharts)

/**
 * Common exporting configuration for all Highcharts charts
 * This ensures proper rendering and functionality of export buttons
 */
export const exportingConfig = {
  exporting: {
    enabled: true,
    buttons: {
      contextButton: {
        menuItems: [
          'downloadPNG',
          'downloadJPEG',
          'downloadPDF',
          'downloadSVG',
          'separator',
          'downloadCSV',
          'downloadXLS'
        ],
        theme: {
          fill: '#ffffff',
          stroke: '#d2d2d7',
          r: 8,
          states: {
            hover: {
              fill: '#f5f5f7',
              stroke: '#6e6e73'
            },
            select: {
              fill: '#e8e8ed',
              stroke: '#1d1d1f'
            }
          }
        },
        symbolStroke: '#1d1d1f',
        symbolFill: '#1d1d1f'
      }
    },
    // Ensure proper rendering for exports
    chartOptions: {
      chart: {
        backgroundColor: '#ffffff'
      },
      plotOptions: {
        series: {
          dataLabels: {
            style: {
              textOutline: 'none'
            }
          }
        }
      }
    },
    // Use client-side export (offline-exporting module)
    fallbackToExportServer: false,
    // File naming
    filename: 'chart-export',
    // Scaling for better quality - increased for better resolution
    scale: 2,
    // Don't set fixed sourceWidth/sourceHeight - let Highcharts use actual chart dimensions
    // This prevents squashing of large charts with many data points
    sourceWidth: undefined,
    sourceHeight: undefined,
    // PDF options
    pdfFont: {
      normal: 'https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Me5Q.ttf',
      bold: 'https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmWUlvAw.ttf'
    }
  }
}

/**
 * Get exporting configuration with custom filename
 * @param {string} filename - Custom filename for the export
 * @returns {Object} Exporting configuration object
 */
export function getExportingConfig(filename = 'chart-export') {
  return {
    ...exportingConfig,
    exporting: {
      ...exportingConfig.exporting,
      filename
    }
  }
}

/**
 * Apply exporting configuration to chart options
 * Merges with existing chart options
 * @param {Object} chartOptions - Existing chart options
 * @param {string} filename - Custom filename for the export
 * @returns {Object} Chart options with exporting configuration
 */
export function withExporting(chartOptions, filename) {
  const exportConfig = filename ? getExportingConfig(filename) : exportingConfig
  
  // Calculate appropriate export dimensions based on chart size
  // This prevents squashing of large charts with many data points
  let sourceWidth = undefined
  let sourceHeight = undefined
  
  // If chart has explicit dimensions, use them for export
  if (chartOptions.chart) {
    const chartHeight = chartOptions.chart.height
    const chartWidth = chartOptions.chart.width
    
    // For charts with explicit height (often large matrices/heatmaps)
    if (chartHeight) {
      // Use actual height or minimum of 1200px for quality
      sourceHeight = Math.max(chartHeight, 1200)
      // Maintain aspect ratio or use default width
      sourceWidth = chartWidth || Math.max(1600, sourceHeight * 1.5)
    } else if (chartWidth) {
      sourceWidth = Math.max(chartWidth, 1200)
    }
  }
  
  return {
    ...chartOptions,
    ...exportConfig,
    // Ensure proper merging if chart already has exporting config
    exporting: {
      ...exportConfig.exporting,
      ...chartOptions.exporting,
      // Override with calculated dimensions if available
      sourceWidth: sourceWidth !== undefined ? sourceWidth : exportConfig.exporting.sourceWidth,
      sourceHeight: sourceHeight !== undefined ? sourceHeight : exportConfig.exporting.sourceHeight,
    }
  }
}

export default Highcharts

