<template>
  <div class="home">
    <!-- Navigation Bar -->
    <nav class="nav-bar">
      <div class="nav-left">
        <button class="hamburger-btn" @click="toggleSidebar" :class="{ active: sidebarOpen }">
          <span></span>
          <span></span>
          <span></span>
        </button>
        <router-link to="/" class="nav-logo">Trajectory Analysis</router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link">Home</router-link>
          <router-link to="/jobs" class="nav-link">Jobs</router-link>
          <router-link to="/about" class="nav-link">About</router-link>
          <router-link to="/references" class="nav-link">References</router-link>
        </div>
      </div>
      <div class="nav-right"></div>
    </nav>

    <!-- System Sidebar -->
    <SystemSidebar :isOpen="sidebarOpen" @close="toggleSidebar" />

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
import ChartSelector from '../components/ChartSelector.vue'
import ControlsPanel from '../components/ControlsPanel.vue'
import ChartContainer from '../components/ChartContainer.vue'
import StatsPanel from '../components/StatsPanel.vue'
import ConservationAnalysis from '../components/ConservationAnalysis.vue'
import UploadModal from '../components/UploadModal.vue'
import SystemSidebar from '../components/SystemSidebar.vue'
import AppFooter from '../components/AppFooter.vue'

const dataStore = useDataStore()
const route = useRoute()
const router = useRouter()
const sidebarOpen = ref(false)
const uploadModal = ref(null)

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const openUploadModal = () => {
  if (uploadModal.value) {
    uploadModal.value.open()
  }
}

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

/* Navigation Bar */
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  padding: 8px;
  background: #f5f5f7;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.hamburger-btn:hover {
  background: #e8e8ed;
}

.hamburger-btn span {
  display: block;
  width: 100%;
  height: 2px;
  background: #1d1d1f;
  border-radius: 1px;
  transition: all 0.2s ease;
}

.hamburger-btn.active span:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}

.hamburger-btn.active span:nth-child(2) {
  opacity: 0;
}

.hamburger-btn.active span:nth-child(3) {
  transform: rotate(-45deg) translate(5px, -5px);
}

.nav-logo {
  font-size: 18px;
  font-weight: 700;
  color: #1d1d1f;
  text-decoration: none;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-left: 32px;
}

.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  transition: color 0.15s ease;
  position: relative;
  padding-bottom: 4px;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: #1d1d1f;
  transition: width 0.15s ease;
}

.nav-link:hover {
  color: #1d1d1f;
}

.nav-link.router-link-active {
  color: #1d1d1f;
}

.nav-link.router-link-active::after {
  width: 100%;
}

.nav-upload-btn {
  padding: 8px 16px;
  background: #1d1d1f;
  color: #ffffff;
  border: none;
  border-radius: 980px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease;
}

.nav-upload-btn:hover {
  background: #000000;
}

/* Main Content */
.main-content {
  flex: 1;
}

.container {
  max-width: 1400px;
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
  .nav-links {
    gap: 16px;
  }

  .nav-link {
    font-size: 13px;
  }

  h1 {
    font-size: 32px;
  }

  .container {
    padding: 24px;
  }
}
</style>
