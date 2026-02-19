<template>
  <div class="conserved-islands-wrapper">
    <MolStarViewer
      v-if="dataStore.currentSystem?.id"
      :system-id="dataStore.currentSystem.id"
      :selected-residues="selectedIslandResidues"
      class="structure-viewer"
    />
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
      <h3 class="panel-title">Conserved Islands (70% threshold)</h3>
      <p class="panel-subtitle">{{ dataStore.conservedIslands.length }} island(s) found</p>
      <p class="selection-hint">
        <span class="radio-icon" aria-hidden="true">◉</span>
        Select one island below to highlight its residues in the 3D viewer. Click again to clear.
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
          </div>
          <div class="residues-table-wrap">
            <table class="residues-table">
              <thead>
                <tr>
                  <th>Chain</th>
                  <th>Res #</th>
                  <th>Res Name</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(res, idx) in island.residues" :key="`${res.chain}-${res.resNum}-${idx}`">
                  <td>{{ res.chain }}</td>
                  <td>{{ res.resNum }}</td>
                  <td>{{ res.resName || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDataStore } from '../../stores/dataStore'
import MolStarViewer from '../MolStarViewer.vue'

const dataStore = useDataStore()
const selectedIslandId = ref(null)

function selectIsland(id) {
  selectedIslandId.value = selectedIslandId.value === id ? null : id
}

const selectedIslandResidues = computed(() => {
  if (!selectedIslandId.value || !dataStore.conservedIslands) return null
  const island = dataStore.conservedIslands.find(i => i.id === selectedIslandId.value)
  return island?.residues ?? null
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
  margin: 0 0 8px 0;
}

.selection-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #86868b;
  margin: 0 0 16px 0;
}

.radio-icon {
  color: #007aff;
  font-size: 16px;
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

.residues-table-wrap {
  max-height: 280px;
  overflow-y: auto;
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
</style>
