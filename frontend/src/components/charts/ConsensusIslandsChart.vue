<template>
  <div class="consensus-islands-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Analyzing interaction networks across frames...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="fetchData" class="retry-btn">Retry</button>
    </div>

    <!-- Results -->
    <div v-else-if="data" class="results-section">
      <!-- No Islands Message -->
      <div v-if="topIslands.length === 0" class="no-islands">
        <p>No consensus islands found.</p>
      </div>

      <!-- Main Content: Graph + Island Cards -->
      <div v-else class="main-content">
        <!-- Network Graph -->
        <div class="graph-section">
          <div v-if="topIslands.length > 0" class="island-selector">
            <label for="islandSelect">View Island:</label>
            <select 
              id="islandSelect"
              v-model.number="selectedIslandForGraph"
              class="selector-dropdown"
            >
              <option :value="null">Select an island</option>
              <option 
                v-for="island in topIslands"
                :key="island.id"
                :value="island.id"
              >
                Island {{ island.id }} ({{ island.size }} residues, {{ island.avgConservation }}% conservation)
              </option>
            </select>
          </div>
          <div ref="chartContainer" class="chart-container"></div>
          <div class="graph-legend">
            <div 
              v-for="chain in uniqueChains" 
              :key="chain"
              class="legend-item"
            >
              <span class="legend-dot" :style="{ backgroundColor: getChainColor(chain) }"></span>
              <span class="legend-label">Chain {{ chain }}</span>
            </div>
          </div>
        </div>

        <!-- Island Cards -->
        <div class="islands-panel">
          <div 
            v-for="(island, index) in topIslands" 
            :key="island.id"
            class="island-card"
          >
            <div class="island-content">
              <div class="island-header">
                <span class="island-title">Island {{ island.id }}</span>
                <div class="chain-badges">
                  <span 
                    v-for="chain in island.chainsInvolved" 
                    :key="chain"
                    class="chain-badge"
                    :style="{ backgroundColor: getChainColor(chain) }"
                  >{{ chain }}</span>
                </div>
              </div>
              <div class="island-stats">
                <div class="stat">
                  <span class="stat-num">{{ island.size }}</span>
                  <span class="stat-txt">residues</span>
                </div>
                <div class="stat">
                  <span class="stat-num">{{ island.avgConservation }}%</span>
                  <span class="stat-txt">islands conservation</span>
                </div>
              </div>
              <div class="residue-list">
                <span class="residue-text">
                  {{ island.residues.slice(0, expandedIslands.has(island.id) ? island.residues.length : 8).map(res => `${res.resName}${res.resNum}`).join(', ') }}
                </span>
                <span 
                  v-if="island.residues.length > 8 && !expandedIslands.has(island.id)"
                  class="more-tag"
                  @click="toggleExpandIsland(island.id)"
                >
                  +{{ island.residues.length - 8 }} more
                </span>
                <span 
                  v-if="island.residues.length > 8 && expandedIslands.has(island.id)"
                  class="more-tag"
                  @click="toggleExpandIsland(island.id)"
                >
                  show less
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useDataStore } from '../../stores/dataStore'
import api from '../../services/api'
import Highcharts from '../../utils/highchartsConfig'
import NetworkgraphModule from 'highcharts/modules/networkgraph'

// Initialize networkgraph module
NetworkgraphModule(Highcharts)

const dataStore = useDataStore()

// State
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const highlightedIsland = ref(null)
const chartContainer = ref(null)
const expandedIslands = ref(new Set())
const selectedIslandForGraph = ref(null)
let chart = null

// Chain colors - professional palette
const chainColors = {
  'A': '#2563eb',
  'B': '#dc2626',
  'C': '#059669',
  'D': '#7c3aed',
  'E': '#d97706',
  'F': '#0891b2',
  'G': '#be185d',
  'H': '#4b5563',
}

const getChainColor = (chain) => {
  return chainColors[chain] || '#6b7280'
}

// Computed
const topIslands = computed(() => {
  if (!data.value?.islands) return []
  // Sort by combined score: size * avgConservation
  const sorted = [...data.value.islands].sort((a, b) => {
    const scoreA = a.size * a.avgConservation
    const scoreB = b.size * b.avgConservation
    return scoreB - scoreA
  })
  return sorted.slice(0, 3)
})

const totalResiduesInTop = computed(() => {
  return topIslands.value.reduce((sum, island) => sum + island.size, 0)
})

const uniqueChains = computed(() => {
  const chains = new Set()
  topIslands.value.forEach(island => {
    island.chainsInvolved.forEach(c => chains.add(c))
  })
  return Array.from(chains).sort()
})

// Methods
const highlightIsland = (islandId) => {
  highlightedIsland.value = islandId
  updateChartHighlight(islandId)
}

const updateChartHighlight = (islandId) => {
  // Highlighting disabled for now - can be implemented later
}

const toggleExpandIsland = (islandId) => {
  if (expandedIslands.value.has(islandId)) {
    expandedIslands.value.delete(islandId)
  } else {
    expandedIslands.value.add(islandId)
  }
}

