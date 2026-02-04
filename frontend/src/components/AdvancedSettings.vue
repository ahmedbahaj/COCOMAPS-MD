<template>
  <div class="advanced-settings">
    <button 
      type="button"
      class="settings-toggle"
      @click="isExpanded = !isExpanded"
    >
      <span class="toggle-icon" :class="{ expanded: isExpanded }">▸</span>
      Advanced Settings
    </button>
    
    <Transition name="slide">
      <div v-if="isExpanded" class="settings-panel">
        <!-- CoCoMaps Cutoff -->
        <div class="setting-row">
          <div class="setting-label">
            <span>Interface Cutoff</span>
            <TooltipIcon text="Distance cutoff in Ångströms for detecting interface residues between the two chains. Residues within this distance are considered part of the interface." />
          </div>
          <div class="setting-control">
            <input 
              type="number" 
              v-model.number="settings.interfaceCutoff"
              min="1" 
              max="20" 
              step="0.5"
              class="number-input"
            />
            <span class="unit">Å</span>
          </div>
        </div>
        
        <!-- Water Cutoff -->
        <div class="setting-row">
          <div class="setting-label">
            <span>Water Cutoff</span>
            <TooltipIcon text="Distance cutoff in Ångströms for detecting bridging water molecules. Waters within this distance of BOTH chains are included in the analysis." />
          </div>
          <div class="setting-control">
            <input 
              type="number" 
              v-model.number="settings.waterCutoff"
              min="1" 
              max="20" 
              step="0.5"
              class="number-input"
            />
            <span class="unit">Å</span>
          </div>
        </div>
        
        <!-- Use Reduce Toggle -->
        <div class="setting-row">
          <div class="setting-label">
            <span>Use Reduce</span>
            <TooltipIcon text="Enable hydrogen addition preprocessing using the Reduce tool. This adds missing hydrogen atoms to the structure before analysis. Slower but may improve accuracy for structures without hydrogens." />
          </div>
          <div class="setting-control">
            <label class="toggle-switch">
              <input 
                type="checkbox" 
                v-model="settings.useReduce"
              />
              <span class="toggle-slider"></span>
            </label>
            <span class="toggle-label">{{ settings.useReduce ? 'ON' : 'OFF' }}</span>
          </div>
        </div>

        <!-- Frame Selection Section (only shown when > maxFrames) -->
        <template v-if="totalFrames > maxFrames">
          <div class="setting-section-divider"></div>
          <h4 class="setting-section-title">Frame Sampling</h4>
          
          <!-- Step Size -->
          <div class="setting-row">
            <div class="setting-label">
              <span>Step Size</span>
              <TooltipIcon text="Sample every Nth frame from the trajectory. A step size of 2 means every other frame (1, 3, 5, ...). Disabled when using custom interval." />
            </div>
            <div class="setting-control">
              <input 
                type="number" 
                v-model.number="settings.frameStep"
                min="1" 
                :max="Math.ceil(totalFrames / 2)"
                :disabled="settings.useCustomInterval"
                class="number-input"
                :class="{ disabled: settings.useCustomInterval }"
              />
              <span class="unit">frames</span>
            </div>
          </div>

          <!-- Effective Frames Display -->
          <div class="setting-row info-row" v-if="!settings.useCustomInterval">
            <div class="setting-label">
              <span>Frames to Analyze</span>
            </div>
            <div class="setting-value">
              {{ Math.ceil(totalFrames / (settings.frameStep || 1)) }} frames (1 to {{ totalFrames }})
            </div>
          </div>

          <!-- Use Custom Interval Toggle -->
          <div class="setting-row">
            <div class="setting-label">
              <span>Use Custom Interval</span>
              <TooltipIcon text="Switch to selecting a specific contiguous range of frames instead of sampling the entire trajectory." />
            </div>
            <div class="setting-control">
              <label class="toggle-switch">
                <input 
                  type="checkbox" 
                  v-model="settings.useCustomInterval"
                />
                <span class="toggle-slider"></span>
              </label>
              <span class="toggle-label">{{ settings.useCustomInterval ? 'ON' : 'OFF' }}</span>
            </div>
          </div>

          <!-- Frame Interval Selector (shown when custom interval is enabled) -->
          <div v-if="settings.useCustomInterval" class="interval-selector-wrapper">
            <FrameIntervalSelector
              :totalFrames="totalFrames"
              :maxFrames="maxFrames"
              v-model="frameInterval"
            />
          </div>
        </template>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import TooltipIcon from './TooltipIcon.vue'
