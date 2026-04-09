<template>
  <span 
    class="tooltip-icon" 
    @mouseenter="showTooltip" 
    @mouseleave="hideTooltip"
  >
    ⓘ
  </span>
  <Teleport to="body">
    <div 
      v-if="visible" 
      class="global-tooltip"
      :style="{ top: y + 'px', left: x + 'px' }"
    >
      {{ text }}
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  text: {
    type: String,
    required: true
  }
})

const visible = ref(false)
const x = ref(0)
const y = ref(0)

const showTooltip = (event) => {
  const posX = event.clientX + 12
  const posY = event.clientY - 8
  x.value = Math.min(posX, window.innerWidth - 340)
  y.value = posY
  visible.value = true
}

const hideTooltip = () => {
  visible.value = false
}
</script>

<style scoped>
.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  font-size: 14px;
  color: #6e6e73;
  cursor: help;
  transition: color 0.15s ease;
}

.tooltip-icon:hover {
  color: #1d1d1f;
}
</style>

<style>
.global-tooltip {
  position: fixed;
  z-index: 10000;
  max-width: 320px;
  padding: 10px 14px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 13px;
  line-height: 1.4;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  pointer-events: none;
  animation: tooltipFade 0.15s ease-out;
}

@keyframes tooltipFade {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
