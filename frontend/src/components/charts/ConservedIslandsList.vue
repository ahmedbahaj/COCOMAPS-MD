<template>
  <div class="conserved-islands-wrapper">
    <MolStarViewer
      v-if="dataStore.currentSystem?.id"
      :system-id="dataStore.currentSystem.id"
      :selected-residues="selectedResiduesForViewer"
      :highlight-mode="viewMode === 'islands' ? 'ball-and-stick' : 'select'"
      class="structure-viewer"
    />
    <div class="viz-controls">
      <h3 class="panel-title">3D Visualization</h3>
      <p class="panel-subtitle">Highlight residues in the structure by choosing a mode below.</p>
      <div class="mode-cards" role="tablist" aria-label="Highlight mode">
        <button
          type="button"
          role="tab"
          :aria-selected="viewMode === 'islands'"
          :class="['mode-card', { active: viewMode === 'islands' }]"
          @click="viewMode = 'islands'"
        >
          <span class="mode-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <circle cx="6" cy="6" r="2"/>
              <circle cx="18" cy="6" r="2"/>
              <circle cx="6" cy="18" r="2"/>
              <circle cx="18" cy="18" r="2"/>
              <line x1="7.5" y1="7.5" x2="10" y2="10"/>
              <line x1="16.5" y1="7.5" x2="14" y2="10"/>
              <line x1="7.5" y1="16.5" x2="10" y2="14"/>
              <line x1="16.5" y1="16.5" x2="14" y2="14"/>
            </svg>
          </span>
          <span class="mode-card-text">
            <span class="mode-card-title">Conserved Islands</span>
            <span class="mode-card-desc">Groups of residues forming connected clusters</span>
          </span>
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="viewMode === 'pairs'"
          :class="['mode-card', { active: viewMode === 'pairs' }]"
          @click="viewMode = 'pairs'"
        >
          <span class="mode-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="8" cy="12" r="4"/>
              <circle cx="16" cy="12" r="4"/>
              <line x1="12" y1="12" x2="12" y2="12"/>
              <path d="M11 10l2 2-2 2"/>
            </svg>
          </span>
          <span class="mode-card-text">
            <span class="mode-card-title">Most Conserved Pairs</span>
            <span class="mode-card-desc">Individual residue pairs ranked by conservation</span>
          </span>
        </button>
      </div>
    </div>

    <template v-if="viewMode === 'islands'">
      <div v-if="dataStore.loading.conservedIslands" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Loading conserved islands...</p>
      </div>
      <div v-else-if="dataStore.errors.conservedIslands" class="error-state">
        <p>{{ dataStore.errors.conservedIslands }}</p>
        <p class="hint">Run the pipeline or <code>python conserved_islands.py systems/{{ dataStore.currentSystem?.id }}</code> to generate.</p>
      </div>
      <div v-else-if="!dataStore.conservedIslands || dataStore.conservedIslands.length === 0" class="empty-state">
        <p>No conserved islands found for this system.</p>
        <p class="hint">Run the pipeline or <code>python conserved_islands.py systems/{{ dataStore.currentSystem?.id }}</code> to generate.</p>
      </div>
      <div v-else class="islands-content">
        <p class="selection-hint">
          <span class="radio-icon" aria-hidden="true">◉</span>
          Select one island to highlight its residues in the 3D viewer. Click again to clear.
        </p>
        <div class="islands-list" role="radiogroup" aria-label="Conserved islands">
        <div
          v-for="island in dataStore.conservedIslands"
          :key="island.id"
          class="island-card"
          :class="{ selected: selectedIslandId === island.id }"
          role="radio"
          :aria-checked="selectedIslandId === island.id"
          tabindex="0"
          @click="selectIsland(island.id)"
          @keydown.enter.prevent="selectIsland(island.id)"
          @keydown.space.prevent="selectIsland(island.id)"
        >
          <div class="island-header">
            <span class="island-radio" :class="{ checked: selectedIslandId === island.id }" aria-hidden="true" />
            <span class="island-id">Island {{ island.id }}</span>
            <span class="island-size">{{ island.size }} residues</span>
            <span class="island-chains">Chains: {{ island.chains?.join(', ') || '—' }}</span>
            <div class="view-toggle" @click.stop>
              <button
                type="button"
                class="view-toggle-btn"
                :class="{ active: getIslandViewMode(island.id) === 'graph' }"
                @click="setIslandViewMode(island.id, 'graph')"
              >
                Graph
              </button>
              <button
                type="button"
                class="view-toggle-btn"
                :class="{ active: getIslandViewMode(island.id) === 'table' }"
                @click="setIslandViewMode(island.id, 'table')"
              >
                Table
              </button>
            </div>
          </div>
          <div class="island-body">
            <div
              v-if="getIslandViewMode(island.id) === 'graph'"
              class="graph-wrapper"
            >
              <IslandGraph
                :island="island"
                :expanded="expandedIslandId === island.id"
              />
              <button
                type="button"
                class="expand-btn graph-expand-btn"
                :class="{ expanded: expandedIslandId === island.id }"
                @click.stop="toggleExpandedIsland(island.id)"
                aria-label="Expand or collapse graph height"
              >
                <span v-if="expandedIslandId === island.id">▴</span>
                <span v-else>▾</span>
              </button>
            </div>
            <div v-else class="residues-table-wrap">
              <table class="residues-table">
                <thead>
                  <tr>
                    <th>Chain</th>
                    <th>Res #</th>
                    <th>Res Name</th>
                    <th>Connected to (in island)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(res, idx) in island.residues" :key="`${res.chain}-${res.resNum}-${idx}`">
                    <td>{{ res.chain }}</td>
                    <td>{{ res.resNum }}</td>
                    <td>{{ res.resName || '—' }}</td>
                    <td class="connected-cell">
                      <span v-if="!res.connectedTo || res.connectedTo.length === 0" class="muted">—</span>
                      <span v-else class="connected-list">
                        <span
                          v-for="(conn, i) in res.connectedTo"
                          :key="`${conn.chain}-${conn.resNum}-${i}`"
                          class="connected-tag"
                        >
                          {{ conn.chain }}:{{ conn.resNum }} {{ conn.resName }}
                        </span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        </div>
      </div>
    </template>
    <template v-else-if="viewMode === 'pairs'">
    <div class="pairs-content">
      <div v-if="!mostConservedList || mostConservedList.length === 0" class="empty-state">
        <p>No conserved pairs for this system yet.</p>
        <p class="hint">Run the pipeline and ensure you have interaction data. Conservation thresholds apply from the Conservation Analysis panel.</p>
      </div>
      <div v-else>
        <p class="selection-hint">
          <span class="check-icon" aria-hidden="true">☑</span>
          All pairs are selected by default. Toggle checkboxes to show only the pairs you want in the 3D viewer.
        </p>

        <!-- Pair Conservation Threshold Slider -->
        <div class="slider-section">
          <label for="pairs-conservation-slider" class="slider-label">Pair Conservation Threshold</label>
          <div class="slider-container">
            <div class="slider-control">
              <input
                id="pairs-conservation-slider"
                type="range"
                min="0"
                max="1"
                step="0.1"
                :value="dataStore.currentThreshold"
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
                :value="thresholdPercent"
                @input="updateThresholdFromInput"
                @blur="validateThresholdInput"
                min="0"
                max="100"
                step="1"
                class="value-input"
              />
              <span class="percent-symbol">%</span>
            </div>
          </div>
          <p class="slider-description">Show pairs with conservation ≥ {{ thresholdPercent }}%</p>
        </div>

        <!-- Toolbar: search + select/deselect (immediately above table) -->
        <div class="pairs-toolbar">
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 20 20" width="16" height="16"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><line x1="12.5" y1="12.5" x2="17" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            <input
              type="text"
              v-model="searchQuery"
              placeholder="Search residues…"
              class="search-input"
            />
            <button v-if="searchQuery" type="button" class="search-clear" @click="searchQuery = ''">✕</button>
          </div>
          <button type="button" class="toolbar-btn" @click="selectAllPairs">Select all</button>
          <button type="button" class="toolbar-btn" @click="deselectAllPairs">Deselect all</button>
          <span class="pairs-count">{{ selectedPairKeys.length }} / {{ filteredPairsList.length }} selected</span>
        </div>

        <div class="pairs-table-wrap">
          <table class="pairs-table">
            <thead>
              <tr>
                <th class="col-check">
                  <input
                    type="checkbox"
                    :checked="allFilteredSelected"
                    :indeterminate="someFilteredSelected && !allFilteredSelected"
                    @change="toggleAllFiltered"
                    aria-label="Select all visible pairs"
                  />
                </th>
                <th class="col-pair sortable" @click="toggleSort('pair')">
                  Residue Pair
                  <span class="sort-arrow" :class="sortIndicatorClass('pair')"></span>
                </th>
                <th class="col-conservation sortable" @click="toggleSort('conservation')">
                  Conservation
                  <span class="sort-arrow" :class="sortIndicatorClass('conservation')"></span>
                </th>
                <th class="col-frames sortable" @click="toggleSort('frames')">
                  Frames
                  <span class="sort-arrow" :class="sortIndicatorClass('frames')"></span>
                </th>
              </tr>
            </thead>
            <tbody>
              <template v-for="item in filteredPairsList" :key="item.pair">
                <tr
                  class="pair-data-row"
                  :class="{ selected: isPairSelected(item.pair) }"
                >
                  <td class="col-check" @click.stop>
                    <input
                      type="checkbox"
                      :checked="isPairSelected(item.pair)"
                      @change="togglePair(item.pair)"
                      :aria-label="`Toggle ${item.pair} in 3D view`"
                    />
                  </td>
                  <td class="col-pair">
                    <span class="pair-name">{{ item.pair }}</span>
                  </td>
                  <td class="col-conservation">
                    <div class="conservation-cell">
                      <div class="conservation-bar-track">
                        <div
                          class="conservation-bar-fill"
                          :style="{ width: conservationPercent(item) + '%', backgroundColor: conservationColor(item) }"
                        ></div>
                      </div>
                      <span class="conservation-value">{{ conservationPercent(item) }}%</span>
                    </div>
                  </td>
                  <td class="col-frames">
                    <span class="frames-value">{{ item.frameCount }}</span>
                    <span class="frames-total"> / {{ dataStore.totalFrames }}</span>
                  </td>
                </tr>
              </template>
              <tr v-if="filteredPairsList.length === 0" class="no-results-row">
                <td colspan="4">
                  <div class="no-results">No pairs match "{{ searchQuery }}"</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDataStore } from '../../stores/dataStore'
