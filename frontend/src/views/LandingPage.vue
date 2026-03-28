<template>
  <div class="landing-page">
    <!-- Navigation -->
    <nav class="nav-bar">
      <div class="nav-left">
        <router-link to="/" class="nav-logo">Trajectory Analysis</router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link active">Home</router-link>
          <router-link to="/jobs" class="nav-link">Jobs</router-link>
          <router-link to="/about" class="nav-link">About</router-link>
          <router-link to="/references" class="nav-link">References</router-link>
        </div>
      </div>
      <div class="nav-right"></div>
    </nav>

    <!-- Hero Section -->
    <header class="hero">
      <div class="hero-content">
        <div class="logo-container">
          <div class="logo-icon">
            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="16" cy="24" r="10" stroke="currentColor" stroke-width="2.5" fill="none"/>
              <circle cx="32" cy="24" r="10" stroke="currentColor" stroke-width="2.5" fill="none"/>
              <circle cx="24" cy="24" r="4" fill="currentColor"/>
            </svg>
          </div>
        </div>
        <h1 class="title">Trajectory Analysis</h1>
        <p class="subtitle">MD Trajectory Analysis</p>
        <p class="description">
          A comprehensive tool for analyzing protein-protein interface interactions across 
          molecular dynamics trajectories. Upload a multi-model PDB file, select chains, 
          and explore conserved interactions with detailed visualizations including 
          contact maps, interaction trends, and residue-level analysis.
        </p>
      </div>
    </header>


    <!-- Main Content -->
    <main class="content">
      <div class="container">
        <!-- Upload Section -->
        <section class="upload-section" v-if="!uploadedFile">
          <div 
            class="upload-dropzone"
            :class="{ 
              'dragging': isDragging,
              'uploading': isUploading 
            }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <input 
              ref="fileInput"
              type="file" 
              accept=".pdb"
              @change="handleFileSelect"
              hidden
            />
            <div class="dropzone-content" v-if="!isUploading">
              <div class="dropzone-icon">
                <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 32L24 22L34 32" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M24 22V42" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                  <path d="M40 32V38C40 40.2091 38.2091 42 36 42H12C9.79086 42 8 40.2091 8 38V32" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                  <path d="M24 6L24 16" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                  <circle cx="24" cy="6" r="2" fill="currentColor"/>
                </svg>
              </div>
              <p class="dropzone-text">
                <strong>Drop your PDB file here</strong>
                <span>or click to browse</span>
              </p>
              <p class="dropzone-hint">.pdb files supported</p>
            </div>
            <div class="dropzone-loading" v-else>
              <div class="spinner"></div>
              <p>Reading structure...</p>
            </div>
          </div>
          
          <!-- View Existing Systems Button -->
          <div class="existing-systems">
            <span class="divider-text">or</span>
            <button class="view-systems-btn" @click="viewExistingSystems">
              View Existing Jobs
            </button>
          </div>
        </section>

        <!-- Configuration Section -->
        <section class="config-section" v-if="uploadedFile">
          <!-- Uploaded File Display -->
          <div class="file-card">
            <div class="file-info">
              <div class="file-icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div class="file-details">
                <span class="file-name">{{ uploadedFile.name }}</span>
                <span class="file-meta">{{ formatFileSize(uploadedFile.size) }} • {{ detectedChains.length }} chains • {{ detectedFrames }} frames</span>
              </div>
            </div>
            <button class="change-file-btn" @click="resetUpload">
              Change
            </button>
          </div>

          <!-- Chain Selector -->
          <ChainSelector 
            :chains="detectedChains" 
            v-model="chainSelection"
          />

          <!-- Frame Sampling Info (shown when > 50 frames) -->
          <p v-if="detectedFrames > 50" class="frame-sampling-note">
            Analyzing {{ effectiveFrameCount }} frames from 1 to {{ detectedFrames }} with step size {{ defaultStepSize }}.
          </p>

          <!-- Advanced Settings -->
          <AdvancedSettings 
            :modelValue="advancedSettings" 
            @update:settings="advancedSettings = $event"
            :defaultJobName="pdbStem"
            :totalFrames="detectedFrames"
            :maxFrames="50"
          />

          <!-- Start Analysis Button -->
          <div class="action-section">
            <button 
              class="start-btn"
              :disabled="!canStartAnalysis || isProcessing"
              @click="startAnalysis"
            >
              <span v-if="!isProcessing">Start Analysis</span>
              <span v-else class="btn-loading">
                <span class="btn-spinner"></span>
                Processing...
              </span>
            </button>
          </div>

          <!-- Processing Status -->
          <div v-if="processingStatus" class="status-card">
            <div class="status-header">
              <span class="status-label">{{ processingStatus.step_label || processingStatus.status }}</span>
              <span class="status-progress">{{ processingStatus.progress }}%</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: processingStatus.progress + '%' }"
              ></div>
            </div>
            <p v-if="processingStatus.status === 'failed'" class="status-error">
              {{ processingStatus.error }}
            </p>
          </div>
        </section>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ChainSelector from '../components/ChainSelector.vue'
