<template>
  <div class="interaction-legend">
    <div class="legend-header" v-if="title">
      {{ title }}
    </div>
    <div class="legend-grid">
      <div
        v-for="interaction in interactions"
        :key="interaction.id"
        class="legend-item"
      >
        <span
          class="legend-color"
          :style="{ backgroundColor: getInteractionBaseColor(interaction.label) }"
        ></span>
        <span class="legend-label">{{ interaction.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { INTERACTION_TYPES } from '../utils/constants'
import { getInteractionBaseColor } from '../utils/chartHelpers'

defineProps({
  title: {
    type: String,
    default: ''
  }
})

const interactions = INTERACTION_TYPES
</script>

<style scoped>
.interaction-legend {
  margin-top: 24px;
  padding: 16px 20px;
  border: 1px solid #e5e5ea;
  border-radius: 16px;
  background: #ffffff;
}

.legend-header {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
}

.legend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #1d1d1f;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.legend-label {
  flex: 1;
}
</style>

