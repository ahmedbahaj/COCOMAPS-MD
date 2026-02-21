/**
 * Pinia store for managing application data and state
 */
import { defineStore } from 'pinia'
import api from '../services/api'
import { matchesSelectedTypes } from '../utils/chartHelpers'
import { INTERACTION_TYPES } from '../utils/constants'

export const useDataStore = defineStore('data', {
  state: () => ({
    // Systems
    systems: [],
    currentSystem: null,

    // Data
    interactions: [],
    areaData: [],
    trends: {},
    trendFrameNumbers: [],  // Actual frame numbers with data (e.g., [21, 22])
    conservedIslands: [],

    // UI State
    currentChartType: 'conservedIslandsList',
    currentThreshold: 0.5,
    useLogScale: false,
    selectedInteractionTypes: new Set(INTERACTION_TYPES.filter(t => t.id !== 'proximal').map(t => t.id)), // All except proximal by default
    timeUnit: null, // User-defined time unit label (e.g., 'ns', 'ps', 'μs'); null means use 'Frame'

    // Loading states
    loading: {
      systems: false,
      interactions: false,
      area: false,
      trends: false,
      conservedIslands: false
    },

    // Error states
    errors: {
      systems: null,
      interactions: null,
      area: null,
      trends: null,
      conservedIslands: null
    }
  }),

  getters: {
    totalFrames: (state) => {
      return state.currentSystem?.frames || 0
    },

    filteredInteractions: (state) => {
      return state.interactions.filter(d => {
        // Use >= for "at least" comparison (greater than or equal to)
        // Compare at percentage level to avoid floating point precision issues
        // Convert to integers for exact comparison
        const thresholdPercent = Math.round(state.currentThreshold * 100)
        const consistencyPercent = Math.round(d.consistency * 100)
        // Only include if consistency is >= threshold (greater than or equal to)
        // This ensures interactions with exactly x% conservation show when threshold is x%
        if (consistencyPercent < thresholdPercent) return false
        if (state.selectedInteractionTypes.size === 0) return false

        // Check if any interaction types match
        const typesString = d.typesArray.join('; ')
        return matchesSelectedTypes(typesString, state.selectedInteractionTypes, INTERACTION_TYPES)
      })
    }
  },

  actions: {
    // Systems
    async loadSystems() {
      this.loading.systems = true
      this.errors.systems = null
      try {
        this.systems = await api.getSystems()
      } catch (error) {
        this.errors.systems = error.message
        console.error('Error loading systems:', error)
      } finally {
        this.loading.systems = false
      }
    },

    async setCurrentSystem(systemId) {
      const system = this.systems.find(s => s.id === systemId)
      if (system) {
        this.currentSystem = system
        // Load all data for the new system
        await Promise.all([
          this.loadInteractions(systemId),
          this.loadAreaData(systemId),
          this.loadTrends(systemId),
          this.loadConservedIslands(systemId)
        ])
      }
    },

    // Data loading
    async loadInteractions(systemId) {
      this.loading.interactions = true
      this.errors.interactions = null
      try {
        const data = await api.getInteractions(systemId)
        this.interactions = data.interactions || []
      } catch (error) {
        this.errors.interactions = error.message
        console.error('Error loading interactions:', error)
      } finally {
        this.loading.interactions = false
      }
    },

    async loadAreaData(systemId) {
      this.loading.area = true
      this.errors.area = null
      try {
        const data = await api.getAreaData(systemId)
        this.areaData = data.frames || []
      } catch (error) {
        this.errors.area = error.message
        console.error('Error loading area data:', error)
      } finally {
        this.loading.area = false
      }
    },

    async loadTrends(systemId) {
      this.loading.trends = true
      this.errors.trends = null
      try {
        const data = await api.getTrends(systemId)
        this.trends = data.trends || {}
        this.trendFrameNumbers = data.frameNumbers || []  // Actual frame numbers with data
      } catch (error) {
        this.errors.trends = error.message
        console.error('Error loading trends:', error)
      } finally {
        this.loading.trends = false
      }
    },

    async loadConservedIslands(systemId) {
      this.loading.conservedIslands = true
      this.errors.conservedIslands = null
      try {
        const data = await api.getConservedIslands(systemId)
        this.conservedIslands = data.islands || []
      } catch (error) {
        this.errors.conservedIslands = error.message
        this.conservedIslands = []
        console.error('Error loading conserved islands:', error)
      } finally {
        this.loading.conservedIslands = false
      }
    },

    // UI State
    setChartType(type) {
      this.currentChartType = type
    },

    setThreshold(threshold) {
      this.currentThreshold = threshold
    },

    setLogScale(useLog) {
      this.useLogScale = useLog
    },

    setTimeUnit(unit) {
      this.timeUnit = unit || null
    },

    toggleInteractionType(typeId) {
      const updatedTypes = new Set(this.selectedInteractionTypes)
      if (updatedTypes.has(typeId)) {
        updatedTypes.delete(typeId)
      } else {
        updatedTypes.add(typeId)
      }
      this.selectedInteractionTypes = updatedTypes
    },

    selectAllInteractionTypes() {
      this.selectedInteractionTypes = new Set(INTERACTION_TYPES.map(t => t.id))
    },

    clearInteractionTypes() {
      this.selectedInteractionTypes = new Set()
    }
  }
})
