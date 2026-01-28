<template>
  <div class="frame-selector" v-if="totalFrames > maxFrames">
    <h3 class="selector-title">Select Frame Interval</h3>
    <p class="selector-description">
      Your trajectory has {{ totalFrames }} frames. Select up to {{ maxFrames }} frames for analysis.
    </p>
    
    <div class="slider-container">
      <div class="slider-labels">
        <span>Frame {{ startFrame }}</span>
        <span class="frame-count">{{ selectedCount }} frames selected</span>
        <span>Frame {{ endFrame }}</span>
      </div>
      
      <div class="range-slider">
        <input 
          type="range" 
          :min="1" 
          :max="totalFrames"
          v-model.number="startFrame"
          class="slider slider-start"
          @input="handleStartChange"
        />
        <input 
          type="range" 
          :min="1" 
          :max="totalFrames"
          v-model.number="endFrame"
          class="slider slider-end"
          @input="handleEndChange"
        />
        <div class="slider-track">
          <div 
            class="slider-range" 
            :style="rangeStyle"
          ></div>
        </div>
      </div>
      
      <div class="frame-inputs">
        <div class="input-group">
          <label>Start</label>
          <input 
            type="number" 
            v-model.number="startFrame"
            :min="1"
            :max="totalFrames"
            @change="handleStartChange"
          />
        </div>
        <div class="input-group">
          <label>End</label>
          <input 
            type="number" 
            v-model.number="endFrame"
            :min="1"
            :max="totalFrames"
            @change="handleEndChange"
          />
        </div>
      </div>
    </div>
    
    <p v-if="selectedCount > maxFrames" class="warning-message">
      ⚠️ Maximum {{ maxFrames }} frames allowed. Range will be adjusted.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  totalFrames: {
    type: Number,
    required: true
  },
  maxFrames: {
    type: Number,
    default: 50
  },
  modelValue: {
    type: Object,
    default: () => ({ startFrame: 1, endFrame: 50 })
  }
})

const emit = defineEmits(['update:modelValue'])

const startFrame = ref(props.modelValue.startFrame || 1)
const endFrame = ref(Math.min(props.modelValue.endFrame || props.maxFrames, props.totalFrames))

const selectedCount = computed(() => {
  return Math.max(0, endFrame.value - startFrame.value + 1)
})

const rangeStyle = computed(() => {
  const start = ((startFrame.value - 1) / (props.totalFrames - 1)) * 100
  const end = ((endFrame.value - 1) / (props.totalFrames - 1)) * 100
  return {
    left: `${start}%`,
    width: `${end - start}%`
  }
})

const handleStartChange = () => {
  // Ensure start <= end
  if (startFrame.value > endFrame.value) {
    startFrame.value = endFrame.value
  }
  // Ensure start >= 1
  if (startFrame.value < 1) {
    startFrame.value = 1
  }
  // Auto-adjust end if range exceeds max
  if (endFrame.value - startFrame.value + 1 > props.maxFrames) {
    endFrame.value = startFrame.value + props.maxFrames - 1
    if (endFrame.value > props.totalFrames) {
      endFrame.value = props.totalFrames
      startFrame.value = Math.max(1, endFrame.value - props.maxFrames + 1)
    }
  }
  emitValue()
}

const handleEndChange = () => {
  // Ensure end >= start
  if (endFrame.value < startFrame.value) {
    endFrame.value = startFrame.value
  }
  // Ensure end <= totalFrames
  if (endFrame.value > props.totalFrames) {
    endFrame.value = props.totalFrames
  }
  // Auto-adjust start if range exceeds max
  if (endFrame.value - startFrame.value + 1 > props.maxFrames) {
    startFrame.value = endFrame.value - props.maxFrames + 1
    if (startFrame.value < 1) {
      startFrame.value = 1
      endFrame.value = Math.min(props.totalFrames, props.maxFrames)
    }
  }
  emitValue()
}

const emitValue = () => {
  emit('update:modelValue', {
    startFrame: startFrame.value,
    endFrame: endFrame.value
  })
}

// Initialize based on total frames
watch(() => props.totalFrames, (newTotal) => {
  if (newTotal > 0) {
    startFrame.value = 1
    endFrame.value = Math.min(props.maxFrames, newTotal)
    emitValue()
  }
}, { immediate: true })
</script>

<style scoped>
.frame-selector {
  background: #fff8e6;
  border: 1px solid #f5d89a;
  border-radius: 16px;
  padding: 28px 32px;
  margin-top: 24px;
}

.selector-title {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.selector-description {
  font-size: 15px;
  color: #6e6e73;
  margin: 0 0 24px 0;
}

.slider-container {
  margin: 0;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: #6e6e73;
}

.frame-count {
  font-weight: 600;
  color: #1d1d1f;
  background: #ffffff;
  padding: 4px 12px;
  border-radius: 980px;
  border: 1px solid #d2d2d7;
}

.range-slider {
  position: relative;
  height: 40px;
  margin-bottom: 20px;
}

.slider {
  position: absolute;
  width: 100%;
  height: 8px;
  top: 50%;
  transform: translateY(-50%);
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  pointer-events: none;
  z-index: 2;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  pointer-events: auto;
  border: 3px solid #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.slider::-moz-range-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  pointer-events: auto;
  border: 3px solid #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.slider-track {
  position: absolute;
  width: 100%;
  height: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: #e8e8ed;
  border-radius: 4px;
  z-index: 1;
}

.slider-range {
  position: absolute;
  height: 100%;
  background: #1d1d1f;
  border-radius: 4px;
}

.frame-inputs {
  display: flex;
  justify-content: space-between;
  gap: 24px;
}

.input-group {
  flex: 1;
  max-width: 120px;
}

.input-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.input-group input {
  width: 100%;
  padding: 10px 14px;
  font-size: 16px;
  font-weight: 500;
  text-align: center;
  border: 2px solid #d2d2d7;
  border-radius: 10px;
  background: #ffffff;
  font-family: inherit;
}

.input-group input:focus {
  outline: none;
  border-color: #1d1d1f;
}

.warning-message {
  margin: 16px 0 0;
  padding: 10px 14px;
  background: #fff2f2;
  border: 1px solid #ffcdd2;
  border-radius: 8px;
  color: #d32f2f;
  font-size: 14px;
  font-weight: 500;
}
</style>
