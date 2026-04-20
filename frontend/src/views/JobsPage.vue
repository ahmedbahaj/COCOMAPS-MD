<template>
  <div class="jobs-page">
    <!-- Header -->
    <header class="page-header">
      <div class="header-content">
        <div class="header-text">
          <h1>Your Jobs</h1>
          <p class="subtitle">Jobs you submit from this browser are listed here. Anyone with a link can still open an analysis by URL.</p>
        </div>
        <router-link to="/" class="submit-job-btn">
          <svg viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 2a.5.5 0 0 1 .5.5v5h5a.5.5 0 0 1 0 1h-5v5a.5.5 0 0 1-1 0v-5h-5a.5.5 0 0 1 0-1h5v-5A.5.5 0 0 1 8 2z"/>
          </svg>
          Submit a new Job
        </router-link>
      </div>
    </header>

    <!-- Main Content -->
    <main class="content">
      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Loading jobs...</p>
      </div>

      <!-- Empty State (no jobs for this browser / no matching rows) -->
      <div v-else-if="allJobs.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="10" width="36" height="28" rx="3"/>
            <path d="M6 18h36"/>
            <circle cx="12" cy="14" r="1.5" fill="currentColor"/>
            <circle cx="17" cy="14" r="1.5" fill="currentColor"/>
            <circle cx="22" cy="14" r="1.5" fill="currentColor"/>
          </svg>
        </div>
        <h2>{{ emptyTitle }}</h2>
        <p>{{ emptyDescription }}</p>
        <router-link to="/" class="start-btn">Get Started</router-link>
      </div>

      <!-- Jobs Table (with search) -->
      <div v-else class="table-wrapper">
        <!-- Search Bar -->
        <div class="table-search">
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input 
              type="text" 
              v-model="searchQuery" 
              placeholder="Search jobs..."
              class="search-input"
            />
            <button v-if="searchQuery" @click="searchQuery = ''" class="clear-search">×</button>
          </div>
        </div>

        <!-- No Results State -->
        <div v-if="filteredJobs.length === 0" class="no-results-state">
          <div class="no-results-icon">
            <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="20" cy="20" r="14"/>
              <path d="M30 30l12 12"/>
            </svg>
          </div>
          <h3>No results found</h3>
          <p>No jobs match "{{ searchQuery }}". Try a different search term.</p>
          <button @click="searchQuery = ''" class="clear-btn">Clear Search</button>
        </div>
        
        <div v-else class="table-container">
        <table class="jobs-table">
          <thead>
            <tr>
              <th class="status-col">Status</th>
              <th @click="sortBy('name')" class="sortable">
                Name
                <span class="sort-icon" :class="{ active: sortColumn === 'name', desc: sortDirection === 'desc' }">
                  <svg viewBox="0 0 12 12"><path d="M6 2l4 4H2z"/></svg>
                </span>
              </th>
              <th @click="sortBy('dateCreated')" class="sortable">
                Date Created
                <span class="sort-icon" :class="{ active: sortColumn === 'dateCreated', desc: sortDirection === 'desc' }">
                  <svg viewBox="0 0 12 12"><path d="M6 2l4 4H2z"/></svg>
                </span>
              </th>
              <th @click="sortBy('frames')" class="sortable">
                Frames
                <span class="sort-icon" :class="{ active: sortColumn === 'frames', desc: sortDirection === 'desc' }">
                  <svg viewBox="0 0 12 12"><path d="M6 2l4 4H2z"/></svg>
                </span>
              </th>
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="job in sortedJobs" 
              :key="job.id"
              @click="openJob(job)"
              class="job-row"
              :class="{ 'is-active': isActiveJob(job) }"
            >
              <td class="status-cell">
                <span class="status-badge" :class="job.status">
                  <!-- Completed -->
                  <svg v-if="job.status === 'ready' || job.status === 'completed'" class="status-icon ready" viewBox="0 0 16 16">
                    <path d="M8 0a8 8 0 1 0 8 8A8 8 0 0 0 8 0zm3.78 5.28l-4.5 5.5a.75.75 0 0 1-1.14.06l-2.25-2.25a.75.75 0 1 1 1.06-1.06l1.64 1.64 3.97-4.86a.75.75 0 0 1 1.22.97z" fill="currentColor"/>
                  </svg>
                  <!-- Failed -->
                  <svg v-else-if="job.status === 'failed'" class="status-icon failed" viewBox="0 0 16 16">
                    <path d="M8 0a8 8 0 1 0 8 8A8 8 0 0 0 8 0zm3.5 10.44a.75.75 0 1 1-1.06 1.06L8 9.06 5.56 11.5A.75.75 0 1 1 4.5 10.44L6.94 8 4.5 5.56A.75.75 0 0 1 5.56 4.5L8 6.94l2.44-2.44a.75.75 0 0 1 1.06 1.06L9.06 8z" fill="currentColor"/>
                  </svg>
                  <!-- Processing (spinner) -->
                  <svg v-else class="status-icon processing" viewBox="0 0 16 16">
                    <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="22" stroke-dashoffset="0">
                      <animateTransform attributeName="transform" type="rotate" from="0 8 8" to="360 8 8" dur="1s" repeatCount="indefinite"/>
                    </circle>
                  </svg>
                </span>
              </td>
              <td class="name-cell">
                <div class="name-wrapper">
                  <span class="job-name">{{ job.name }}</span>
                  <span v-if="job.name !== job.id" class="job-id">{{ job.id }}</span>
                  <!-- Progress bar for active jobs -->
                  <div v-if="isActiveJob(job)" class="inline-progress">
                    <div class="inline-progress-bar">
                      <div class="inline-progress-fill" :style="{ width: (job.progress || 0) + '%' }"></div>
                    </div>
                    <span class="inline-progress-label">{{ job.step_label || job.status }}</span>
                  </div>
                </div>
              </td>
              <td class="date-cell">{{ formatDate(job.dateCreated) }}</td>
              <td class="frames-cell">{{ job.frames || '—' }}</td>
              <td class="actions-cell" @click.stop>
                <button class="action-btn" @click="openRenameModal(job)" title="Rename" v-if="!isActiveJob(job)">
                  <svg viewBox="0 0 16 16" fill="currentColor">
                    <path d="M11.498 2.002a1.5 1.5 0 0 1 2.121 0l.379.379a1.5 1.5 0 0 1 0 2.121l-7.5 7.5a.5.5 0 0 1-.177.118l-3.5 1.5a.5.5 0 0 1-.638-.638l1.5-3.5a.5.5 0 0 1 .118-.177l7.697-7.303zM11.85 3.85l-6.5 6.5-.897 2.093 2.093-.897 6.5-6.5-.696-.696-.5-.5z"/>
                  </svg>
                </button>
                <button class="action-btn open-btn" @click="openJob(job)" :title="isActiveJob(job) ? 'Track Progress' : 'Open'">
                  <svg viewBox="0 0 16 16" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z"/>
                    <path fill-rule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        
        <div class="table-footer">
          <span class="job-count">Showing {{ filteredJobs.length }} of {{ allJobs.length }} jobs</span>
        </div>
        </div>
      </div>
    </main>

    <!-- Rename Modal -->
    <Teleport to="body">
      <div v-if="renameModal.visible" class="modal-overlay" @click.self="closeRenameModal">
        <div class="modal-panel">
          <div class="modal-header">
            <h3>Rename Job</h3>
            <button class="modal-close" @click="closeRenameModal">×</button>
          </div>
          <div class="modal-body">
            <label for="new-name">New Name</label>
            <input 
              id="new-name"
              type="text" 
              v-model="renameModal.newName"
              @keyup.enter="confirmRename"
              placeholder="Enter new name..."
              class="rename-input"
              ref="renameInput"
            />
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="closeRenameModal">Cancel</button>
            <button class="btn-confirm" @click="confirmRename" :disabled="!renameModal.newName.trim()">
              Rename
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSystemsStore } from '../stores/systemsStore'
import api from '../services/api'
import AppFooter from '../components/layout/AppFooter.vue'
import { getSubmittedJobIds, jobRowMatchesSubmitted } from '../utils/cocomapsmdJobIds.js'