import AdvancedSettings from '../components/AdvancedSettings.vue'
import AppFooter from '../components/AppFooter.vue'
import api from '../services/api'
import { useDataStore } from '../stores/dataStore'

const router = useRouter()
const route = useRoute()
const dataStore = useDataStore()
const fileInput = ref(null)

// Upload state
const isDragging = ref(false)
const isUploading = ref(false)
const uploadedFile = ref(null)
const detectedChains = ref([])
const detectedFrames = ref(0)

// Configuration state
const chainSelection = ref({ chain1: '', chain2: '', isValid: false })
const advancedSettings = ref({
  jobName: '',
  email: '',
  interfaceCutoff: 5.0,
  waterCutoff: 5.0,
  useReduce: false,
  timeUnit: '',
  // Frame selection settings
  frameStep: 1,
  useCustomInterval: false,
  startFrame: 1,
  endFrame: 50
})

// PDB file stem (filename without .pdb) for default job name
const pdbStem = computed(() => {
  const file = uploadedFile.value
  if (!file || !file.name) return ''
  return file.name.replace(/\.pdb$/i, '')
})

// Computed: default step size to cover full trajectory in ~50 frames
const defaultStepSize = computed(() => {
  if (detectedFrames.value <= 50) return 1
  return Math.floor(detectedFrames.value / 50) || 1
})

// Computed: effective frame count with current step size
const effectiveFrameCount = computed(() => {
  const step = advancedSettings.value.useCustomInterval 
    ? 1 
    : (advancedSettings.value.frameStep || defaultStepSize.value)
  return Math.ceil(detectedFrames.value / step)
})

// Processing state
const isProcessing = ref(false)
const processingStatus = ref(null)
const activeJobId = ref(null)
let statusPollInterval = null

const canStartAnalysis = computed(() => {
  return uploadedFile.value &&
         chainSelection.value.isValid &&
         detectedChains.value.length >= 2
})

