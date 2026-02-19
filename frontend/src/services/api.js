/**
 * API service for communicating with Flask backend
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000 // 30 second timeout
})

// Add response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.error || error.response.data?.message || error.message
      return Promise.reject(new Error(message || 'Server error'))
    } else if (error.request) {
      // Request made but no response
      return Promise.reject(new Error('No response from server. Make sure the backend is running on port 5001.'))
    } else {
      // Error setting up request
      return Promise.reject(new Error(error.message || 'Request failed'))
    }
  }
)

export default {
  // Systems
  async getSystems() {
    const response = await api.get('/systems')
    return response.data
  },

  async getSystem(systemId) {
    const response = await api.get(`/systems/${systemId}`)
    return response.data
  },

  async renameSystem(systemId, newName) {
    const response = await api.post(`/systems/${systemId}/rename`, { name: newName })
    return response.data
  },

  // Data
  async getInteractions(systemId) {
    const response = await api.get(`/systems/${systemId}/interactions`)
    return response.data
  },

  async getAreaData(systemId) {
    const response = await api.get(`/systems/${systemId}/area`)
    return response.data
  },

  async getTrends(systemId) {
    const response = await api.get(`/systems/${systemId}/trends`)
    return response.data
  },

  async getAtomPairs(systemId, params) {
    const response = await api.get(`/systems/${systemId}/atom-pairs`, { params })
    return response.data
  },

  async getAtomPairsBatch(systemId, pairs) {
    const response = await api.post(`/systems/${systemId}/atom-pairs/batch`, { pairs })
    return response.data
  },

  async getInteractionDistances(systemId) {
    const response = await api.get(`/systems/${systemId}/interaction-distances`)
    return response.data
  },

  async getConservedIslands(systemId) {
    const response = await api.get(`/systems/${systemId}/conserved-islands`)
    return response.data
  },

  /**
   * Get the URL for a frame's PDB file (for Mol* viewer).
   * Uses current origin in dev (Vite proxy) or VITE_API_URL when set.
   */
  getFramePdbUrl(systemId, frameNum = 1) {
    const base = import.meta.env.VITE_API_URL
    const path = `/systems/${systemId}/frame/${frameNum}/pdb`
    if (base) {
      return `${base.replace(/\/$/, '')}${path}`
    }
    return `${typeof window !== 'undefined' ? window.location.origin : ''}/api${path}`
  },

  /**
   * Fetch PDB file content for a frame (for Mol* loadStructureFromData).
   * Uses same-origin URL in dev (Vite proxy) so the request appears in Network tab
   * and avoids CORS. Falls back to direct API URL when VITE_API_URL is set.
   */
  async getFramePdbContent(systemId, frameNum = 1) {
    const base = import.meta.env.VITE_API_URL
    const url = base
      ? `${base.replace(/\/$/, '')}/systems/${systemId}/frame/${frameNum}/pdb`
      : `/api/systems/${systemId}/frame/${frameNum}/pdb`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Failed to load PDB: ${res.status} ${res.statusText}`)
    return res.text()
  },

  async getDistanceDistributions(systemId, interactionTypes, minConsistency) {
    const params = {}
    if (interactionTypes && interactionTypes.length > 0) {
      params.interaction_types = interactionTypes.join(',')
    }
    if (minConsistency !== undefined && minConsistency !== null) {
      params.min_consistency = minConsistency
    }
    const response = await api.get(`/systems/${systemId}/distance-distributions`, { params })
    return response.data
  },

  // Upload
  async uploadFile(file, onProgress) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      }
    })
    return response.data
  },

  async getStatus(pdbId) {
    const response = await api.get(`/status/${pdbId}`)
    return response.data
  },

  /**
   * Upload file with full configuration options
   * @param {File} file - The PDB file to upload
   * @param {Object} options - Configuration options
   * @param {string} options.chain1 - First chain ID
   * @param {string} options.chain2 - Second chain ID
   * @param {boolean} options.useReduce - Whether to use reduce preprocessing
   * @param {number} options.interfaceCutoff - Interface cutoff distance
   * @param {number} options.waterCutoff - Water cutoff distance
   * @param {number} [options.startFrame] - Start frame (1-indexed, optional)
   * @param {number} [options.endFrame] - End frame (1-indexed, optional)
   * @param {Function} onProgress - Progress callback
   */
  async uploadFileWithOptions(file, options, onProgress) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('chain1', options.chain1)
    formData.append('chain2', options.chain2)
    formData.append('reduce', options.useReduce ? 'true' : 'false')
    formData.append('interface_cutoff', options.interfaceCutoff)
    formData.append('water_cutoff', options.waterCutoff)

    // Add frame interval if specified
    if (options.startFrame !== undefined && options.endFrame !== undefined) {
      formData.append('start_frame', options.startFrame)
      formData.append('end_frame', options.endFrame)
    }

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      }
    })
    return response.data
  }
}

