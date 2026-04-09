/**
 * Per-system analysis payloads from the API (interactions, area, trends, islands).
 */
import { defineStore } from 'pinia'
import api from '../services/api'
import { matchesSelectedTypes } from '../utils/chartHelpers'
import { INTERACTION_TYPES } from '../utils/constants'
import { useChartUiStore } from './chartUiStore'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    interactions: [],
    areaData: [],
    trends: {},
    trendFrameNumbers: [],
    conservedIslands: [],

    loading: {
      interactions: false,
      area: false,
      trends: false,
      conservedIslands: false
    },

    errors: {
      interactions: null,
      area: null,
      trends: null,
      conservedIslands: null
    }
  }),

  getters: {
    filteredInteractions: (state) => {
      const ui = useChartUiStore()
      return state.interactions.filter(d => {
        const thresholdPercent = Math.round(ui.currentThreshold * 100)
        const consistencyPercent = Math.round(d.consistency * 100)
        if (consistencyPercent < thresholdPercent) return false
        if (ui.selectedInteractionTypes.size === 0) return false

        const typesString = d.typesArray.join('; ')
        return matchesSelectedTypes(typesString, ui.selectedInteractionTypes, INTERACTION_TYPES)
      })
    }
  },

  actions: {
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
        this.trendFrameNumbers = data.frameNumbers || []
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
    }
  }
})