import { useConservationStatistics } from '../../composables/useConservationStatistics'
import { parseResidueId, getInteractionBaseColor, getTextColorForBg } from '../../utils/chartHelpers'
import MolStarViewer from '../analysis/MolStarViewer.vue'
import IslandGraph from './IslandGraph.vue'

const dataStore = useDataStore()
const { statistics } = useConservationStatistics()

const viewMode = ref('islands')
const selectedIslandId = ref(null)
const islandViewMode = ref({})
const expandedIslandId = ref(null)
const selectedPairKeys = ref([])

// --- New state for table features ---
const searchQuery = ref('')
const sortColumn = ref('conservation') // 'pair' | 'conservation' | 'frames' | 'types'
const sortDirection = ref('desc')       // 'asc' | 'desc'

const mostConservedList = computed(() => statistics.value?.residue?.mostConservedList ?? [])

// --- Search + Sort ---
const filteredPairsList = computed(() => {
  let list = [...mostConservedList.value]

  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(item => item.pair.toLowerCase().includes(q))
  }

  // Sort
  list.sort((a, b) => {
    let cmp = 0
    switch (sortColumn.value) {
      case 'pair':
        cmp = a.pair.localeCompare(b.pair)
        break
      case 'conservation':
        cmp = (a.frameCount / (dataStore.totalFrames || 1)) - (b.frameCount / (dataStore.totalFrames || 1))
        break
      case 'frames':
        cmp = a.frameCount - b.frameCount
        break
    }
    return sortDirection.value === 'asc' ? cmp : -cmp
  })

  return list
})

