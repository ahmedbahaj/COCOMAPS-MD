<template>
  <div v-if="visible" class="trajectory-modal-overlay" @click.self="close">
    <div class="trajectory-modal-panel">
      <div class="panel-header">
        <h2>Interaction Trajectory Analysis</h2>
        <button class="close-button" @click="close">×</button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading trajectory data...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
      </div>

      <div v-else-if="interactionData" class="panel-content">
        <!-- Residue Pair Info -->
        <div class="residue-info">
          <h3>{{ interactionData.pair }}</h3>
          <p class="interaction-meta">
            <span class="meta-item">
              <strong>Interaction Type:</strong> {{ interactionData.type }}
            </span>
            <span class="meta-item">
              <strong>Overall Conservation:</strong> {{ Math.round(interactionData.pairConsistency * 100) }}%
            </span>
            <span class="meta-item">
              <strong>Type Conservation:</strong> {{ Math.round(interactionData.typeConservation * 100) }}%
            </span>
          </p>
        </div>

        <!-- Connected Atoms for Selected Frame -->
        <div v-if="selectedFrame" class="atom-connection-section" :class="{ empty: !frameHasInteraction(selectedFrame) }">
          <!-- Only show atoms if the frame has the interaction -->
          <template v-if="frameHasInteraction(selectedFrame)">
            <h4>Atoms Connected in Frame {{ selectedFrame }}</h4>
            
            <div v-if="frameAtomPairs.length > 0" class="atom-connection-visual">
              <div 
                v-for="(atomPair, idx) in frameAtomPairs" 
                :key="idx"
                class="atom-bond-card"
              >
                <div class="bond-visual">
                  <div class="atom-node atom-1">
                    <span class="atom-name">{{ atomPair.atom1 }}</span>
                    <span class="atom-residue">{{ getResidueFromPair(1) }}</span>
                  </div>
                  <div class="bond-line" :style="{ backgroundColor: getInteractionBaseColor(atomPair.type) }">
                    <span class="bond-type">{{ atomPair.type }}</span>
                  </div>
                  <div class="atom-node atom-2">
                    <span class="atom-name">{{ atomPair.atom2 }}</span>
                    <span class="atom-residue">{{ getResidueFromPair(2) }}</span>
                  </div>
                </div>
                <div class="bond-stats">
                  <span class="bond-frequency" :style="{ color: getInteractionBaseColor(atomPair.type) }">
                    {{ Math.round(atomPair.consistency * 100) }}% overall conservation
                  </span>
                </div>
              </div>
            </div>
            <div v-else-if="!atomPairData" class="no-atoms-msg">
              <p>Loading atom pairs...</p>
            </div>
            <div v-else class="no-atoms-msg">
              <p>No atom-level data for frame {{ selectedFrame }}</p>
            </div>
          </template>
          
          <!-- Frame has no interaction -->
          <template v-else>
            <h4>Frame {{ selectedFrame }}</h4>
            <div class="no-atoms-msg">
              <p>No {{ interactionData.type }} interaction in this frame</p>
            </div>
          </template>
        </div>

        <!-- Statistical Summary Cards -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ stats.persistence }}</div>
            <div class="stat-label">Persistence</div>
            <div class="stat-sublabel">{{ stats.presentFrames }} of {{ totalFrames }} frames</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.avgDistance }}</div>
            <div class="stat-label">Avg Distance</div>
            <div class="stat-sublabel">{{ stats.distanceRange }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.variability }}</div>
            <div class="stat-label">Variability</div>
            <div class="stat-sublabel">σ = {{ stats.stdDev }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.longestStretch }}</div>
            <div class="stat-label">Longest Stretch</div>
            <div class="stat-sublabel">Consecutive frames</div>
          </div>
        </div>

        <!-- Interaction Conservation Timeline -->
        <div class="section">
          <h4>Interaction Conservation Timeline</h4>
          <p class="section-description">
            Click on the timeline to select a frame | Blue = Present, Gray = Absent
          </p>
          <div class="timeline-bar-container">
            <div class="timeline-bar" ref="timelineBar" @click="handleTimelineClick">
              <div 
                v-for="frame in totalFrames" 
                :key="frame"
                class="timeline-segment"
                :class="{ 
                  'has-interaction': frameHasInteraction(frame),
                  'selected': selectedFrame === frame
                }"
                :style="{ width: `${100 / totalFrames}%` }"
                @click.stop="selectFrame(frame)"
                :title="getFrameTooltip(frame)"
              ></div>
            </div>
            <div class="timeline-markers">
              <span class="marker" style="left: 0%">1</span>
              <span class="marker" style="left: 25%">{{ Math.round(totalFrames * 0.25) }}</span>
              <span class="marker" style="left: 50%">{{ Math.round(totalFrames * 0.5) }}</span>
              <span class="marker" style="left: 75%">{{ Math.round(totalFrames * 0.75) }}</span>
              <span class="marker" style="left: 100%">{{ totalFrames }}</span>
            </div>
            <div v-if="selectedFrame" class="selected-marker" :style="{ left: `${((selectedFrame - 1) / (totalFrames - 1)) * 100}%` }">
              <div class="marker-line"></div>
              <div class="marker-label">Frame {{ selectedFrame }}</div>
            </div>
          </div>
        </div>

        <!-- Selected Frame Details -->
        <div v-if="selectedFrame" class="section frame-details">
          <h4>Frame {{ selectedFrame }} Details</h4>
          <div class="frame-detail-card">
            <div class="detail-row">
              <span class="detail-label">Status:</span>
              <span class="detail-value" :class="frameHasInteraction(selectedFrame) ? 'present' : 'absent'">
                {{ frameHasInteraction(selectedFrame) ? 'Present' : 'Absent' }}
              </span>
            </div>
            <div v-if="frameHasInteraction(selectedFrame) && getFrameDistance(selectedFrame)" class="detail-row">
              <span class="detail-label">Distance:</span>
              <span class="detail-value">{{ getFrameDistance(selectedFrame).toFixed(2) }} Å</span>
            </div>
            <div v-if="frameHasInteraction(selectedFrame)" class="detail-row">
              <span class="detail-label">Interaction Type:</span>
              <span class="detail-value">{{ interactionData.type }}</span>
            </div>
          </div>
        </div>

        <!-- Distance Evolution Chart -->
        <div class="section">
          <h4>Distance Evolution Over Time</h4>
          <div v-if="anomalies.length > 0" class="anomaly-summary">
            <span class="anomaly-icon">⚠️</span>
            <span>{{ anomalies.length }} anomalies detected</span>
            <button class="anomaly-toggle" @click="showAnomalyDetails = !showAnomalyDetails">
              {{ showAnomalyDetails ? 'Hide' : 'Show' }}
            </button>
          </div>
          <div v-if="showAnomalyDetails && anomalies.length > 0" class="anomaly-list">
            <div 
              v-for="(anomaly, idx) in anomalies" 
              :key="idx"
              class="anomaly-item"
              :class="'anomaly-' + anomaly.type"
              @click="selectFrame(anomaly.frame)"
            >
              <span class="anomaly-badge">{{ anomaly.type === 'outlier' ? '📊' : '⚡' }}</span>
              <span class="anomaly-desc">{{ anomaly.description }}</span>
              <span class="anomaly-frame">Frame {{ anomaly.frame }}</span>
            </div>
          </div>
          <div ref="distanceChart" class="chart-container"></div>
        </div>

        <!-- Distance Distribution Histogram -->
        <div v-if="distanceHistogram.length > 0" class="section">
          <h4>Distance Distribution</h4>
          <p class="section-description">
            Distribution of distances across all frames where interaction is present
          </p>
          <div ref="histogramChart" class="chart-container-small"></div>
          <div class="distribution-stats">
            <div class="dist-stat">
              <span class="dist-label">Mode:</span>
              <span class="dist-value">{{ distanceStats.mode }}</span>
            </div>
            <div class="dist-stat">
              <span class="dist-label">Median:</span>
              <span class="dist-value">{{ distanceStats.median }}</span>
            </div>
            <div class="dist-stat">
              <span class="dist-label">Skewness:</span>
              <span class="dist-value">{{ distanceStats.skewness }}</span>
            </div>
          </div>
        </div>

        <!-- Interaction Type Analysis -->
        <div v-if="interactionTypeAnalysis.types.length > 1" class="section">
          <h4>Interaction Type Analysis</h4>
          <p class="section-description">
            How different interaction types co-occur across the trajectory
          </p>
          
          <!-- Type Timeline -->
          <div class="type-timeline">
            <div 
              v-for="typeData in interactionTypeAnalysis.types" 
              :key="typeData.type"
              class="type-row"
            >
              <div class="type-label">{{ typeData.type }}</div>
              <div class="type-bar">
                <div 
                  v-for="frame in totalFrames" 
                  :key="frame"
                  class="type-segment"
                  :class="{ 'active': typeData.frames.includes(frame) }"
                  :style="{ width: `${100 / totalFrames}%` }"
                  :title="`Frame ${frame}: ${typeData.frames.includes(frame) ? 'Active' : 'Inactive'}`"
                ></div>
              </div>
              <div class="type-percent">{{ Math.round(typeData.persistence * 100) }}%</div>
            </div>
          </div>

          <!-- Co-occurrence Matrix -->
          <div v-if="interactionTypeAnalysis.types.length > 1" class="cooccurrence-section">
            <h5>Co-occurrence Analysis</h5>
            <div class="cooccurrence-grid">
              <div 
                v-for="pair in interactionTypeAnalysis.cooccurrence" 
                :key="pair.types"
                class="cooccurrence-item"
              >
                <div class="cooccurrence-types">{{ pair.type1 }} + {{ pair.type2 }}</div>
                <div class="cooccurrence-bar-container">
                  <div class="cooccurrence-bar" :style="{ width: `${pair.percentage}%` }"></div>
                </div>
                <div class="cooccurrence-value">{{ pair.percentage }}% co-occur</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Binding Events -->
        <div v-if="bindingEvents.length > 0" class="section">
          <h4>Binding Events</h4>
          <div class="events-list">
            <div 
              v-for="(event, idx) in bindingEvents" 
              :key="idx"
              class="event-item"
              :class="'event-' + event.type"
            >
              <span class="event-icon">{{ event.icon }}</span>
              <span class="event-label">{{ event.label }}</span>
              <span class="event-frame">Frame {{ event.frame }}</span>
            </div>
          </div>
        </div>

        <!-- Interaction Details Table -->
        <div class="section">
          <h4>Frame-by-Frame Data</h4>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Frame</th>
                  <th>Status</th>
                  <th>Distance (Å)</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="frame in totalFrames" :key="frame">
                  <td><strong>{{ frame }}</strong></td>
                  <td>
                    <span class="status-badge" :class="frameHasInteraction(frame) ? 'present' : 'absent'">
                      {{ frameHasInteraction(frame) ? 'Present' : 'Absent' }}
                    </span>
                  </td>
                  <td>{{ getFrameDistance(frame) ? getFrameDistance(frame).toFixed(2) : '—' }}</td>
                  <td>{{ frameHasInteraction(frame) ? interactionData.type : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          <button class="action-btn secondary-btn" @click="exportData">
            Export Data
          </button>
          <button class="action-btn primary-btn" @click="openAtomPairExplorer">
            View Atom Pairs
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import Highcharts from 'highcharts'
import { useDataStore } from '../stores/dataStore'
import api from '../services/api'
import { getInteractionBaseColor } from '../utils/chartHelpers'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  interactionData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'openAtomPairExplorer'])

