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
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import TooltipIcon from './TooltipIcon.vue'

const emit = defineEmits(['update:settings'])

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      interfaceCutoff: 5.0,
      waterCutoff: 5.0,
      useReduce: false
    })
  }
})

const isExpanded = ref(false)

const settings = reactive({
  interfaceCutoff: props.modelValue.interfaceCutoff ?? 5.0,
  waterCutoff: props.modelValue.waterCutoff ?? 5.0,
  useReduce: props.modelValue.useReduce ?? false
})

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
  max-height: 300px;
}
</style>
