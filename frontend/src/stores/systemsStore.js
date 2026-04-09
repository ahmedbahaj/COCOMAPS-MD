/**
 * Loaded systems / jobs and current selection.
 */
import { defineStore } from 'pinia'
import api from '../services/api'
import { useAnalysisStore } from './analysisStore'

export const useSystemsStore = defineStore('systems', {
  state: () => ({
    systems: [],
    currentSystem: null,
    isLoading: false,
    error: null
  }),

  getters: {
    totalFrames: (state) => state.currentSystem?.frames || 0
  },

  actions: {
    async loadSystems() {
      this.isLoading = true
      this.error = null
      try {
        this.systems = await api.getSystems()
      } catch (error) {
        this.error = error.message
        console.error('Error loading systems:', error)
      } finally {
        this.isLoading = false
      }
    },

    async setCurrentSystem(systemId) {
      const system = this.systems.find(s => s.id === systemId)
      if (!system) return

      this.currentSystem = system

      const analysis = useAnalysisStore()
      await Promise.all([
        analysis.loadInteractions(systemId),
        analysis.loadAreaData(systemId),
        analysis.loadTrends(systemId),
        analysis.loadConservedIslands(systemId)
      ])
    }
  }
})