const dataStore = useDataStore()
const loading = ref(false)
const error = ref(null)
const distanceData = ref(null)
const atomPairData = ref(null)
const distanceChart = ref(null)
const histogramChart = ref(null)
const timelineBar = ref(null)
let chartInstance = null
let histogramInstance = null
const selectedFrame = ref(null)
const showAnomalyDetails = ref(false)

const totalFrames = computed(() => dataStore.totalFrames)

// Atom pairs present in the selected frame, filtered by the clicked interaction type
const frameAtomPairs = computed(() => {
  if (!atomPairData.value || !selectedFrame.value || !props.interactionData) {
    return []
  }
  
  // Use atomPairsByFrame - the direct mapping from frame to atom pairs
  const byFrame = atomPairData.value.atomPairsByFrame
  if (!byFrame) {
    return []
  }
  
  // Get atom pairs for the selected frame (key is string)
  const frameKey = String(selectedFrame.value)
  const atomsInFrame = byFrame[frameKey] || []
  
  // Get the interaction type that was clicked
  const clickedType = props.interactionData.type
  
  // Filter atom pairs to only show those matching the clicked interaction type
  return atomsInFrame
    .filter(frameAtom => frameAtom.interactionType === clickedType)
    .map(frameAtom => {
      // Find the full stats for this atom pair
      const fullStats = atomPairData.value.atomPairs?.find(
        p => p.atomPair === frameAtom.atomPair
      )
      return {
        ...frameAtom,
        consistency: fullStats?.consistency || 0,
        frameCount: fullStats?.frameCount || 1,
        type: frameAtom.interactionType
      }
    })
})

