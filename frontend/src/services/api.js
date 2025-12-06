/**
 * API service for communicating with Flask backend
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

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
      return Promise.reject(new Error('No response from server. Make sure the backend is running on port 5000.'))
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

  async getSimilarityMatrix(systemId) {
    const response = await api.get(`/systems/${systemId}/similarity-matrix`)
    return response.data
  },

  async getAtomPairs(systemId, params) {
    const response = await api.get(`/systems/${systemId}/atom-pairs`, { params })
    return response.data
  },

  async getInteractionDistances(systemId) {
    const response = await api.get(`/systems/${systemId}/interaction-distances`)
    return response.data
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
  }
}

