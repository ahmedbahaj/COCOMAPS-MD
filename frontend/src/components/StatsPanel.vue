<template>
  <div class="stats-panel">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ totalInteractions }}</div>
        <div class="stat-label">Unique Residue Pairs</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ visibleInteractions }}</div>
        <div class="stat-label">Unique Filtered Pairs</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ avgConsistency }}</div>
        <div class="stat-label">
          Avg Conservation
          <span 
            class="info-icon" 
            @mouseenter="showTooltip($event, 'Average percentage of frames in which each filtered residue pair is present across the trajectory.')"
            @mouseleave="hideTooltip"
          >ⓘ</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dataStore.totalFrames }}</div>
        <div class="stat-label">Trajectory Frames</div>
      </div>
    </div>
  </div>
  
  <!-- Tooltip -->
  <Teleport to="body">
    <div 
      v-if="activeTooltip.visible" 
      class="stats-tooltip"
      :style="{ top: activeTooltip.y + 'px', left: activeTooltip.x + 'px' }"
    >
      {{ activeTooltip.text }}
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useDataStore } from '../stores/dataStore'

const dataStore = useDataStore()

// Tooltip state
const activeTooltip = ref({
  visible: false,
  text: '',
  x: 0,
  y: 0
})

const showTooltip = (event, text) => {
  const x = event.clientX + 12
  const y = event.clientY - 8
  activeTooltip.value = {
    visible: true,
    text,
    x,
    y
  }
}

const hideTooltip = () => {
  activeTooltip.value.visible = false
}

const totalInteractions = computed(() => {
  return dataStore.interactions.length
})

const visibleInteractions = computed(() => {
  return dataStore.filteredInteractions.length
})

const avgConsistency = computed(() => {
  if (dataStore.filteredInteractions.length === 0) return '-'
  const avg = dataStore.filteredInteractions.reduce((sum, d) => sum + d.consistency, 0) / dataStore.filteredInteractions.length
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  color: #6e6e73;
  font-weight: 500;
}

.info-icon {
  font-size: 13px;
  color: #8e8e93;
  cursor: pointer;
  transition: color 0.15s ease;
}

.info-icon:hover {
  color: #3B6EF5;
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

<style>
/* Global tooltip - teleported to body */
.stats-tooltip {
  position: fixed;
  padding: 10px 14px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  white-space: pre-line;
  max-width: 320px;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  z-index: 100000;
  pointer-events: none;
  text-align: left;
  animation: statsTooltipFadeIn 0.15s ease;
}

@keyframes statsTooltipFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