// Extract residue name from pair
const getResidueFromPair = (index) => {
  if (!props.interactionData?.pair) return ''
  const parts = props.interactionData.pair.split(' ↔ ')
  return parts[index - 1] || ''
}

// Handle click on the timeline bar (for precision selection)
const handleTimelineClick = (event) => {
  if (!timelineBar.value) return
  const rect = timelineBar.value.getBoundingClientRect()
  const clickX = event.clientX - rect.left
  const percentage = clickX / rect.width
  const frame = Math.max(1, Math.min(totalFrames.value, Math.round(percentage * totalFrames.value) + 1))
  selectFrame(frame)
}

const close = () => {
  emit('close')
}

const openAtomPairExplorer = () => {
  emit('openAtomPairExplorer', {
    pair: props.interactionData.pair
  })
}

// Check if frame has this interaction
const frameHasInteraction = (frame) => {
  if (!props.interactionData?.frames) return false
  return props.interactionData.frames.includes(frame)
}

// Get distance for a specific frame
const getFrameDistance = (frame) => {
  if (!distanceData.value || !props.interactionData) return null
  
  const pairKey = props.interactionData.pair.replace(' ↔ ', '_').replace(/-/g, '-')
  const distances = distanceData.value.distances?.[pairKey]
  if (!distances) return null
  
  const frameDistances = distances[frame]
  if (!frameDistances) return null
  
  return frameDistances[props.interactionData.type]
}