const renderChart = () => {
  if (!chartContainer.value || topIslands.value.length === 0 || !selectedIslandForGraph.value) {
    return
  }

  // Find the selected island
  const selectedIsland = topIslands.value.find(island => island.id === selectedIslandForGraph.value)
  if (!selectedIsland) return

  // Prepare nodes and links from actual interaction data
  const nodes = []
  const links = []
  const islandColor = '#3b82f6'
  
  // Add nodes for this island
  selectedIsland.residues.forEach(res => {
    nodes.push({
      id: res.id,
      name: `${res.resName}${res.resNum}`,
      marker: {
        radius: 10,
        fillColor: getChainColor(res.chain),
        lineWidth: 2,
        lineColor: islandColor
      },
      islandId: selectedIsland.id,
      chain: res.chain,
      color: getChainColor(res.chain)
    })
  })

  // Add actual interaction edges from backend data
  if (selectedIsland.edges) {
    selectedIsland.edges.forEach(edge => {
      links.push({
        from: edge.from,
        to: edge.to,
        color: islandColor + '80', // Add transparency
        width: Math.max(1, Math.min(edge.frequency / 20, 4)) // Width based on frequency
      })
    })
  }

  // Destroy existing chart
  if (chart) {
    chart.destroy()
    chart = null
  }

  if (links.length === 0) {
    // No edges to show
    return
  }

  try {
    chart = Highcharts.chart(chartContainer.value, {
      chart: {
        type: 'networkgraph',
        backgroundColor: '#fafafa',
        height: 400
      },
      title: { text: null },
      credits: { enabled: false },
      plotOptions: {
        networkgraph: {
          keys: ['from', 'to'],
          layoutAlgorithm: {
            enableSimulation: false,
            initialPositions: 'circle'
          }
        }
      },
      series: [{
        type: 'networkgraph',
        draggable: false,
        dataLabels: {
          enabled: true,
          linkFormat: '',
          allowOverlap: false,
          style: {
            fontSize: '9px',
            fontWeight: '600',
            textOutline: '2px white'
          }
        },
        marker: {
          radius: 10
        },
        nodes: nodes,
        data: links
      }],
      tooltip: {
        formatter: function() {
          if (this.point.isNode !== false) {
            return `<b>${this.point.name || this.point.id}</b><br/>Chain: ${this.point.chain || '?'}`
          }
          // For edges
          if (this.point.from && this.point.to) {
            return `${this.point.from} ↔ ${this.point.to}`
          }
          return false
        }
      }
    })
  } catch (e) {
    console.error('Chart render error:', e)
  }
}

const fetchData = async () => {
  if (!dataStore.currentSystem?.id) {
    error.value = 'No system selected'
    return
  }

  loading.value = true
  error.value = null

  try {
    // Use lower thresholds to get more islands, then we pick top 3
    data.value = await api.getConsensusIslands(dataStore.currentSystem.id, {
      minCoIslandFrequency: 30,
      minIslandSize: 3
    })
    
    // Wait for DOM to update, then render chart
    await nextTick()
    setTimeout(() => {
      renderChart()
    }, 100)
  } catch (e) {
    error.value = e.message || 'Failed to fetch consensus islands data'
    data.value = null
  } finally {
    loading.value = false
  }
}

// Watch for system changes
watch(() => dataStore.currentSystem?.id, () => {
  if (dataStore.currentSystem?.id) {
    fetchData()
  }
})

// Re-render chart when data changes
watch(topIslands, () => {
  // Auto-select first island when data loads
  if (topIslands.value.length > 0 && !selectedIslandForGraph.value) {
    selectedIslandForGraph.value = topIslands.value[0].id
  }
  nextTick(() => renderChart())
}, { deep: true })

watch(selectedIslandForGraph, () => {
  nextTick(() => renderChart())
})

onMounted(() => {
  if (dataStore.currentSystem?.id) {
    fetchData()
  }
})
</script>

<style scoped>
.consensus-islands-container {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #1f2937;
  padding: 24px;
}

/* Header */
.header-section {
  text-align: center;
  margin-bottom: 24px;
}

.main-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 6px 0;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 0.9rem;
  color: #6b7280;
  margin: 0;
}

/* Summary Row */
.summary-row {
  display: flex;
  justify-content: center;
  gap: 48px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.1;
}

.stat-label {
  font-size: 0.75rem;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Loading & Error */
.loading-state, .error-state {
  text-align: center;
  padding: 60px 20px;
  color: #6b7280;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 20px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
}

.no-islands {
  text-align: center;
  padding: 48px;
  color: #6b7280;
}

/* Main Content */
.main-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  align-items: start;
}

/* Graph Section */
.graph-section {
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
}

.island-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.island-selector label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #374151;
}

.selector-dropdown {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.9rem;
  color: #1f2937;
  cursor: pointer;
}

.selector-dropdown:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.chart-container {
  width: 100%;
  min-height: 400px;
}

.graph-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
  margin-top: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-label {
  font-size: 0.8rem;
  color: #4b5563;
}

/* Islands Panel */
.islands-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.island-card {
  display: flex;
  gap: 12px;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  transition: none;
  cursor: default;
}

.island-card:hover,
.island-card.highlighted {
  border-color: #e5e7eb;
  box-shadow: none;
}

.island-rank {
  display: none;
}

.island-content {
  flex: 1;
  min-width: 0;
}

.island-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.island-title {
  font-weight: 600;
  color: #111827;
}

.chain-badges {
  display: flex;
  gap: 4px;
}

.chain-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 600;
  color: white;
}

.island-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-num {
  font-size: 1.1rem;
  font-weight: 600;
  color: #111827;
}

.stat-txt {
  font-size: 0.75rem;
  color: #6b7280;
}

.residue-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.residue-text {
  font-size: 0.85rem;
  color: #9ca3af;
  line-height: 1.4;
}

.more-tag {
  padding: 0;
  font-size: 0.85rem;
  color: #2563eb;
  cursor: pointer;
  user-select: none;
}

/* Responsive */
@media (max-width: 900px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .islands-panel {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .island-card {
    flex: 1;
    min-width: 250px;
  }
}

/* Print */
@media print {
  .consensus-islands-container {
    padding: 0;
  }
}
</style>