// On mount: check for active job in localStorage or query param
onMounted(async () => {
  const jobIdFromQuery = route.query.job
  const savedJobId = localStorage.getItem('activeJobId')
  const jobId = jobIdFromQuery || savedJobId

  if (jobId) {
    activeJobId.value = jobId
    isProcessing.value = true
    processingStatus.value = { status: 'resuming', progress: 0, step_label: 'Resuming job…' }

    // Restore UI state from the job record so the file card and chain info
    // show the correct values instead of zeros when navigating back.
    try {
      const jobStatus = await api.getStatus(jobId)
      const pdbName = jobStatus.pdb_name || jobId
      const chain1 = jobStatus.chain1 || 'A'
      const chain2 = jobStatus.chain2 || 'B'

      // endFrame from the job record tells us how many frames were submitted
      // (frames field starts at 0 and is only set on completion)
      const endFrame = typeof jobStatus.endFrame === 'number' ? jobStatus.endFrame : jobStatus.frames || 0

      uploadedFile.value = { name: pdbName + '.pdb', size: 0 }
      detectedChains.value = [chain1, chain2]
      detectedFrames.value = endFrame
      chainSelection.value = { chain1, chain2, isValid: true }
    } catch {
      // Fallback: show placeholder so the config section at least renders
      uploadedFile.value = { name: jobId, size: 0 }
    }

    pollStatus(jobId)
  }
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const viewExistingSystems = () => {
  router.push({ name: 'Jobs' })
}

const handleDrop = (event) => {
  isDragging.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

const processFile = async (file) => {
  if (!file.name.toLowerCase().endsWith('.pdb')) {
    alert('Please upload a PDB file (.pdb extension)')
    return
  }

  isUploading.value = true
  uploadedFile.value = file

  try {
    // Read file content to detect chains and frames
    const content = await readFileContent(file)
    const chains = detectChainsFromPDB(content)
    const frames = detectFramesFromPDB(content)
    detectedChains.value = chains
    detectedFrames.value = frames

    if (chains.length < 2) {
      alert('The PDB file must contain at least 2 chains for interface analysis.')
      resetUpload()
      return
    }
  } catch (error) {
    console.error('Error reading file:', error)
    alert('Error reading PDB file. Please try again.')
    resetUpload()
  } finally {
    isUploading.value = false
  }
}

const readFileContent = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = (e) => reject(e)
    reader.readAsText(file)
  })
}

const detectChainsFromPDB = (content) => {
  const chains = new Set()
  const lines = content.split('\n')
  
  for (const line of lines) {
    if (line.startsWith('ATOM') || line.startsWith('HETATM')) {
      // Chain ID is at position 21 (0-indexed)
      const chainId = line.charAt(21).trim()
      if (chainId) {
        chains.add(chainId)
      }
    }
  }
  
  return Array.from(chains).sort()
}

const detectFramesFromPDB = (content) => {
  // Count MODEL records to determine number of frames
  // If no MODEL records exist, it's a single frame structure
  const modelMatches = content.match(/^MODEL\s/gm)
  return modelMatches ? modelMatches.length : 1
}