function toggleSort(col) {
  if (sortColumn.value === col) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortDirection.value = col === 'pair' ? 'asc' : 'desc'
  }
}

function sortIndicatorClass(col) {
  if (sortColumn.value !== col) return 'inactive'
  return sortDirection.value === 'asc' ? 'asc' : 'desc'
}

// --- Conservation display helpers ---
function conservationPercent(item) {
  const totalFrames = dataStore.totalFrames || 1
  return Math.round((item.frameCount / totalFrames) * 100)
}

function conservationColor(item) {
  const pct = conservationPercent(item) / 100
  // Gradient: light blue → deep blue
  if (pct >= 0.9) return '#0D47A1'
  if (pct >= 0.7) return '#1E88E5'
  if (pct >= 0.5) return '#42A5F5'
  if (pct >= 0.3) return '#90CAF9'
  return '#BBDEFB'
}

// --- Header checkbox (select/deselect all filtered) ---
const allFilteredSelected = computed(() => {
  if (filteredPairsList.value.length === 0) return false
  return filteredPairsList.value.every(item => isPairSelected(item.pair))
})
const someFilteredSelected = computed(() => {
  return filteredPairsList.value.some(item => isPairSelected(item.pair))
})
function toggleAllFiltered() {
  if (allFilteredSelected.value) {
    // Deselect all filtered
    const filteredKeys = new Set(filteredPairsList.value.map(p => p.pair))
    selectedPairKeys.value = selectedPairKeys.value.filter(k => !filteredKeys.has(k))
  } else {
    // Select all filtered (keep existing selections too)
    const existing = new Set(selectedPairKeys.value)
    filteredPairsList.value.forEach(item => existing.add(item.pair))
    selectedPairKeys.value = Array.from(existing)
  }
}

