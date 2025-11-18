/**
 * Chart helper functions
 */


const INTERACTION_COLOR_RULES = [
  { color: [47, 79, 79], keywords: ['π-π', 'pi-pi', 'pi pi'] }, // π-π interaction
  { color: [152, 251, 152], keywords: ['amino-pi', 'amino_pi', 'polar-π', 'polar-pi'] }, // Polar-π (Amino-π)
  { color: [255, 0, 255], keywords: ['anion-π', 'anion-pi', 'anion_pi'] }, // Anion-π interaction
  { color: [60, 95, 95], keywords: ['apolar vdw', 'apolar_vdw'] }, // Apolar vdW contact
  { color: [173, 216, 230], keywords: ['ch-o', 'c-h_on', 'c-h on', 'ch-on'] }, // CH-O/N bond
  { color: [34, 139, 34], keywords: ['ch-π', 'ch-pi', 'c-h_pi'] }, // CH-π interaction
  { color: [0, 255, 255], keywords: ['cation-π', 'cation-pi', 'cation_pi'] }, // Cation-π interaction
  { color: [139, 0, 0], keywords: ['clash'] }, // Clash
  { color: [75, 0, 130], keywords: ['h-bond*', 'h-bond', 'hydrogen bond'] }, // H-bond
  { color: [85, 107, 47], keywords: ['halogen'] }, // Halogen bond
  { color: [70, 130, 180], keywords: ['lp-π', 'lp-pi', 'lone pair', 'lone_pair_pi'] }, // lp-π interaction
  { color: [139, 69, 19], keywords: ['metal mediated', 'metal_mediated'] }, // Metal mediated contact
  { color: [90, 75, 170], keywords: ['n-s-o-h', 'n-s-o-h_pi', 'o/n/sh'] }, // O/N/SH-π interaction
  { color: [255, 0, 127], keywords: ['polar vdw', 'polar_vdw'] }, // Polar vdW contact
  { color: [54, 69, 79], keywords: ['proximal'] }, // Proximal contact
  { color: [128, 0, 128], keywords: ['salt-bridge', 'salt bridge'] }, // Salt-bridge
  { color: [255, 103, 0], keywords: ['s-bond', 'ss bond', 's-s bond', 'ss_bond', 's-s'] }, // S / S-S bond
  { color: [72, 61, 139], keywords: ['water', 'water mediated', 'water_mediated'] } // Water mediated contact
]

function findInteractionColor(typeString) {
  const normalized = typeString.toLowerCase()
  for (const rule of INTERACTION_COLOR_RULES) {
    if (rule.keywords.some(keyword => normalized.includes(keyword.toLowerCase()))) {
      return rule.color
    }
  }
  return [75, 0, 130] // default (indigo)
}

/**
 * Get color for interaction type based on the fixed palette
 */
export function getInteractionColor(types, consistency) {
  const baseColor = findInteractionColor(types)
  const opacity = 0.3 + (consistency * 0.6)
  return `rgba(${baseColor[0]}, ${baseColor[1]}, ${baseColor[2]}, ${opacity})`
}

export function getInteractionBaseColor(typeLabel) {
  const color = findInteractionColor(typeLabel)
  return `rgb(${color[0]}, ${color[1]}, ${color[2]})`
}

/**
 * Check if interaction matches selected types
 */
export function matchesSelectedTypes(interactionTypes, selectedTypes, interactionTypeList) {
  if (selectedTypes.size === 0) return false
  
  const typesLower = interactionTypes.toLowerCase()
  
  for (const typeId of selectedTypes) {
    const type = interactionTypeList.find(t => t.id === typeId)
    if (type) {
      for (const keyword of type.keywords) {
        if (typesLower.includes(keyword.toLowerCase())) {
          return true
        }
      }
    }
  }
  return false
}

/**
 * Export INTERACTION_TYPES for use in components
 */
export { INTERACTION_TYPES } from './constants'