const resetUpload = () => {
  uploadedFile.value = null
  detectedChains.value = []
  detectedFrames.value = 0
  chainSelection.value = { chain1: '', chain2: '', isValid: false }
  advancedSettings.value = {
    jobName: '',
    email: '',
    interfaceCutoff: 5.0,
    waterCutoff: 5.0,
    useReduce: false,
    timeUnit: '',
    frameStep: 1,
    useCustomInterval: false,
    startFrame: 1,
    endFrame: 50
  }
  processingStatus.value = null
  activeJobId.value = null
  localStorage.removeItem('activeJobId')
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const startAnalysis = async () => {
  if (!canStartAnalysis.value) return

  isProcessing.value = true
  processingStatus.value = { status: 'uploading', progress: 0, step_label: 'Uploading file…' }

  try {
    // Build options object
    const options = {
      jobName: (advancedSettings.value.jobName || pdbStem.value || '').trim() || pdbStem.value,
      email: (advancedSettings.value.email || '').trim(),
      chain1: chainSelection.value.chain1,
      chain2: chainSelection.value.chain2,
      useReduce: advancedSettings.value.useReduce,
      interfaceCutoff: advancedSettings.value.interfaceCutoff,
      waterCutoff: advancedSettings.value.waterCutoff
    }

    // Always send frame range so backend processes the correct number of frames
    if (detectedFrames.value > 50) {
      if (advancedSettings.value.useCustomInterval) {
        options.startFrame = advancedSettings.value.startFrame
        options.endFrame = advancedSettings.value.endFrame
      } else {
        options.startFrame = 1
        options.endFrame = detectedFrames.value
        options.frameStep = advancedSettings.value.frameStep || defaultStepSize.value
      }
    } else {
      // ≤50 frames: send full range explicitly so backend doesn't rely on defaults
      options.startFrame = 1
      options.endFrame = detectedFrames.value
      options.frameStep = 1
    }

    // Upload file using the proper API method
    const result = await api.uploadFileWithOptions(
      uploadedFile.value,
      options,
      (percent) => {
        processingStatus.value = { status: 'uploading', progress: percent, step_label: 'Uploading file…' }
      }
    )

    if (result.success) {
      const jobId = result.job_id
      activeJobId.value = jobId
      // Persist job ID so we can resume on refresh
      localStorage.setItem('activeJobId', jobId)
      // Start polling for status
      pollStatus(jobId)
    } else {
      throw new Error(result.error || 'Upload failed')
    }
  } catch (error) {
    console.error('Upload error:', error)
    processingStatus.value = { 
      status: 'failed', 
      progress: 0,
      step_label: 'Failed',
      error: error.message || 'Failed to upload file'
    }
    isProcessing.value = false
  }
}

const pollStatus = (jobId) => {
  statusPollInterval = setInterval(async () => {
    try {
      const status = await api.getStatus(jobId)
      processingStatus.value = status

      if (status.status === 'completed') {
        clearInterval(statusPollInterval)
        isProcessing.value = false
        activeJobId.value = null
        localStorage.removeItem('activeJobId')
        // Store timeUnit in dataStore for charts to use
        dataStore.setTimeUnit(advancedSettings.value.timeUnit)

        // Prefer public analysis jobId from backend (canonical); else resolve from systems
        const analysisJobId = status.analysis_job_id
        if (analysisJobId) {
          router.push({ name: 'Analysis', params: { jobId: analysisJobId } })
        } else {
          try {
            const systems = await api.getSystems()
            const systemId = status.pdb_name || jobId
            const system = systems.find(s => s.id === systemId)
            if (system && system.jobId) {
              router.push({ name: 'Analysis', params: { jobId: system.jobId } })
            } else {
              router.push({ name: 'Jobs' })
            }
          } catch (e) {
            console.error('Failed to resolve system/jobId after completion:', e)
            router.push({ name: 'Jobs' })
          }
        }
      } else if (status.status === 'failed') {
        clearInterval(statusPollInterval)
        isProcessing.value = false
        activeJobId.value = null
        localStorage.removeItem('activeJobId')
      }
    } catch (error) {
      console.error('Status poll error:', error)
    }
  }, 2000)
}

// Cleanup on unmount
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (statusPollInterval) {
    clearInterval(statusPollInterval)
  }
})

// Sync default step size when frames change
watch(defaultStepSize, (newStep) => {
  // Only update if not using custom interval and step hasn't been manually changed
  if (!advancedSettings.value.useCustomInterval) {
    advancedSettings.value.frameStep = newStep
  }
}, { immediate: true })
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f5f5f7 0%, #ffffff 100%);
}

/* Navigation */
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 40px;
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

.nav-logo {
  font-size: 20px;
  font-weight: 700;
  color: #1d1d1f;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 32px;
  margin-left: 32px;
}

