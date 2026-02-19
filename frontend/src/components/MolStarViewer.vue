<template>
  <div class="molstar-viewer-wrapper">
    <div
      v-if="!systemId"
      class="molstar-placeholder"
    >
      <p>No structure to display. Select a system.</p>
    </div>
    <div v-else class="molstar-viewer-inner">
      <div
        v-if="loadError"
        class="molstar-error-overlay"
      >
        <p>{{ loadError }}</p>
        <p class="hint">Ensure the backend is running on port 5001. Try <a :href="testPageUrl" target="_blank">standalone test</a>.</p>
      </div>
      <div
        v-else-if="loading"
        class="molstar-loading-overlay"
      >
        <div class="loading-spinner"></div>
        <p>Loading structure...</p>
      </div>
      <div
        :id="containerId"
        class="molstar-container"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue'

const props = defineProps({
  systemId: { type: String, default: null },
  frameNum: { type: Number, default: 1 },
  /** Residues to highlight: [{ chain, resNum, resName }]. Null to clear. */
  selectedResidues: { type: Array, default: null }
})

const containerId = ref(`molstar-${Math.random().toString(36).slice(2, 11)}`)
const loading = ref(true)
const loadError = ref(null)
let viewer = null

const testPageUrl = computed(() => {
  if (typeof window === 'undefined') return '#'
  return `${window.location.origin}/molstar-test.html`
})

function getPdbUrl() {
  if (typeof window === 'undefined') return ''
  const base = import.meta.env.VITE_API_URL
  const path = `/systems/${props.systemId}/frame/${props.frameNum}/pdb`
  if (base) {
    return `${base.replace(/\/$/, '')}${path}`
  }
  return `${window.location.origin}/api${path}`
}

async function initViewer() {
  if (!props.systemId || typeof window === 'undefined') return

  loading.value = true
  loadError.value = null
  await nextTick()

  const el = document.getElementById(containerId.value)
  if (!el) {
    loadError.value = 'Viewer container not found'
    loading.value = false
    return
  }

  if (!window.molstar?.Viewer) {
    loadError.value = 'Mol* not loaded. Check index.html has molstar.js script.'
    loading.value = false
    return
  }

  try {
    const url = getPdbUrl()
    viewer = await window.molstar.Viewer.create(containerId.value, {
      layoutIsExpanded: false,
      layoutShowControls: false,
      layoutShowRemoteState: false,
      layoutShowSequence: false,
      layoutShowLog: false,
      layoutShowLeftPanel: false,
      viewportShowExpand: true,
      viewportShowControls: false,
      viewportShowSelectionMode: false,
      viewportShowAnimation: false
    })
    await viewer.loadStructureFromUrl(url, 'pdb', false)
    if (viewer?.handleResize) viewer.handleResize()
    highlightResidues(props.selectedResidues)
  } catch (err) {
    console.error('Mol* load error:', err)
    loadError.value = err?.message || 'Failed to load structure'
  } finally {
    loading.value = false
  }
}

function disposeViewer() {
  if (viewer) {
    try { viewer.dispose() } catch (e) { console.warn('Mol* dispose:', e) }
    viewer = null
  }
}

function highlightResidues(residues) {
  if (!viewer) return
  try {
    if (!residues || residues.length === 0) {
      viewer.plugin.managers.interactivity.lociSelects.deselectAll()
      return
    }
    viewer.plugin.managers.interactivity.lociSelects.deselectAll()
    const schema = {
      items: residues.map(r => ({
        auth_asym_id: String(r.chain),
        auth_seq_id: Number(r.resNum)
      }))
    }
    viewer.structureInteractivity({
      elements: schema,
      action: 'select',
      applyGranularity: true
    })
  } catch (err) {
    console.warn('Mol* highlight:', err)
  }
}

onMounted(() => initViewer())
onBeforeUnmount(() => disposeViewer())

watch(() => [props.systemId, props.frameNum], () => {
  disposeViewer()
  if (props.systemId) {
    loading.value = true
    nextTick(() => initViewer())
  }
})

watch(() => props.selectedResidues, (residues) => {
  if (!loading.value && !loadError.value) {
    highlightResidues(residues)
  }
}, { immediate: true, deep: true })
</script>

<style scoped>
.molstar-viewer-wrapper {
  width: 100%;
  min-height: 400px;
  position: relative;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.molstar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #86868b;
  font-size: 15px;
}

.molstar-container {
  width: 100%;
  height: 600px;
  position: relative;
  min-height: 600px;
}

.molstar-viewer-inner {
  position: relative;
  min-height: 600px;
}

.molstar-error-overlay,
.molstar-loading-overlay {
  min-height: 600px;
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: rgba(26, 26, 26, 0.95);
  color: #6e6e73;
  font-size: 15px;
}

.molstar-error-overlay {
  color: #d32f2f;
}

.molstar-error-overlay .hint {
  font-size: 13px;
  color: #86868b;
  margin-top: 4px;
}

.molstar-loading-overlay .loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #d2d2d7;
  border-top-color: #1d1d1f;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.molstar-container :deep(.msp-plugin) {
  border-radius: 8px;
}
</style>
