<template>
  <div class="conserved-islands-wrapper">
    <MolStarViewer
      v-if="dataStore.currentSystem?.id"
      :system-id="dataStore.currentSystem.id"
      :selected-residues="selectedResiduesForViewer"
      class="structure-viewer"
    />
    <div class="viz-controls">
      <h3 class="panel-title">3D Visualization</h3>
      <p class="panel-subtitle">Highlight residues in the structure by choosing a mode below.</p>
      <div class="mode-toggle" role="tablist" aria-label="Highlight mode">
        <button
          type="button"
          role="tab"
          :aria-selected="viewMode === 'islands'"
          :class="['mode-btn', { active: viewMode === 'islands' }]"
          @click="viewMode = 'islands'"
        >
          Conserved Islands
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="viewMode === 'pairs'"
          :class="['mode-btn', { active: viewMode === 'pairs' }]"
          @click="viewMode = 'pairs'"
        >
          Most Conserved Pairs
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
        <div class="pairs-toolbar">
          <button type="button" class="toolbar-btn" @click="selectAllPairs">Select all</button>
          <button type="button" class="toolbar-btn" @click="deselectAllPairs">Deselect all</button>
          <span class="pairs-count">{{ selectedPairKeys.length }} of {{ mostConservedList.length }} selected</span>
        </div>
        <ul class="pairs-list" role="list">
          <li
            v-for="item in mostConservedList"
            :key="item.pair"
            class="pair-row"
            :class="{ selected: isPairSelected(item.pair) }"
          >
            <label class="pair-row-label">
              <input
                type="checkbox"
                :checked="isPairSelected(item.pair)"
                :aria-label="`Toggle ${item.pair} in 3D view`"
                @change="togglePair(item.pair)"
              />
              <span class="pair-name">{{ item.pair }}</span>
              <span class="pair-meta">({{ item.frameCount }}/{{ dataStore.totalFrames }} frames)</span>
            </label>
            <div v-if="item.types && item.types.length" class="type-tags">
              <span
                v-for="(t, tIdx) in item.types.slice(0, 4)"
                :key="tIdx"
                class="type-tag"
                :style="{ backgroundColor: getInteractionBaseColor(t.type), color: getTextColorForBg(t.type) }"
              >{{ t.type }}</span>
              <span v-if="item.types.length > 4" class="type-tag more">+{{ item.types.length - 4 }}</span>
            </div>
          </li>
        </ul>
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
import MolStarViewer from '../MolStarViewer.vue'
import IslandGraph from './IslandGraph.vue'

const dataStore = useDataStore()
const { statistics } = useConservationStatistics()

const viewMode = ref('islands')
const selectedIslandId = ref(null)
const islandViewMode = ref({})
const expandedIslandId = ref(null)
const selectedPairKeys = ref([])

const mostConservedList = computed(() => statistics.value?.residue?.mostConservedList ?? [])

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
  selectedPairKeys.value = mostConservedList.value.map((p) => p.pair)
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

.mode-toggle {
  display: flex;
  gap: 0;
  background: #e8e8ed;
  border-radius: 10px;
  padding: 4px;
  width: fit-content;
}

.mode-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: transparent;
  color: #6e6e73;
  transition: background 0.2s, color 0.2s;
}

.mode-btn:hover {
  color: #1d1d1f;
}

.mode-btn.active {
  background: #ffffff;
  color: #1d1d1f;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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

.pairs-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pair-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f5f7;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: border-color 0.2s, background 0.2s;
}

.pair-row:hover {
  background: #ebebed;
}

.pair-row.selected {
  border-color: #007aff;
  background: #f0f7ff;
}

.pair-row-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.pair-row-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  cursor: pointer;
  accent-color: #007aff;
}

.pair-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.pair-meta {
  font-size: 13px;
  color: #6e6e73;
  margin-left: 4px;
}

.pair-row .type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex-shrink: 0;
}

.pair-row .type-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
}

.pair-row .type-tag.more {
  background: #d2d2d7 !important;
  color: #6e6e73;
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
</style>