.nav-link {
  font-size: 15px;
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

.nav-link:hover,
.nav-link.active,
.nav-link.router-link-active {
  color: #1d1d1f;
}

.nav-link.active::after,
.nav-link.router-link-active::after {
  width: 100%;
}

/* Hero Section */
.hero {
  padding: 60px 40px 50px;
  text-align: center;
  background: linear-gradient(180deg, #ffffff 0%, #f5f5f7 100%);
}

.hero-content {
  max-width: 720px;
  margin: 0 auto;
}

.logo-container {
  margin-bottom: 24px;
}

.logo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  color: #1d1d1f;
}

.logo-icon svg {
  width: 64px;
  height: 64px;
}

.title {
  font-size: 48px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.subtitle {
  font-size: 28px;
  font-weight: 500;
  color: #6e6e73;
  margin: 8px 0 0 0;
  letter-spacing: -0.01em;
}

.description {
  font-size: 19px;
  line-height: 1.5;
  color: #6e6e73;
  margin: 24px 0 0 0;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.hero-features {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
  flex-wrap: wrap;
}

.feature-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: #ffffff;
  border: 1px solid #e8e8ed;
  border-radius: 980px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}

.feature-icon {
  font-size: 16px;
}

/* Main Content */
.content {
  flex: 1;
  padding: 0 40px 80px;
}

.container {
  max-width: 680px;
  margin: 0 auto;
}

/* Upload Section */
.upload-section {
  margin-top: -20px;
}

.upload-dropzone {
  background: #ffffff;
  border: 2px dashed #d2d2d7;
  border-radius: 20px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-dropzone:hover {
  border-color: #0066cc;
  background: #f8faff;
}

.upload-dropzone.dragging {
  border-color: #0066cc;
  background: #f0f7ff;
  border-style: solid;
}

.upload-dropzone.uploading {
  cursor: wait;
  pointer-events: none;
}

.dropzone-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  color: #6e6e73;
}

.dropzone-icon svg {
  width: 100%;
  height: 100%;
}

.dropzone-text {
  margin: 0;
  font-size: 19px;
  color: #1d1d1f;
}

.dropzone-text strong {
  display: block;
  margin-bottom: 4px;
}

.dropzone-text span {
  color: #6e6e73;
  font-size: 17px;
}

.dropzone-hint {
  margin: 12px 0 0;
  font-size: 14px;
  color: #86868b;
}

.dropzone-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #6e6e73;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e8e8ed;
  border-top-color: #0066cc;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Existing Systems */
.existing-systems {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.divider-text {
  font-size: 14px;
  color: #86868b;
  text-transform: lowercase;
}

.view-systems-btn {
  padding: 12px 28px;
  background: transparent;
  color: #0066cc;
  border: 1px solid #0066cc;
  border-radius: 980px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s ease;
}

.view-systems-btn:hover {
  background: #0066cc;
  color: #ffffff;
}

/* Config Section */
.config-section {
  margin-top: 0;
}

.file-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e8e8ed;
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 0;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.file-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
  border-radius: 10px;
  color: #1d1d1f;
}

.file-icon svg {
  width: 24px;
  height: 24px;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.file-meta {
  font-size: 14px;
  color: #6e6e73;
}

.change-file-btn {
  padding: 10px 20px;
  background: #f5f5f7;
  border: none;
  border-radius: 980px;
  font-size: 15px;
  font-weight: 500;
  color: #1d1d1f;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s ease;
}

.change-file-btn:hover {
  background: #e8e8ed;
}

/* Frame Sampling Note */
.frame-sampling-note {
  font-size: 14px;
  color: #86868b;
  margin: 16px 0 0 0;
  text-align: center;
}

/* Action Section */
.action-section {
  margin-top: 32px;
  text-align: center;
}

.start-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 200px;
  padding: 16px 40px;
  background: #1d1d1f;
  color: #ffffff;
  border: none;
  border-radius: 980px;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s ease;
}

.start-btn:hover:not(:disabled) {
  background: #000000;
  transform: scale(1.02);
}

.start-btn:disabled {
  background: #d2d2d7;
  color: #86868b;
  cursor: not-allowed;
  transform: none;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Status Card */
.status-card {
  margin-top: 24px;
  background: #ffffff;
  border: 1px solid #e8e8ed;
  border-radius: 16px;
  padding: 20px 24px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-label {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  text-transform: capitalize;
}

.status-progress {
  font-size: 15px;
  font-weight: 600;
  color: #0066cc;
}

.progress-bar {
  height: 8px;
  background: #e8e8ed;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #0066cc 0%, #00a2ff 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.status-error {
  margin: 12px 0 0;
  padding: 12px;
  background: #fff2f2;
  border-radius: 8px;
  color: #d32f2f;
  font-size: 14px;
}

/* Responsive */
@media (max-width: 768px) {
  .nav-bar {
    padding: 16px 24px;
  }

  .nav-links {
    gap: 20px;
  }

  .hero {
    padding: 40px 24px 32px;
  }

  .title {
    font-size: 32px;
  }

  .subtitle {
    font-size: 20px;
  }

  .description {
    font-size: 16px;
  }

  .hero-features {
    gap: 10px;
  }

  .feature-tag {
    padding: 8px 14px;
    font-size: 13px;
  }

  .content {
    padding: 0 24px 60px;
  }

  .upload-dropzone {
    padding: 40px 24px;
  }
}
</style>
