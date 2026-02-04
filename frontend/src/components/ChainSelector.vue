<template>
  <div class="chain-selector">
    <h3 class="selector-title">Select Chains for Analysis</h3>
    <p class="selector-description">Choose two different chains to analyze their interface interactions.</p>
    
    <div class="chain-selects">
      <div class="chain-select-group">
        <label for="chain1">Chain 1</label>
        <div class="select-wrapper">
          <select 
            id="chain1" 
            v-model="selectedChain1"
          >
            <option value="" disabled>Select chain</option>
            <option 
              v-for="chain in chain1Options" 
              :key="chain" 
              :value="chain"
            >
              Chain {{ chain }}
            </option>
          </select>
          <span class="select-arrow">▼</span>
        </div>
      </div>
      
      <div class="chain-divider">
        <span class="divider-icon">↔</span>
      </div>
      
      <div class="chain-select-group">
        <label for="chain2">Chain 2</label>
        <div class="select-wrapper">
          <select 
            id="chain2" 
            v-model="selectedChain2"
          >
            <option value="" disabled>Select chain</option>
            <option 
              v-for="chain in chain2Options" 
              :key="chain" 
              :value="chain"
            >
              Chain {{ chain }}
            </option>
          </select>
          <span class="select-arrow">▼</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  chains: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: Object,
    default: () => ({ chain1: '', chain2: '' })
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedChain1 = ref(props.modelValue.chain1 || '')
const selectedChain2 = ref(props.modelValue.chain2 || '')

// Filtered options: exclude the chain selected in the other dropdown
const chain1Options = computed(() => {
  return props.chains.filter(c => c !== selectedChain2.value)
})

const chain2Options = computed(() => {
  return props.chains.filter(c => c !== selectedChain1.value)
})

const isValid = computed(() => {
  return selectedChain1.value && selectedChain2.value && selectedChain1.value !== selectedChain2.value
})

watch([selectedChain1, selectedChain2], () => {
  emit('update:modelValue', {
    chain1: selectedChain1.value,
    chain2: selectedChain2.value,
    isValid: isValid.value
  })
})

// Auto-select first two chains if available
watch(() => props.chains, (newChains) => {
  if (newChains.length >= 2 && !selectedChain1.value && !selectedChain2.value) {
    selectedChain1.value = newChains[0]
    selectedChain2.value = newChains[1]
  } else if (newChains.length === 1 && !selectedChain1.value) {
    selectedChain1.value = newChains[0]
  }
}, { immediate: true })
</script>

<style scoped>
.chain-selector {
  background: #f5f5f7;
  border-radius: 16px;
  padding: 28px 32px;
  margin-top: 32px;
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

.chain-selects {
  display: flex;
  align-items: flex-end;
  gap: 24px;
  justify-content: center;
}

.chain-select-group {
  flex: 1;
  max-width: 200px;
}

.chain-select-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #6e6e73;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.select-wrapper {
  position: relative;
}

.select-wrapper select {
  width: 100%;
  padding: 14px 40px 14px 16px;
  font-size: 17px;
  font-weight: 500;
  color: #1d1d1f;
  background: #ffffff;
  border: 2px solid #d2d2d7;
  border-radius: 12px;
  appearance: none;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s ease;
}

.select-wrapper select:focus {
  outline: none;
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.select-wrapper select.error {
  border-color: #ff3b30;
}

.select-wrapper select.error:focus {
  box-shadow: 0 0 0 3px rgba(255, 59, 48, 0.1);
}

.select-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: #6e6e73;
  pointer-events: none;
}

.chain-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-bottom: 8px;
}

.divider-icon {
  font-size: 24px;
  color: #6e6e73;
}

.error-message {
  margin-top: 16px;
  padding: 12px 16px;
  background: #fff2f2;
  border: 1px solid #ffcdd2;
  border-radius: 8px;
  color: #d32f2f;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
}
</style>
