<template>
  <div class="home">
    <!-- System Sidebar -->
    <SystemSidebar :isOpen="sidebarOpen" @close="$emit('toggle-sidebar')" />

    <!-- Main Content -->
    <div class="main-content">
      <div class="container">
        <h1 v-if="dataStore.currentSystem">{{ dataStore.currentSystem.name }}</h1>
        <h1 v-else>Select a System</h1>
        <p class="subtitle" v-if="dataStore.currentSystem">
          Chain {{ dataStore.currentSystem.chain1 || 'A' }} ↔ Chain {{ dataStore.currentSystem.chain2 || 'B' }} Residue Interactions Across {{ dataStore.currentSystem.frames }} Frames
        </p>
        <p class="subtitle" v-else>
          Use the menu to select a system for analysis
        </p>

        <ChartSelector />
        <div class="analysis-card">
          <ChartContainer />
          <ControlsPanel />
        </div>
        <StatsPanel v-if="dataStore.currentSystem" />
        <ConservationAnalysis v-if="dataStore.currentSystem" />
      </div>
    </div>

    <UploadModal ref="uploadModal" />

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDataStore } from '../stores/dataStore'
import ChartSelector from '../components/analysis/ChartSelector.vue'
import ControlsPanel from '../components/analysis/ControlsPanel.vue'
import ChartContainer from '../components/analysis/ChartContainer.vue'
import StatsPanel from '../components/analysis/StatsPanel.vue'
import ConservationAnalysis from '../components/analysis/ConservationAnalysis.vue'
import UploadModal from '../components/analysis/UploadModal.vue'
import SystemSidebar from '../components/analysis/SystemSidebar.vue'
import AppFooter from '../components/layout/AppFooter.vue'

const props = defineProps({
  sidebarOpen: { type: Boolean, default: false }
})
defineEmits(['toggle-sidebar'])

const dataStore = useDataStore()
const route = useRoute()
const router = useRouter()
const uploadModal = ref(null)

onMounted(async () => {
  await dataStore.loadSystems()

  const jobId = route.params.jobId

  if (jobId && dataStore.systems.length > 0) {
    const systemForJob = dataStore.systems.find(s => s.jobId === jobId)
    if (systemForJob) {
      await dataStore.setCurrentSystem(systemForJob.id)
      return
    }
  }

  // Fallback: set first system as default if available
  if (dataStore.systems.length > 0 && !dataStore.currentSystem) {
    const first = dataStore.systems[0]
    await dataStore.setCurrentSystem(first.id)
    if (first.jobId) {
      router.replace({ name: 'Analysis', params: { jobId: first.jobId } })
    }
  }
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Main Content */
.main-content {
  flex: 1;
}

.container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 40px;
}

h1 {
  font-size: 48px;
  line-height: 1.1;
  font-weight: 600;
  letter-spacing: -0.02em;
  text-align: center;
  margin-bottom: 12px;
  color: #1d1d1f;
}

.subtitle {
  font-size: 20px;
  line-height: 1.4;
  font-weight: 400;
  text-align: center;
  color: #6e6e73;
  margin-bottom: 40px;
}

.analysis-card {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  margin-bottom: 32px;
}

@media (max-width: 768px) {
  h1 {
    font-size: 32px;
  }

  .container {
    padding: 24px;
  }
}
</style>