const router = useRouter()
const systemsStore = useSystemsStore()

const allJobs = ref([])
const loading = ref(true)
const searchQuery = ref('')
const sortColumn = ref('dateCreated')
const sortDirection = ref('desc')
let jobsPollInterval = null

// Rename modal state
const renameModal = ref({
  visible: false,
  system: null,
  newName: ''
})
const renameInput = ref(null)

// Load on mount
onMounted(async () => {
  await loadAllJobs()
  // Poll for updates if there are active jobs
  startPollingIfNeeded()
})

onUnmounted(() => {
  if (jobsPollInterval) {
    clearInterval(jobsPollInterval)
  }
})

const loadAllJobs = async () => {
  loading.value = true
  try {
    // Fetch both completed systems and active jobs in parallel
    const [systems, jobs] = await Promise.all([
      api.getSystems(),
      api.getJobs().catch(() => [])  // graceful fallback if endpoint not ready
    ])

    // Build a merged list
    const merged = new Map()

    // Index jobs by system_id so we can attach the upload UUID to the
    // corresponding completed-system row (needed for localStorage matching).
    const jobBySystemId = new Map()
    for (const job of jobs) {
      const sid = job.system_id || job.pdb_name
      if (sid) jobBySystemId.set(sid, job)
    }

    // Collect the exact system directory stems for all active (in-progress) jobs
    // so we can suppress the prematurely-detected 'ready' filesystem entry.
    const activeSystemIds = new Set(
      jobs
        .filter(j => !['completed', 'failed'].includes(j.status))
        .map(j => j.system_id || j.pdb_name)
    )

    // Add completed systems, skipping any whose directory is still being
    // written by an active job (avoids the duplicate row problem).
    for (const system of systems) {
      if (activeSystemIds.has(system.id)) continue
      if (system.isExample) continue
      const matchingJob = jobBySystemId.get(system.id)
      merged.set(system.id, {
        id: system.id,
        name: system.name,
        dateCreated: system.dateCreated,
        frames: system.frames,
        status: system.status || 'ready',
        jobId: system.jobId || null,
        job_id: matchingJob ? matchingJob.job_id : null,
        step_label: null,
        progress: 100
      })
    }

    // Overlay active/recent jobs keyed by UUID so multiple concurrent jobs for
    // the same pdb_name each get their own row instead of overriding each other.
    for (const job of jobs) {
      const pdbName = job.pdb_name
      const isActive = !['completed', 'failed'].includes(job.status)

      if (isActive) {
        merged.set(job.job_id, {
          id: job.job_id,
          name: pdbName,
          dateCreated: job.created_at,
          frames: job.frames || 0,
          status: job.status,
          job_id: job.job_id,
          step_label: job.step_label,
          progress: job.progress || 0
        })
      } else if (job.status === 'failed') {
        // Show failed jobs that don't have a completed system entry
        if (!merged.has(pdbName)) {
          merged.set(job.job_id, {
            id: job.job_id,
            name: pdbName,
            dateCreated: job.created_at,
            frames: job.frames || 0,
            status: 'failed',
            job_id: job.job_id,
            step_label: job.step_label,
            progress: job.progress || 0
          })
        }
      } else if (job.status === 'completed') {
        // Attach the upload UUID + public analysis ID to the system row
        const sid = job.system_id || pdbName
        if (sid && merged.has(sid)) {
          const row = merged.get(sid)
          if (job.analysis_job_id) row.jobId = job.analysis_job_id
          if (job.job_id) row.job_id = job.job_id
        }
      }
    }

    const rows = Array.from(merged.values())
    const submitted = new Set(getSubmittedJobIds())
    allJobs.value = rows.filter((job) => jobRowMatchesSubmitted(job, submitted))
  } catch (error) {
    console.error('Failed to load jobs:', error)
    allJobs.value = []
  } finally {
    loading.value = false
  }
}