// Get tooltip for frame
const getFrameTooltip = (frame) => {
  if (frameHasInteraction(frame)) {
    const dist = getFrameDistance(frame)
    return dist ? `Frame ${frame}: Present (${dist.toFixed(2)} Å)` : `Frame ${frame}: Present`
  }
  return `Frame ${frame}: Absent`
}

// Select/deselect frame for details (toggle)
const selectFrame = (frame) => {
  if (selectedFrame.value === frame) {
    selectedFrame.value = null  // Deselect if already selected
  } else {
    selectedFrame.value = frame
  }
}

// Calculate statistics
const stats = computed(() => {
  if (!props.interactionData) {
    return {
      persistence: '—',
      presentFrames: 0,
      avgDistance: '—',
      distanceRange: '—',
      variability: '—',
      stdDev: '—',
      longestStretch: 0
    }
  }

  const frames = props.interactionData.frames || []
  const persistence = `${Math.round((frames.length / totalFrames.value) * 100)}%`
  
  // Calculate distance statistics
  const distances = []
  frames.forEach(frame => {
    const dist = getFrameDistance(frame)
    if (dist !== null) distances.push(dist)
  })
  
  let avgDistance = '—'
  let distanceRange = '—'
  let variability = '—'
  let stdDev = '—'
  
  if (distances.length > 0) {
    const avg = distances.reduce((sum, d) => sum + d, 0) / distances.length
    avgDistance = `${avg.toFixed(2)} Å`
    
    const min = Math.min(...distances)
    const max = Math.max(...distances)
    distanceRange = `${min.toFixed(1)} - ${max.toFixed(1)} Å`
    
    const variance = distances.reduce((sum, d) => sum + Math.pow(d - avg, 2), 0) / distances.length
    const std = Math.sqrt(variance)
    stdDev = std.toFixed(2)
    
    if (std < 0.3) variability = 'Low'
    else if (std < 0.8) variability = 'Medium'
    else variability = 'High'
  }
  
  // Calculate longest consecutive stretch
  let longestStretch = 0
  let currentStretch = 0
  for (let i = 1; i <= totalFrames.value; i++) {
    if (frameHasInteraction(i)) {
      currentStretch++
      longestStretch = Math.max(longestStretch, currentStretch)
    } else {
      currentStretch = 0
    }
  }
  
  return {
    persistence,
    presentFrames: frames.length,
    avgDistance,
    distanceRange,
    variability,
    stdDev,
    longestStretch
  }
})

// Detect binding events
const bindingEvents = computed(() => {
  if (!props.interactionData) return []
  
  const events = []
  let wasPresent = false
  
  for (let i = 1; i <= totalFrames.value; i++) {
    const isPresent = frameHasInteraction(i)
    
    if (isPresent && !wasPresent) {
      events.push({
        type: 'formation',
        icon: '🟢',
        label: wasPresent === null ? 'Formation' : 'Reformation',
        frame: i
      })
    } else if (!isPresent && wasPresent) {
      events.push({
        type: 'breaking',
        icon: '🔴',
        label: 'Breaking',
        frame: i
      })
    }
    
    wasPresent = isPresent
  }
  
  return events
})

// Distance histogram data
const distanceHistogram = computed(() => {
  if (!props.interactionData || !distanceData.value) return []
  
  const distances = []
  const frames = props.interactionData.frames || []
  
  frames.forEach(frame => {
    const dist = getFrameDistance(frame)
    if (dist !== null) distances.push(dist)
  })
  
  if (distances.length === 0) return []
  
  // Create bins
  const min = Math.floor(Math.min(...distances) * 10) / 10
  const max = Math.ceil(Math.max(...distances) * 10) / 10
  const binWidth = 0.2 // 0.2 Å bins
  const numBins = Math.ceil((max - min) / binWidth)
  
  const bins = []
  for (let i = 0; i < numBins; i++) {
    const binStart = min + (i * binWidth)
    const binEnd = binStart + binWidth
    const count = distances.filter(d => d >= binStart && d < binEnd).length
    bins.push({
      range: `${binStart.toFixed(1)}-${binEnd.toFixed(1)}`,
      start: binStart,
      end: binEnd,
      count: count,
      percentage: Math.round((count / distances.length) * 100)
    })
  }
  
  return bins
})

