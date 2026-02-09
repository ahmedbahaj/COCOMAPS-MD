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
      </div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/about" class="nav-link">About</router-link>
        <router-link to="/references" class="nav-link">References</router-link>
      </div>
    </nav>

    <!-- Sidebar Overlay -->
    <div class="sidebar-overlay" v-if="sidebarOpen" @click="toggleSidebar"></div>

    <!-- Sidebar -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <span class="sidebar-title">Systems</span>
        <button class="close-sidebar" @click="toggleSidebar">×</button>
      </div>
      
      <div v-if="dataStore.loading.systems" class="loading">Loading systems...</div>
      
      <div v-else class="systems-list">
        <div
          v-for="system in dataStore.systems"
          :key="system.id"
          :class="['system-item', { active: dataStore.currentSystem?.id === system.id }]"
          @click="selectSystem(system.id)"
        >
          <div class="system-name">{{ system.name }}</div>
          <div class="system-frames">{{ system.frames }} frames</div>
        </div>
      </div>
    </aside>

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
        <ControlsPanel />
        <ChartContainer />
      </div>
    </div>

    <UploadModal ref="uploadModal" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDataStore } from '../stores/dataStore'
import ChartSelector from '../components/ChartSelector.vue'
import ControlsPanel from '../components/ControlsPanel.vue'
import ChartContainer from '../components/ChartContainer.vue'
import UploadModal from '../components/UploadModal.vue'

const dataStore = useDataStore()
const sidebarOpen = ref(false)
const uploadModal = ref(null)

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const selectSystem = async (systemId) => {
  await dataStore.setCurrentSystem(systemId)
  sidebarOpen.value = false
}

const openUploadModal = () => {
  if (uploadModal.value) {
    uploadModal.value.open()
  }
}

onMounted(async () => {
  await dataStore.loadSystems()
  // Set first system as default if available
  if (dataStore.systems.length > 0 && !dataStore.currentSystem) {
    await dataStore.setCurrentSystem(dataStore.systems[0].id)
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
}

.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  transition: color 0.15s ease;
}

.nav-link:hover {
  color: #1d1d1f;
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
  left: -300px;
  top: 0;
  width: 300px;
  height: 100vh;
  background: #ffffff;
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.1);
  padding: 20px;
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
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e8e8ed;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-sidebar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
  border: none;
  border-radius: 8px;
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
  gap: 8px;
}

.system-item {
  padding: 14px 16px;
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
  font-size: 12px;
  color: #6e6e73;
}

.system-item.active .system-frames {
  color: #a1a1a6;
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