const startPollingIfNeeded = () => {
  if (jobsPollInterval) clearInterval(jobsPollInterval)

  const hasActive = allJobs.value.some(j => isActiveJob(j))
  if (hasActive) {
    jobsPollInterval = setInterval(async () => {
      await loadAllJobs()
      // Stop polling if no more active jobs
      const stillActive = allJobs.value.some(j => isActiveJob(j))
      if (!stillActive && jobsPollInterval) {
        clearInterval(jobsPollInterval)
        jobsPollInterval = null
      }
    }, 5000)
  }
}

const isActiveJob = (job) => {
  return ['queued', 'splitting', 'analyzing', 'resuming'].includes(job.status)
}

const submittedJobIdCount = computed(() => getSubmittedJobIds().length)

const emptyTitle = computed(() =>
  submittedJobIdCount.value === 0 ? 'No jobs yet' : 'No matching jobs'
)

const emptyDescription = computed(() =>
  submittedJobIdCount.value === 0
    ? 'Submit a trajectory from this browser to see it here. Analysis links stay shareable with anyone.'
    : 'Your saved job IDs did not match any current data on the server. If you cleared browser data or the server was reset, submit again from the home page.'
)

// Filter by search query
const filteredJobs = computed(() => {
  if (!searchQuery.value.trim()) {
    return allJobs.value
  }
  const query = searchQuery.value.toLowerCase()
  return allJobs.value.filter(job => 
    job.name.toLowerCase().includes(query) ||
    job.id.toLowerCase().includes(query)
  )
})

