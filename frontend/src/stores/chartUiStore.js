/**
 * Chart selection, filters, and display preferences (no server data).
 */
import { defineStore } from 'pinia'
import { INTERACTION_TYPES } from '../utils/constants'

export const useChartUiStore = defineStore('chartUi', {
  state: () => ({
    currentChartType: 'interactionConservationMatrix',
    currentThreshold: 0.5,
    useLogScale: false,
    selectedInteractionTypes: new Set(INTERACTION_TYPES.filter(t => t.id !== 'proximal').map(t => t.id)),
    typeConservationThreshold: 0.5,
    timeUnit: null
  }),

  actions: {
    setChartType(type) {
      this.currentChartType = type
    },

    setThreshold(threshold) {
      this.currentThreshold = threshold
    },

    setLogScale(useLog) {
      this.useLogScale = useLog
    },

    setTypeConservationThreshold(value) {
      this.typeConservationThreshold = value
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