// --- Pair selection ---
watch(
  [viewMode, mostConservedList],
  () => {
    if (viewMode.value === 'pairs' && mostConservedList.value.length > 0 && selectedPairKeys.value.length === 0) {
      selectedPairKeys.value = mostConservedList.value.map((p) => p.pair)
    }
  },
  { immediate: true }
)

watch(mostConservedList, (list) => {
  if (list.length > 0 && viewMode.value === 'pairs') {
    selectedPairKeys.value = list.map((p) => p.pair)
  }
}, { deep: true })

// --- Island helpers ---
function selectIsland(id) {
  selectedIslandId.value = selectedIslandId.value === id ? null : id
}
function getIslandViewMode(id) {
  const current = islandViewMode.value[id]
  return current === 'table' ? 'table' : 'graph'
}
function setIslandViewMode(id, mode) {
  islandViewMode.value = { ...islandViewMode.value, [id]: mode }
}
function toggleExpandedIsland(id) {
  expandedIslandId.value = expandedIslandId.value === id ? null : id
}

function pairStringToResidues(pairStr) {
  if (!pairStr || typeof pairStr !== 'string') return []
  const parts = pairStr.split(/\s*↔\s*/).map((s) => s.trim()).filter(Boolean)
  if (parts.length !== 2) return []
  const r1 = parseResidueId(parts[0])
  const r2 = parseResidueId(parts[1])
  const out = []
  if (r1) out.push({ chain: r1.chain, resNum: Number(r1.resNum), resName: r1.resName })
  if (r2) out.push({ chain: r2.chain, resNum: Number(r2.resNum), resName: r2.resName })
  return out
}

function isPairSelected(pairKey) {
  return selectedPairKeys.value.includes(pairKey)
}
function togglePair(pairKey) {
  if (isPairSelected(pairKey)) {
    selectedPairKeys.value = selectedPairKeys.value.filter((k) => k !== pairKey)
  } else {
    selectedPairKeys.value = [...selectedPairKeys.value, pairKey]
  }
}
function selectAllPairs() {
  selectedPairKeys.value = filteredPairsList.value.map((p) => p.pair)
}
function deselectAllPairs() {
  selectedPairKeys.value = []
}

const selectedIslandResidues = computed(() => {
  if (!selectedIslandId.value || !dataStore.conservedIslands) return null
  const island = dataStore.conservedIslands.find((i) => i.id === selectedIslandId.value)
  return island?.residues ?? null
})

const selectedPairsResidues = computed(() => {
  if (viewMode.value !== 'pairs' || selectedPairKeys.value.length === 0) return null
  const seen = new Set()
  const list = []
  selectedPairKeys.value.forEach((pairKey) => {
    pairStringToResidues(pairKey).forEach((r) => {
      const key = `${r.chain}-${r.resNum}`
      if (!seen.has(key)) {
        seen.add(key)
        list.push(r)
      }
    })
  })
  return list.length ? list : null
})

const selectedResiduesForViewer = computed(() => {
  if (viewMode.value === 'islands') return selectedIslandResidues.value
  return selectedPairsResidues.value
})

// --- Pair Conservation Threshold slider ---
const thresholdPercent = computed(() => Math.round(dataStore.currentThreshold * 100))

const conservationTicks = computed(() => {
  const ticks = []
  for (let value = 0; value <= 1.0 + 0.0001; value += 0.1) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

const updateThreshold = (event) => {
  dataStore.setThreshold(parseFloat(event.target.value))
}

const updateThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    dataStore.setThreshold(value / 100)
  }
}

const validateThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = thresholdPercent.value
    return
  }
  value = Math.max(0, Math.min(100, value))
  event.target.value = value
  dataStore.setThreshold(value / 100)
}
</script>

<style scoped>
.conserved-islands-wrapper {
  min-height: 400px;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.structure-viewer {
  flex-shrink: 0;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  color: #6e6e73;
  font-size: 17px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #d2d2d7;
  border-top-color: #1d1d1f;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state p,
.empty-state p {
  margin: 0 0 8px 0;
}

.hint {
  font-size: 14px;
  color: #86868b;
  margin-top: 8px;
}

.hint code {
  background: #f5f5f7;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.panel-title {
  font-size: 22px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 4px 0;
}

.panel-subtitle {
  font-size: 15px;
  color: #6e6e73;
  margin: 0 0 16px 0;
}

.viz-controls {
  margin-bottom: 20px;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  background: #f5f5f7;
  border: 2px solid #e8e8ed;
  border-radius: 14px;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: all 0.2s ease;
}

.mode-card:hover {
  border-color: #d2d2d7;
  background: #f0f0f2;
}

.mode-card.active {
  background: #ffffff;
  border-color: #007aff;
  box-shadow: 0 2px 10px rgba(0, 122, 255, 0.12);
}

.mode-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  background: #e8e8ed;
  border-radius: 10px;
  color: #6e6e73;
  transition: all 0.2s ease;
}

.mode-card.active .mode-card-icon {
  background: rgba(0, 122, 255, 0.1);
  color: #007aff;
}

.mode-card-icon svg {
  width: 20px;
  height: 20px;
}

.mode-card-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.mode-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  line-height: 1.3;
}

.mode-card-desc {
  font-size: 12px;
  font-weight: 400;
  color: #86868b;
  line-height: 1.4;
}

.mode-card.active .mode-card-title {
  color: #007aff;
}

.selection-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #86868b;
  margin: 0 0 16px 0;
}

.radio-icon,
.check-icon {
  color: #007aff;
  font-size: 16px;
}

.pairs-content .empty-state {
  margin-top: 0;
}

.pairs-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-btn {
  padding: 8px 14px;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #ffffff;
  color: #1d1d1f;
  transition: background 0.15s, border-color 0.15s;
}

.toolbar-btn:hover {
  background: #f5f5f7;
  border-color: #c7c7cc;
}

.pairs-count {
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
}

/* =================== Search Box =================== */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 300px;
}
.search-icon {
  position: absolute;
  left: 12px;
  color: #86868b;
  pointer-events: none;
}
.search-input {
  width: 100%;
  padding: 8px 32px 8px 34px;
  font-size: 14px;
  border: 2px solid #d2d2d7;
  border-radius: 10px;
  background: #ffffff;
  color: #1d1d1f;
  font-family: inherit;
  transition: border-color 0.15s;
}
.search-input:focus {
  outline: none;
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, 0.08);
}
.search-input::placeholder {
  color: #a1a1a6;
}
.search-clear {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  font-size: 14px;
  color: #86868b;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 50%;
}
.search-clear:hover {
  color: #1d1d1f;
  background: #e8e8ed;
}

/* =================== Sortable Table =================== */
.pairs-table-wrap {
  overflow-x: auto;
  border: 1px solid #e8e8ed;
  border-radius: 12px;
  background: #ffffff;
}

.pairs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.pairs-table thead th {
  text-align: left;
  padding: 12px 16px;
  background: #f5f5f7;
  color: #6e6e73;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #e8e8ed;
  white-space: nowrap;
  user-select: none;
}

.pairs-table thead th.sortable {
  cursor: pointer;
  transition: color 0.15s;
}
.pairs-table thead th.sortable:hover {
  color: #1d1d1f;
}

.col-check {
  width: 40px;
  text-align: center;
}
.col-check input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #007aff;
}
.col-pair { min-width: 180px; }
.col-conservation { min-width: 160px; }
.col-frames { min-width: 90px; }
.col-types { min-width: 100px; }

/* Sort arrows */
.sort-arrow {
  display: inline-block;
  width: 0;
  height: 0;
  margin-left: 6px;
  vertical-align: middle;
}
.sort-arrow.inactive::after {
  content: '⇅';
  font-size: 11px;
  opacity: 0.4;
}
.sort-arrow.asc::after {
  content: '↑';
  font-size: 13px;
  font-weight: 700;
  color: #1d1d1f;
}
.sort-arrow.desc::after {
  content: '↓';
  font-size: 13px;
  font-weight: 700;
  color: #1d1d1f;
}