// Sort
const sortedJobs = computed(() => {
  const sorted = [...filteredJobs.value]
  sorted.sort((a, b) => {
    let aVal = a[sortColumn.value]
    let bVal = b[sortColumn.value]
    
    if (sortColumn.value === 'dateCreated') {
      aVal = new Date(aVal || 0).getTime()
      bVal = new Date(bVal || 0).getTime()
    }
    
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = (bVal || '').toLowerCase()
    }
    
    if (aVal < bVal) return sortDirection.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection.value === 'asc' ? 1 : -1
    return 0
  })
  return sorted
})

const sortBy = (column) => {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = column === 'dateCreated' ? 'desc' : 'asc'
  }
}

const formatDate = (isoDate) => {
  if (!isoDate) return '—'
  const date = new Date(isoDate)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Open job: active jobs go to LandingPage with job tracking, completed go to Analysis
const openJob = async (job) => {
  if (isActiveJob(job)) {
    // Navigate to landing page with job query param to track progress
    router.push({ name: 'Landing', query: { job: job.job_id } })
  } else if (job.status === 'failed') {
    // Nothing to open for failed jobs
    return
  } else {
    // Completed system - navigate directly to analysis by its public jobId
    await systemsStore.loadSystems()

    // Try to find the matching system by id or by jobId from the jobs table
    const system = systemsStore.systems.find(
      (s) => s.id === job.id || (job.jobId && s.jobId === job.jobId)
    )

    if (!system || !system.jobId) {
      console.warn('No jobId found for job/system', job)
      return
    }

    await systemsStore.setCurrentSystem(system.id)
    router.push({ name: 'Analysis', params: { jobId: system.jobId } })
  }
}

// Rename modal functions
const openRenameModal = async (job) => {
  renameModal.value = {
    visible: true,
    system: job,
    newName: job.name
  }
  await nextTick()
  renameInput.value?.focus()
  renameInput.value?.select()
}

const closeRenameModal = () => {
  renameModal.value = {
    visible: false,
    system: null,
    newName: ''
  }
}

const confirmRename = async () => {
  const { system, newName } = renameModal.value
  if (!system || !newName.trim()) return
  
  try {
    await api.renameSystem(system.id, newName.trim())
    const idx = allJobs.value.findIndex(s => s.id === system.id)
    if (idx !== -1) {
      allJobs.value[idx].name = newName.trim()
    }
    closeRenameModal()
  } catch (error) {
    console.error('Failed to rename system:', error)
    alert('Failed to rename job. Please try again.')
  }
}
</script>

<style scoped>
.jobs-page {
  min-height: 100vh;
  background: #f5f5f7;
  display: flex;
  flex-direction: column;
}

/* Header */
.page-header {
  background: #ffffff;
  padding: 40px;
  border-bottom: 1px solid #e8e8ed;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.submit-job-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: #007aff;
  border: none;
  border-radius: 980px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.submit-job-btn:hover {
  background: #0066d6;
  transform: translateY(-1px);
}

.submit-job-btn svg {
  width: 16px;
  height: 16px;
}

.header-text h1 {
  font-size: 32px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 17px;
  color: #6e6e73;
  margin: 0;
}

/* Content */
.content {
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px;
  width: 100%;
  box-sizing: border-box;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #6e6e73;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e8e8ed;
  border-top-color: #1d1d1f;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-icon {
  width: 80px;
  height: 80px;
  color: #8e8e93;
  margin-bottom: 24px;
}

.empty-state h2 {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.empty-state p {
  font-size: 17px;
  color: #6e6e73;
  margin: 0 0 24px 0;
  max-width: 400px;
}

.start-btn,
.clear-btn {
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: #1d1d1f;
  border: none;
  border-radius: 980px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.start-btn:hover,
.clear-btn:hover {
  background: #000000;
  transform: translateY(-1px);
}

/* No Results State (inside table wrapper) */
.no-results-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
}

.no-results-icon {
  width: 64px;
  height: 64px;
  color: #8e8e93;
  margin-bottom: 20px;
}

.no-results-state h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
}

.no-results-state p {
  font-size: 15px;
  color: #6e6e73;
  margin: 0 0 20px 0;
  max-width: 400px;
}

/* Table Wrapper */
.table-wrapper {
  width: 100%;
}

/* Table Search */
.table-search {
  margin-bottom: 16px;
}

.table-search .search-box {
  position: relative;
  width: 100%;
}

.table-search .search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: #8e8e93;
}

.table-search .search-input {
  width: 100%;
  padding: 14px 44px 14px 48px;
  font-size: 15px;
  border: 1px solid #e8e8ed;
  border-radius: 12px;
  background: #ffffff;
  color: #1d1d1f;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.table-search .search-input:focus {
  outline: none;
  border-color: #007aff;
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

.table-search .search-input::placeholder {
  color: #8e8e93;
}

.table-search .clear-search {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border: none;
  background: #e8e8ed;
  color: #6e6e73;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.table-search .clear-search:hover {
  background: #d1d1d6;
  color: #1d1d1f;
}

/* Table */
.table-container {
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
}

.jobs-table {
  width: 100%;
  border-collapse: collapse;
}

.jobs-table th {
  padding: 16px 20px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #f5f5f7;
  border-bottom: 1px solid #e8e8ed;
}

.jobs-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: color 0.15s ease;
}

.jobs-table th.sortable:hover {
  color: #1d1d1f;
}

.sort-icon {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-left: 6px;
  opacity: 0.3;
  transition: all 0.15s ease;
}

.sort-icon.active {
  opacity: 1;
}

.sort-icon.desc svg {
  transform: rotate(180deg);
}

.sort-icon svg {
  fill: currentColor;
  transition: transform 0.15s ease;
}

.status-col {
  width: 80px;
}

.actions-col {
  width: 100px;
  text-align: center;
}

.job-row {
  cursor: pointer;
  transition: background 0.15s ease;
}

.job-row:hover {
  background: #f5f5f7;
}

.job-row.is-active {
  background: #f8faff;
}

.job-row.is-active:hover {
  background: #f0f5ff;
}

.jobs-table td {
  padding: 16px 20px;
  border-bottom: 1px solid #e8e8ed;
  font-size: 15px;
  color: #1d1d1f;
}

.job-row:last-child td {
  border-bottom: none;
}

/* Status */
.status-cell {
  text-align: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.status-icon {
  width: 20px;
  height: 20px;
}

.status-icon.ready {
  color: #34c759;
}

.status-icon.processing {
  color: #ff9500;
}

.status-icon.failed {
  color: #ff3b30;
}

/* Name Cell */
.name-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.job-name {
  font-weight: 600;
}

.job-id {
  font-size: 12px;
  color: #8e8e93;
}

/* Inline Progress (for active jobs) */
.inline-progress {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.inline-progress-bar {
  height: 4px;
  background: #e8e8ed;
  border-radius: 2px;
  overflow: hidden;
  width: 100%;
  max-width: 200px;
}

.inline-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007aff 0%, #00a2ff 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.inline-progress-label {
  font-size: 12px;
  color: #6e6e73;
  font-weight: 500;
}

/* Date Cell */
.date-cell {
  color: #6e6e73;
}

/* Frames Cell */
.frames-cell {
  font-variant-numeric: tabular-nums;
}

/* Actions */
.actions-cell {
  text-align: center;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #8e8e93;
  border-radius: 8px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  margin: 0 2px;
}

.action-btn:hover {
  background: #e8e8ed;
  color: #1d1d1f;
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.action-btn.open-btn:hover {
  background: #1d1d1f;
  color: #ffffff;
}

/* Table Footer */
.table-footer {
  padding: 16px 20px;
  background: #f5f5f7;
  border-top: 1px solid #e8e8ed;
}

.job-count {
  font-size: 14px;
  color: #6e6e73;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-panel {
  background: #ffffff;
  border-radius: 16px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.2s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8ed;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #f5f5f7;
  color: #6e6e73;
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.modal-close:hover {
  background: #e8e8ed;
  color: #1d1d1f;
}

.modal-body {
  padding: 24px;
}

.modal-body label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.rename-input {
  width: 100%;
  padding: 12px 16px;
  font-size: 15px;
  border: 2px solid #d2d2d7;
  border-radius: 10px;
  font-family: inherit;
  transition: all 0.15s ease;
  box-sizing: border-box;
}

.rename-input:focus {
  outline: none;
  border-color: #1d1d1f;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e8e8ed;
  background: #f5f5f7;
  border-radius: 0 0 16px 16px;
}

.btn-cancel,
.btn-confirm {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-cancel {
  background: #ffffff;
  color: #1d1d1f;
  border: 1px solid #d2d2d7;
}

.btn-cancel:hover {
  background: #f5f5f7;
}

.btn-confirm {
  background: #1d1d1f;
  color: #ffffff;
  border: none;
}

.btn-confirm:hover:not(:disabled) {
  background: #000000;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 24px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .submit-job-btn {
    width: 100%;
    justify-content: center;
  }

  .content {
    padding: 24px;
  }

  .jobs-table th,
  .jobs-table td {
    padding: 12px 16px;
  }

  .date-cell {
    display: none;
  }
}
</style>
