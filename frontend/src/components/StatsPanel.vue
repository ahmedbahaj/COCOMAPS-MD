<template>
  <div class="stats-panel">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ totalInteractions }}</div>
        <div class="stat-label">Total Interactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ visibleInteractions }}</div>
        <div class="stat-label">Visible Interactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ avgConsistency }}</div>
        <div class="stat-label">Avg Conservation</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dataStore.totalFrames }}</div>
        <div class="stat-label">Total Frames</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDataStore } from '../stores/dataStore'

const dataStore = useDataStore()

const totalInteractions = computed(() => {
  return dataStore.interactions.length
})

const visibleInteractions = computed(() => {
  return dataStore.filteredInteractions.length
})

const avgConsistency = computed(() => {
  if (dataStore.interactions.length === 0) return '-'
  const avg = dataStore.interactions.reduce((sum, d) => sum + d.consistency, 0) / dataStore.interactions.length
  return Math.round(avg * 100) + '%'
})
</script>

<style scoped>
.stats-panel {
  background: #fbfbfd;
  border-radius: 18px;
  padding: 24px 32px;
  margin-top: 32px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  border: 1px solid #d2d2d7;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6e6e73;
  font-weight: 500;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 500px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