import FrameIntervalSelector from './FrameIntervalSelector.vue'

const emit = defineEmits(['update:settings'])

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      interfaceCutoff: 6.0,
      waterCutoff: 5.0,
      useReduce: false,
      frameStep: 1,
      useCustomInterval: false,
      startFrame: 1,
      endFrame: 50
    })
  },
  totalFrames: {
    type: Number,
    default: 0
  },
  maxFrames: {
    type: Number,
    default: 50
  }
})

const isExpanded = ref(false)

const settings = reactive({
  interfaceCutoff: props.modelValue.interfaceCutoff ?? 6.0,
  waterCutoff: props.modelValue.waterCutoff ?? 5.0,
  useReduce: props.modelValue.useReduce ?? false,
  frameStep: props.modelValue.frameStep ?? 1,
  useCustomInterval: props.modelValue.useCustomInterval ?? false,
  startFrame: props.modelValue.startFrame ?? 1,
  endFrame: props.modelValue.endFrame ?? 50
})

// Frame interval for FrameIntervalSelector v-model
const frameInterval = ref({
  startFrame: settings.startFrame,
  endFrame: Math.min(settings.endFrame, props.maxFrames)
})

// Sync frameInterval changes back to settings
watch(frameInterval, (newVal) => {
  settings.startFrame = newVal.startFrame
  settings.endFrame = newVal.endFrame
}, { deep: true })

// Watch for external settings updates (e.g., from parent)
watch(() => props.modelValue, (newVal) => {
  if (newVal.frameStep !== undefined) settings.frameStep = newVal.frameStep
  if (newVal.useCustomInterval !== undefined) settings.useCustomInterval = newVal.useCustomInterval
  if (newVal.startFrame !== undefined) settings.startFrame = newVal.startFrame
  if (newVal.endFrame !== undefined) settings.endFrame = newVal.endFrame
}, { deep: true })

watch(settings, (newSettings) => {
  emit('update:settings', { ...newSettings })
}, { deep: true })
</script>

<style scoped>
.advanced-settings {
  margin-top: 24px;
}

.settings-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  padding: 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  cursor: pointer;
  font-family: inherit;
  transition: color 0.15s ease;
}

.settings-toggle:hover {
  color: #0066cc;
}

.toggle-icon {
  font-size: 12px;
  transition: transform 0.2s ease;
}

.toggle-icon.expanded {
  transform: rotate(90deg);
}

.settings-panel {
  background: #f5f5f7;
  border-radius: 12px;
  padding: 20px 24px;
  margin-top: 8px;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #e8e8ed;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
}

.setting-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.number-input {
  width: 80px;
  padding: 8px 12px;
  font-size: 15px;
  font-weight: 500;
  text-align: right;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  background: #ffffff;
  font-family: inherit;
  transition: all 0.15s ease;
}

.number-input:focus {
  outline: none;
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.unit {
  font-size: 15px;
  font-weight: 500;
  color: #6e6e73;
  min-width: 20px;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 28px;
  margin: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #d2d2d7;
  border-radius: 28px;
  transition: all 0.3s ease;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 22px;
  width: 22px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #34c759;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 14px;
  font-weight: 600;
  color: #6e6e73;
  min-width: 32px;
}

/* Transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  margin-top: 0;
}

.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 800px;
}

/* Frame Sampling Section */
.setting-section-divider {
  height: 1px;
  background: #d2d2d7;
  margin: 16px 0;
}

.setting-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 12px 0;
}

.info-row {
  background: #f0f7ff;
  border-radius: 8px;
  padding: 10px 14px;
  margin: -4px 0 8px 0;
}

.setting-value {
  font-size: 14px;
  font-weight: 600;
  color: #0066cc;
}

.number-input.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.interval-selector-wrapper {
  margin-top: 12px;
}

.interval-selector-wrapper :deep(.frame-selector) {
  margin-top: 0;
  background: transparent;
  border: none;
  padding: 0;
}

.interval-selector-wrapper :deep(.selector-title),
.interval-selector-wrapper :deep(.selector-description) {
  display: none;
}
</style>
