<template>
  <div class="conserved-islands-wrapper">
    <MolStarViewer
      v-if="dataStore.currentSystem?.id"
      :system-id="dataStore.currentSystem.id"
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
      <div class="islands-list">
        <div
          v-for="island in dataStore.conservedIslands"
          :key="island.id"
          class="island-card"
        >
          <div class="island-header">
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
import { useDataStore } from '../../stores/dataStore'
import MolStarViewer from '../MolStarViewer.vue'

const dataStore = useDataStore()

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
  margin: 0 0 20px 0;
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
  border: 1px solid #e8e8ed;
}

.island-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  font-size: 15px;
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