/* Data rows */
.pair-data-row {
  cursor: pointer;
  transition: background 0.12s;
}
.pair-data-row td {
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f2;
  vertical-align: middle;
}
.pair-data-row:hover {
  background: #fafafa;
}
.pair-data-row.selected {
  background: #f0f7ff;
}

.pair-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

/* Conservation bar */
.conservation-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.conservation-bar-track {
  flex: 1;
  height: 8px;
  background: #e8e8ed;
  border-radius: 4px;
  overflow: hidden;
  min-width: 60px;
}
.conservation-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.conservation-value {
  font-size: 13px;
  font-weight: 700;
  color: #1d1d1f;
  font-variant-numeric: tabular-nums;
  min-width: 36px;
  text-align: right;
}

/* Frames column */
.frames-value {
  font-weight: 600;
  color: #1d1d1f;
  font-variant-numeric: tabular-nums;
}
.frames-total {
  color: #86868b;
  font-size: 12px;
}

/* Type dots (compact) */
.col-types > div,
.col-types {
  display: flex;
  align-items: center;
  gap: 6px;
}
.type-dots {
  display: flex;
  gap: 3px;
  align-items: center;
}
.type-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.type-dot-more {
  font-size: 11px;
  font-weight: 600;
  color: #86868b;
}
.types-count {
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  margin-left: 2px;
}


/* No results */
.no-results-row td {
  border-bottom: none;
}
.no-results {
  padding: 40px 20px;
  text-align: center;
  color: #86868b;
  font-size: 15px;
}

.islands-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.island-card {
  background: #f5f5f7;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #e8e8ed;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.island-card:hover {
  border-color: #c7c7cc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.island-card.selected {
  border-color: #007aff;
  box-shadow: 0 0 0 1px #007aff;
}

.island-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  font-size: 15px;
}

.island-radio {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 2px solid #c7c7cc;
  border-radius: 50%;
  background: #fff;
  transition: border-color 0.2s, background 0.2s;
}

.island-radio.checked {
  border-color: #007aff;
  background: #007aff;
  box-shadow: inset 0 0 0 3px #fff;
}

.island-id {
  font-weight: 600;
  color: #1d1d1f;
}

.island-size {
  color: #6e6e73;
}

.island-chains {
  color: #1d1d1f;
  font-weight: 500;
}

.island-body {
  background: #f5f5f7;
}

.view-toggle {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.view-toggle-btn {
  border: none;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  background: #f5f5f7;
  color: #6e6e73;
  transition: background 0.15s ease, color 0.15s ease;
}

.view-toggle-btn.active {
  background: #007aff;
  color: #ffffff;
}

.graph-wrapper {
  position: relative;
}

.graph-expand-btn {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  border: none;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 50%;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  background: #ffffff;
  color: #6e6e73;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-expand-btn:hover {
  background: #f5f5f7;
  color: #1d1d1f;
}

.graph-expand-btn.expanded {
  background: #e5e5ea;
  color: #1d1d1f;
}

.residues-table-wrap {
  max-height: 280px;
  overflow-y: auto;
  padding: 8px 20px 20px;
}

.residues-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.residues-table th {
  text-align: left;
  padding: 10px 16px;
  background: #ebebed;
  color: #6e6e73;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.residues-table td {
  padding: 8px 16px;
  border-bottom: 1px solid #e8e8ed;
  color: #1d1d1f;
}

.residues-table tbody tr:last-child td {
  border-bottom: none;
}

.residues-table tbody tr:hover {
  background: #fafafa;
}

.connected-cell {
  max-width: 280px;
}

.muted {
  color: #86868b;
}

.connected-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}

.connected-tag {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  background: #e8f4fc;
  color: #1d1d1f;
  border-radius: 6px;
  white-space: nowrap;
}

/* Slider styles (matching ControlsPanel / DistanceDistribution) */
.slider-section {
  margin-bottom: 20px;
  padding: 16px 0;
  border-top: 1px solid #e8e8ed;
}

.slider-label {
  display: block;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  letter-spacing: -0.022em;
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
  border-radius: 2px;
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
  font-size: 14px;
  color: #6e6e73;
  margin-top: 8px;
  margin-bottom: 0;
}
</style>
