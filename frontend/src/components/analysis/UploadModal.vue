<template>
  <div v-if="isOpen" class="modal" @click.self="close">
    <div class="modal-content">
      <button class="close-btn" @click="close">×</button>
      <div class="modal-title">Upload PDB File</div>
      
      <div
        class="dropzone"
        :class="{ dragover: isDragging }"
        @click="triggerFileInput"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div class="dropzone-icon">📁</div>
        <div class="dropzone-text">Drag & drop your PDB file here</div>
        <div class="dropzone-subtext">or click to browse</div>
      </div>
      
      <input
        ref="fileInput"
        type="file"
        accept=".pdb"
        style="display: none;"
        @change="handleFileSelect"
      />
      
      <div v-if="uploading" class="progress-container">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <div class="progress-text">{{ progressText }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../services/api'
import { useSystemsStore } from '../../stores/systemsStore'

const systemsStore = useSystemsStore()
const isOpen = ref(false)
const isDragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const progressText = ref('')
const fileInput = ref(null)
let currentUploadId = null
let pollInterval = null

const open = () => {
  isOpen.value = true
}

const close = () => {
  isOpen.value = false
  uploading.value = false
  progress.value = 0
  progressText.value = ''
  currentUploadId = null
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    handleUpload(file)
  }
}

const handleDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.name.endsWith('.pdb')) {
    handleUpload(file)
  }
}

const handleUpload = async (file) => {
  if (!file.name.endsWith('.pdb')) {
    alert('Please select a valid PDB file')
    return
  }

  uploading.value = true
  progress.value = 10
  progressText.value = 'Uploading file...'

  try {
    const result = await api.uploadFile(file, (percent) => {
      progress.value = percent
    })

    if (result.success) {
      currentUploadId = result.id
      progressText.value = 'Processing PDB file...'
      pollStatus(result.id)
    } else {
      alert('Upload failed: ' + (result.error || 'Unknown error'))
      close()
    }
  } catch (error) {
    console.error('Upload error:', error)
    alert('Upload failed. Make sure the backend server is running on port 5000')
    close()
  }
}

const pollStatus = (pdbId) => {
  pollInterval = setInterval(async () => {
    try {
      const status = await api.getStatus(pdbId)

      progress.value = status.progress || 0

      if (status.status === 'splitting') {
        progressText.value = `Splitting PDB into frames... ${status.progress}%`
      } else if (status.status === 'analyzing') {
        progressText.value = `Running CoCoMaps analysis... ${status.progress}%`
      } else if (status.status === 'completed') {
        progressText.value = 'Processing complete!'
        
        // Reload systems and switch to new one
        await systemsStore.loadSystems()
        await systemsStore.setCurrentSystem(pdbId)
        
        // Close modal after delay
        setTimeout(() => {
          close()
        }, 1500)
        
        if (pollInterval) {
          clearInterval(pollInterval)
          pollInterval = null
        }
      } else if (status.status === 'failed') {
        alert('Processing failed: ' + (status.error || 'Unknown error'))
        close()
      }
    } catch (error) {
      console.error('Error polling status:', error)
    }
  }, 2000)
}

defineExpose({
  open,
  close
})
</script>

<style scoped>
.modal {
  position: fixed;
  z-index: 2000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background-color: #ffffff;
  padding: 40px;
  border-radius: 24px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
}

.close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f5f5f7;
  border: none;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #e8e8ed;
}

.modal-title {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 24px;
  text-align: center;
}

.dropzone {
  border: 2px dashed #d2d2d7;
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fbfbfd;
}

.dropzone:hover,
.dropzone.dragover {
  border-color: #1d1d1f;
  background: #f5f5f7;
}

.dropzone-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.dropzone-text {
  font-size: 17px;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.dropzone-subtext {
  font-size: 14px;
  color: #6e6e73;
}

.progress-container {
  margin-top: 24px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e8e8ed;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: #1d1d1f;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  font-size: 14px;
  color: #6e6e73;
}
</style>