// Distance statistics for histogram
const distanceStats = computed(() => {
  if (!props.interactionData || !distanceData.value) {
    return { mode: '—', median: '—', skewness: '—' }
  }
  
  const distances = []
  const frames = props.interactionData.frames || []
  
  frames.forEach(frame => {
    const dist = getFrameDistance(frame)
    if (dist !== null) distances.push(dist)
  })
  
  if (distances.length === 0) {
    return { mode: '—', median: '—', skewness: '—' }
  }
  
  // Sort for median
  const sorted = [...distances].sort((a, b) => a - b)
  const median = sorted.length % 2 === 0
    ? ((sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2).toFixed(2) + ' Å'
    : sorted[Math.floor(sorted.length / 2)].toFixed(2) + ' Å'
  
  // Find mode (most common bin)
  const modeBin = distanceHistogram.value.reduce((max, bin) => 
    bin.count > max.count ? bin : max, { count: 0 })
  const mode = modeBin.range ? `${modeBin.range} Å` : '—'
  
  // Calculate skewness
  const avg = distances.reduce((s, d) => s + d, 0) / distances.length
  const std = Math.sqrt(distances.reduce((s, d) => s + Math.pow(d - avg, 2), 0) / distances.length)
  const skew = std > 0 
    ? distances.reduce((s, d) => s + Math.pow((d - avg) / std, 3), 0) / distances.length
    : 0
  
  let skewness = 'Symmetric'
  if (skew > 0.5) skewness = 'Right-skewed'
  else if (skew < -0.5) skewness = 'Left-skewed'
  
  return { mode, median, skewness }
})

// Anomaly detection
const anomalies = computed(() => {
  if (!props.interactionData || !distanceData.value) return []
  
  const detected = []
  const frames = props.interactionData.frames || []
  const distances = []
  
  frames.forEach(frame => {
    const dist = getFrameDistance(frame)
    if (dist !== null) distances.push({ frame, distance: dist })
  })
  
  if (distances.length < 3) return []
  
  // Calculate mean and std
  const values = distances.map(d => d.distance)
  const avg = values.reduce((s, d) => s + d, 0) / values.length
  const std = Math.sqrt(values.reduce((s, d) => s + Math.pow(d - avg, 2), 0) / values.length)
  
  // Detect outliers (beyond 2 std)
  distances.forEach(d => {
    if (Math.abs(d.distance - avg) > 2 * std) {
      detected.push({
        type: 'outlier',
        frame: d.frame,
        description: `Distance ${d.distance.toFixed(2)}Å is ${d.distance > avg ? 'unusually high' : 'unusually low'}`,
        value: d.distance
      })
    }
  })
  
  // Detect sudden jumps (large change between consecutive frames)
  const sortedDistances = [...distances].sort((a, b) => a.frame - b.frame)
  for (let i = 1; i < sortedDistances.length; i++) {
    const prev = sortedDistances[i - 1]
    const curr = sortedDistances[i]
    const change = Math.abs(curr.distance - prev.distance)
    
    // If consecutive frames and jump > 1.5Å (significant)
    if (curr.frame - prev.frame === 1 && change > 1.5) {
      detected.push({
        type: 'jump',
        frame: curr.frame,
        description: `Sudden ${change.toFixed(2)}Å jump from frame ${prev.frame}`,
        value: change
      })
    }
  }
  
  return detected.sort((a, b) => a.frame - b.frame)
})

// Interaction type analysis
const interactionTypeAnalysis = computed(() => {
  if (!props.interactionData || !distanceData.value) {
    return { types: [], cooccurrence: [] }
  }
  
  const pairKey = props.interactionData.pair.replace(' ↔ ', '_').replace(/-/g, '-')
  const allDistances = distanceData.value.distances?.[pairKey]
  
  if (!allDistances) {
    return { types: [], cooccurrence: [] }
  }
  
  // Collect all types and their frames
  const typeFrames = new Map()
  
  for (let frame = 1; frame <= totalFrames.value; frame++) {
    const frameData = allDistances[frame]
    if (!frameData) continue
    
    Object.keys(frameData).forEach(type => {
      if (!typeFrames.has(type)) {
        typeFrames.set(type, [])
      }
      typeFrames.get(type).push(frame)
    })
  }
  
  // Convert to array with persistence
  const types = Array.from(typeFrames.entries()).map(([type, frames]) => ({
    type,
    frames,
    persistence: frames.length / totalFrames.value
  })).sort((a, b) => b.persistence - a.persistence)
  
  // Calculate co-occurrence
  const cooccurrence = []
  for (let i = 0; i < types.length; i++) {
    for (let j = i + 1; j < types.length; j++) {
      const type1Frames = new Set(types[i].frames)
      const type2Frames = new Set(types[j].frames)
      
      // Count frames where both are present
      let coCount = 0
      type1Frames.forEach(f => {
        if (type2Frames.has(f)) coCount++
      })
      
      // Calculate percentage relative to the less common type
      const minFrames = Math.min(types[i].frames.length, types[j].frames.length)
      const percentage = minFrames > 0 ? Math.round((coCount / minFrames) * 100) : 0
      
      if (percentage > 0) {
        cooccurrence.push({
          type1: types[i].type,
          type2: types[j].type,
          types: `${types[i].type} + ${types[j].type}`,
          coCount,
          percentage
        })
      }
    }
  }
  
  return { types, cooccurrence: cooccurrence.sort((a, b) => b.percentage - a.percentage) }
})

// Update histogram chart
const updateHistogramChart = () => {
  if (!histogramChart.value || distanceHistogram.value.length === 0) return
  
  if (histogramInstance) {
    histogramInstance.destroy()
  }
  
  const chartData = distanceHistogram.value.map(bin => ({
    name: bin.range,
    y: bin.count,
    percentage: bin.percentage
  }))
  
  histogramInstance = Highcharts.chart(histogramChart.value, {
    chart: {
      type: 'column',
      backgroundColor: 'transparent',
      height: 200
    },
    title: { text: null },
    credits: { enabled: false },
    xAxis: {
      type: 'category',
      labels: {
        rotation: -45,
        style: { fontSize: '10px', color: '#6e6e73' }
      },
      title: { text: 'Distance (Å)', style: { fontSize: '11px', color: '#6e6e73' } }
    },
    yAxis: {
      title: { text: 'Frames', style: { fontSize: '11px', color: '#6e6e73' } },
      labels: { style: { fontSize: '10px', color: '#6e6e73' } }
    },
    legend: { enabled: false },
    plotOptions: {
      column: {
        color: '#3B6EF5',
        borderRadius: 3,
        dataLabels: {
          enabled: true,
          format: '{point.y}',
          style: { fontSize: '9px', color: '#6e6e73' }
        }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 8,
      formatter: function() {
        return `<b>${this.point.name} Å</b><br/>Frames: ${this.point.y} (${this.point.percentage}%)`
      }
    },
    series: [{ name: 'Frames', data: chartData }]
  })
}

// Update distance chart
const updateDistanceChart = () => {
  if (!distanceChart.value || !props.interactionData) return
  
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const chartData = []
  const anomalyFrames = new Set(anomalies.value.map(a => a.frame))
  
  for (let i = 1; i <= totalFrames.value; i++) {
    const dist = getFrameDistance(i)
    if (dist !== null) {
      const isAnomaly = anomalyFrames.has(i)
      chartData.push({
        x: i,
        y: dist,
        marker: {
          fillColor: isAnomaly ? '#FF3B30' : (frameHasInteraction(i) ? '#3B6EF5' : '#CC0000'),
          radius: isAnomaly ? 7 : 4,
          symbol: isAnomaly ? 'diamond' : 'circle',
          lineWidth: isAnomaly ? 2 : 0,
          lineColor: '#FF3B30'
        },
        isAnomaly: isAnomaly
      })
    }
  }
  
  chartInstance = Highcharts.chart(distanceChart.value, {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      height: 300
    },
    title: {
      text: null
    },
    credits: {
      enabled: false
    },
    xAxis: {
      title: {
        text: 'Frame Number',
        style: {
          fontSize: '13px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      min: 1,
      max: totalFrames.value,
      labels: {
        style: {
          fontSize: '11px',
          color: '#6e6e73'
        }
      }
    },
    yAxis: {
      title: {
        text: 'Distance (Å)',
        style: {
          fontSize: '13px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '11px',
          color: '#6e6e73'
        }
      },
      plotLines: props.interactionData.type === 'H-bond' ? [{
        value: 3.5,
        color: '#FF8800',
        dashStyle: 'dash',
        width: 2,
        label: {
          text: 'H-bond cutoff (3.5Å)',
          style: {
            fontSize: '11px',
            color: '#FF8800'
          }
        }
      }] : []
    },
    legend: {
      enabled: false
    },
    plotOptions: {
      line: {
        marker: {
          enabled: true,
          radius: 4
        },
        color: '#3B6EF5',
        lineWidth: 2
      }
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 8,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      formatter: function() {
        const anomalyInfo = this.point.isAnomaly ? '<br/><span style="color:#FF3B30">⚠️ Anomaly detected</span>' : ''
        return `<b>Frame ${this.x}</b><br/>Distance: ${this.y.toFixed(2)} Å${anomalyInfo}`
      }
    },
    series: [{
      name: 'Distance',
      data: chartData
    }]
  })
}

// Load distance data
const loadDistanceData = async () => {
  if (!dataStore.currentSystem) return
  
  loading.value = true
  error.value = null
  showAnomalyDetails.value = false
  
  try {
    const response = await api.getInteractionDistances(dataStore.currentSystem.id)
    distanceData.value = response
    
    await nextTick()
    updateDistanceChart()
    updateHistogramChart()
  } catch (err) {
    error.value = err.message || 'Failed to load distance data'
    console.error('Error loading distance data:', err)
  } finally {
    loading.value = false
  }
}

// Load atom pair data
const loadAtomPairData = async () => {
  if (!dataStore.currentSystem || !props.interactionData?.pair) return
  
  try {
    // Parse the pair (format: "A-LYS8 ↔ B-ASP45")
    const parts = props.interactionData.pair.split(' ↔ ')
    if (parts.length !== 2) return
    
    const parseId = (id) => {
      const match = id.match(/^([A-Z])-(.+?)(\d+)$/)
      if (match) {
        return { chain: match[1], name: match[2], num: match[3] }
      }
      return null
    }
    
    const res1 = parseId(parts[0])
    const res2 = parseId(parts[1])
    
    if (!res1 || !res2) return
    
    const params = {
      resName1: res1.name,
      resNum1: res1.num,
      chain1: res1.chain,
      resName2: res2.name,
      resNum2: res2.num,
      chain2: res2.chain
    }
    
    const response = await api.getAtomPairs(dataStore.currentSystem.id, params)
    atomPairData.value = response
  } catch (err) {
    console.error('Error loading atom pair data:', err)
    // Don't show error - atom pairs are supplementary data
  }
}

// Export data as CSV
const exportData = () => {
  if (!props.interactionData) return
  
  let csv = 'Frame,Status,Distance (Å),Type\n'
  
  for (let i = 1; i <= totalFrames.value; i++) {
    const status = frameHasInteraction(i) ? 'Present' : 'Absent'
    const dist = getFrameDistance(i)
    const distStr = dist !== null ? dist.toFixed(2) : ''
    const type = frameHasInteraction(i) ? props.interactionData.type : ''
    
    csv += `${i},${status},${distStr},${type}\n`
  }
  
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.interactionData.pair.replace(' ↔ ', '_')}_trajectory.csv`
  a.click()
  window.URL.revokeObjectURL(url)
}

watch(() => props.visible, (newVal) => {
  if (newVal && props.interactionData) {
    // Pre-select the frame that was clicked in the chart
    selectedFrame.value = props.interactionData.frame || null
    loadDistanceData()
    loadAtomPairData()
  }
})

watch(() => props.interactionData, () => {
  if (props.visible && props.interactionData) {
    selectedFrame.value = props.interactionData.frame || null
    loadDistanceData()
    loadAtomPairData()
  }
}, { deep: true })
</script>

<style scoped>
.trajectory-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.trajectory-modal-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 1400px;
  max-height: 90vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8ed;
}

.panel-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
}

.close-button {
  background: none;
  border: none;
  font-size: 32px;
  color: #6e6e73;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: #f5f5f7;
}

.panel-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.loading-state,
.error-state {
  padding: 60px 24px;
  text-align: center;
  color: #6e6e73;
}

.spinner {
  border: 3px solid #e8e8ed;
  border-top: 3px solid #3B6EF5;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.residue-info {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e8e8ed;
}

.residue-info h3 {
  margin: 0 0 12px 0;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.interaction-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 14px;
  color: #6e6e73;
}

.meta-item strong {
  color: #1d1d1f;
}

/* Connected Atoms Visualization */
.atom-connection-section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
}

.atom-connection-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.atom-connection-section.empty {
  text-align: center;
}

.no-atoms-msg {
  text-align: center;
  padding: 16px;
}

.no-atoms-msg p {
  margin: 0;
  color: #6e6e73;
  font-size: 13px;
}

.atom-connection-visual {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.atom-bond-card {
  background: white;
  border-radius: 10px;
  padding: 14px 18px;
  border: 1px solid #e8e8ed;
  transition: all 0.2s;
}

.atom-bond-card:hover {
  border-color: #3B6EF5;
  box-shadow: 0 2px 8px rgba(59, 110, 245, 0.1);
}

.bond-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 10px;
}

.atom-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  background: #f5f5f7;
  border-radius: 8px;
  min-width: 80px;
}

.atom-node.atom-1 {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.atom-node.atom-2 {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.atom-name {
  font-size: 16px;
  font-weight: 700;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

.atom-residue {
  font-size: 10px;
  color: #6e6e73;
  margin-top: 2px;
}

.bond-line {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 4px;
  position: relative;
}

.bond-type {
  position: absolute;
  top: -18px;
  font-size: 10px;
  font-weight: 600;
  color: #6e6e73;
  white-space: nowrap;
  background: white;
  padding: 2px 6px;
  border-radius: 4px;
}

.bond-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.bond-frequency {
  font-size: 12px;
  font-weight: 600;
}

.bond-frames {
  font-size: 11px;
  color: #6e6e73;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  border: 1px solid #d2d2d7;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6e6e73;
  font-weight: 500;
  margin-bottom: 4px;
}

.stat-sublabel {
  font-size: 12px;
  color: #6e6e73;
}

.section {
  margin-bottom: 32px;
}

.section h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.section-description {
  font-size: 13px;
  color: #6e6e73;
  margin: 0 0 12px 0;
}

.timeline-bar-container {
  position: relative;
  padding-bottom: 30px;
  margin-bottom: 16px;
}

.timeline-bar {
  display: flex;
  height: 32px;
  background: #e8e8ed;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.timeline-segment {
  height: 100%;
  background: #e8e8ed;
  transition: background-color 0.1s ease;
  border-right: 1px solid rgba(255, 255, 255, 0.3);
}

.timeline-segment:last-child {
  border-right: none;
}

.timeline-segment.has-interaction {
  background: #3B6EF5;
}

.timeline-segment.selected {
  background: #1d1d1f !important;
}

.timeline-segment:hover {
  opacity: 0.8;
}

.timeline-markers {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 20px;
}

.marker {
  position: absolute;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 600;
  color: #6e6e73;
}

.marker:first-child {
  transform: translateX(0);
}

.marker:last-child {
  transform: translateX(-100%);
}

.selected-marker {
  position: absolute;
  top: -8px;
  transform: translateX(-50%);
  z-index: 10;
  pointer-events: none;
}

.marker-line {
  width: 2px;
  height: 48px;
  background: #1d1d1f;
  margin: 0 auto;
}

.marker-label {
  background: #1d1d1f;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  margin-top: 4px;
}

.frame-details {
  background: #f5f5f7;
  padding: 16px;
  border-radius: 12px;
}

.frame-detail-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e8e8ed;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 14px;
  font-weight: 600;
  color: #6e6e73;
}

.detail-value {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.detail-value.present {
  color: #00AA00;
}

.detail-value.absent {
  color: #CC0000;
}

.chart-container {
  min-height: 300px;
  width: 100%;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f5f7;
  border-radius: 8px;
  font-size: 14px;
}

.event-icon {
  font-size: 18px;
}

.event-label {
  font-weight: 600;
  color: #1d1d1f;
  flex: 1;
}

.event-frame {
  color: #6e6e73;
  font-size: 12px;
}

.table-container {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f5f5f7;
  position: sticky;
  top: 0;
  z-index: 10;
}

th {
  padding: 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

td {
  padding: 12px;
  font-size: 14px;
  color: #1d1d1f;
  border-bottom: 1px solid #e8e8ed;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.status-badge.present {
  background: #00AA00;
}

.status-badge.absent {
  background: #CC0000;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding-top: 24px;
  border-top: 1px solid #e8e8ed;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 980px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.primary-btn {
  background: #1d1d1f;
  color: white;
}

.primary-btn:hover {
  background: #000000;
}

.secondary-btn {
  background: #f5f5f7;
  color: #1d1d1f;
}

.secondary-btn:hover {
  background: #e8e8ed;
}

/* Anomaly Detection Styles */
.anomaly-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #FFF5F5;
  border: 1px solid #FFCCCC;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #CC0000;
}

.anomaly-icon {
  font-size: 16px;
}

.anomaly-toggle {
  margin-left: auto;
  padding: 4px 12px;
  background: #FF3B30;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.anomaly-toggle:hover {
  background: #CC0000;
}

.anomaly-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  max-height: 150px;
  overflow-y: auto;
  padding: 8px;
  background: #fafafa;
  border-radius: 8px;
}

.anomaly-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e8e8ed;
}

.anomaly-item:hover {
  border-color: #FF3B30;
  background: #FFF5F5;
}

.anomaly-badge {
  font-size: 14px;
}

.anomaly-desc {
  flex: 1;
  color: #1d1d1f;
}

.anomaly-frame {
  color: #6e6e73;
  font-weight: 600;
}

/* Distance Histogram Styles */
.chart-container-small {
  min-height: 200px;
  width: 100%;
}

.distribution-stats {
  display: flex;
  gap: 24px;
  justify-content: center;
  margin-top: 12px;
  padding: 12px;
  background: #f5f5f7;
  border-radius: 8px;
}

.dist-stat {
  display: flex;
  gap: 6px;
  align-items: center;
}

.dist-label {
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
}

.dist-value {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
}

/* Interaction Type Analysis Styles */
.type-timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.type-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.type-label {
  width: 100px;
  font-size: 12px;
  font-weight: 600;
  color: #1d1d1f;
  text-align: right;
  flex-shrink: 0;
}

.type-bar {
  flex: 1;
  display: flex;
  height: 20px;
  background: #e8e8ed;
  border-radius: 4px;
  overflow: hidden;
}

.type-segment {
  height: 100%;
  background: #e8e8ed;
  transition: background-color 0.1s;
}

.type-segment.active {
  background: #3B6EF5;
}

.type-percent {
  width: 50px;
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  text-align: left;
}

.cooccurrence-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e8e8ed;
}

.cooccurrence-section h5 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.cooccurrence-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cooccurrence-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f5f5f7;
  border-radius: 8px;
}

.cooccurrence-types {
  width: 180px;
  font-size: 12px;
  font-weight: 600;
  color: #1d1d1f;
  flex-shrink: 0;
}

.cooccurrence-bar-container {
  flex: 1;
  height: 8px;
  background: #e8e8ed;
  border-radius: 4px;
  overflow: hidden;
}

.cooccurrence-bar {
  height: 100%;
  background: linear-gradient(90deg, #3B6EF5, #00AA00);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.cooccurrence-value {
  width: 100px;
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  text-align: right;
}
</style>

