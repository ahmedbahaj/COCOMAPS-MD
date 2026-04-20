<template>
  <div class="sidebar-wrapper">
    <!-- Sidebar Overlay -->
    <div class="sidebar-overlay" v-if="isOpen" @click="$emit('close')"></div>

    <!-- Sidebar -->
    <aside class="sidebar" :class="{ open: isOpen }">
    <div class="sidebar-header">
      <span class="sidebar-title">Jobs</span>
      <button class="close-sidebar" @click="$emit('close')">×</button>
    </div>
    
    <div v-if="systemsStore.isLoading" class="loading">Loading Jobs...</div>
    
    <div v-else class="systems-list">
      <div
        v-for="system in userSystems"
        :key="system.id"
        :class="['system-item', { active: systemsStore.currentSystem?.id === system.id }]"
        @click="selectSystem(system.id)"
      >
        <div class="system-name">{{ system.name }}</div>
        <div class="system-frames">{{ system.frames }} frames</div>
      </div>
    </div>
    </aside>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSystemsStore } from '../../stores/systemsStore'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'select-system'])

const systemsStore = useSystemsStore()
const router = useRouter()

const userSystems = computed(() => systemsStore.systems.filter(s => !s.isExample))

const selectSystem = async (systemId) => {
  await systemsStore.setCurrentSystem(systemId)

  const system = systemsStore.systems.find(s => s.id === systemId)
  if (system && system.jobId) {
    router.push({ name: 'Analysis', params: { jobId: system.jobId } })
  }

  emit('select-system', systemId)
  emit('close')
}
</script>

<style scoped>
/* Sidebar Overlay */
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 200;
}

/* Sidebar */
.sidebar {
  position: fixed;
  left: -380px;
  top: 0;
  width: 380px;
  height: 100vh;
  background: #ffffff;
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.1);
  padding: 24px;
  overflow-y: auto;
  z-index: 300;
  transition: left 0.3s ease;
}

.sidebar.open {
  left: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e8e8ed;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-sidebar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
  border: none;
  border-radius: 10px;
  font-size: 24px;
  color: #6e6e73;
  cursor: pointer;
  transition: all 0.15s ease;
}

.close-sidebar:hover {
  background: #e8e8ed;
  color: #1d1d1f;
}

.loading {
  padding: 20px;
  text-align: center;
  color: #6e6e73;
}

.systems-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.system-item {
  padding: 16px 18px;
  border-radius: 12px;
  background: #f5f5f7;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.system-item:hover {
  background: #e8e8ed;
}

.system-item.active {
  background: #1d1d1f;
  color: #ffffff;
  border-color: #1d1d1f;
}

.system-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.system-frames {
  font-size: 13px;
  color: #6e6e73;
}

.system-item.active .system-frames {
  color: #a1a1a6;
}

@media (max-width: 480px) {
  .sidebar {
    width: 100%;
    left: -100%;
  }
}
</style>
