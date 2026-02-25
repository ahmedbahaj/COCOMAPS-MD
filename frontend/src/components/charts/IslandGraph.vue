<template>
  <div class="island-graph" :class="{ expanded }">
    <svg
      class="graph-svg"
      :viewBox="`0 0 ${viewBoxWidth} ${viewBoxHeight}`"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- Edges -->
      <g class="edges">
        <line
          v-for="edge in edges"
          :key="edge.id"
          :x1="edge.source.x"
          :y1="edge.source.y"
          :x2="edge.target.x"
          :y2="edge.target.y"
          class="edge-line"
        >
          <title>
            {{ edge.source.label }} ↔ {{ edge.target.label }}
          </title>
        </line>
      </g>

      <!-- Nodes -->
      <g class="nodes">
        <g
          v-for="node in nodes"
          :key="node.id"
          class="node-group"
        >
          <circle
            :cx="node.x"
            :cy="node.y"
            :r="nodeRadius"
            class="node-circle"
            :data-chain="node.chain"
          />
          <text
            :x="node.x + (node.chainIndex === 0 ? -nodeLabelOffset : nodeLabelOffset)"
            :y="node.y + 4"
            class="node-label"
            :class="{
              'align-right': node.chainIndex === 0,
              'align-left': node.chainIndex !== 0
            }"
          >
            {{ node.label }}
          </text>
          <title>
            {{ node.label }}
          </title>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  island: {
    type: Object,
    required: true
  },
  expanded: {
    type: Boolean,
    default: false
  }
})

const viewBoxWidth = 800
const minHeight = 260
const verticalPadding = 40
const nodeRadius = 8
const rowHeight = 40
const horizontalPadding = 80
const nodeLabelOffset = 14

const viewBoxHeight = computed(() => {
  const residues = props.island?.residues || []
  if (!residues.length) return minHeight

  const chainOrder = Array.from(
    new Set(residues.map(r => r.chain).filter(Boolean))
  )
  if (!chainOrder.length) return minHeight

  const byChain = new Map()
  chainOrder.forEach(chain => {
    byChain.set(
      chain,
      residues
        .filter(r => r.chain === chain)
        .sort((a, b) => (a.resNum || 0) - (b.resNum || 0))
    )
  })

  const maxCount = Math.max(
    ...Array.from(byChain.values()).map(list => list.length || 0)
  )

  return maxCount > 1
    ? Math.max(minHeight, verticalPadding * 2 + (maxCount - 1) * rowHeight)
    : minHeight
})

const nodes = computed(() => {
  const residues = props.island?.residues || []
  if (!residues.length) return []

  // Group residues by chain (e.g. A on left, B on right)
  const chainOrder = Array.from(
    new Set(residues.map(r => r.chain).filter(Boolean))
  ).sort()

  if (!chainOrder.length) return []

  const byChain = new Map()
  chainOrder.forEach(chain => {
    byChain.set(
      chain,
      residues
        .filter(r => r.chain === chain)
        .sort((a, b) => (a.resNum || 0) - (b.resNum || 0))
    )
  })

  const height = viewBoxHeight.value

  const colCount = chainOrder.length
  const usableWidth =
    colCount > 1
      ? viewBoxWidth - 2 * horizontalPadding
      : viewBoxWidth - 2 * horizontalPadding

  const chainX = new Map()
  chainOrder.forEach((chain, idx) => {
    let x
    if (colCount === 1) {
      x = viewBoxWidth / 2
    } else if (colCount === 2) {
      x = idx === 0 ? horizontalPadding : viewBoxWidth - horizontalPadding
    } else {
      x = horizontalPadding + (idx * usableWidth) / (colCount - 1)
    }
    chainX.set(chain, x)
  })

  const allNodes = []
  chainOrder.forEach((chain, chainIdx) => {
    const list = byChain.get(chain) || []
    const nodeCount = list.length || 1
    list.forEach((res, idx) => {
      const y =
        nodeCount > 1
          ? verticalPadding + (idx * (height - 2 * verticalPadding)) / (nodeCount - 1)
          : height / 2
      allNodes.push({
        id: `${chain}:${res.resNum}`,
        chain,
        chainIndex: chainIdx,
        resNum: res.resNum,
        resName: res.resName,
        x: chainX.get(chain),
        y,
        label: `${chain}:${res.resNum} ${res.resName || ''}`.trim()
      })
    })
  })

  return allNodes
})

const edges = computed(() => {
  const residues = props.island?.residues || []
  if (!residues.length) return []

  const nodeMap = new Map()
  nodes.value.forEach(n => {
    nodeMap.set(n.id, n)
  })

  const seen = new Set()
  const result = []

  for (const res of residues) {
    const fromId = `${res.chain}:${res.resNum}`
    const fromNode = nodeMap.get(fromId)
    if (!fromNode || !Array.isArray(res.connectedTo)) continue

    for (const conn of res.connectedTo) {
      const toId = `${conn.chain}:${conn.resNum}`
      const toNode = nodeMap.get(toId)
      if (!toNode) continue

      // undirected edge: avoid duplicates
      const key =
        fromId < toId ? `${fromId}__${toId}` : `${toId}__${fromId}`
      if (seen.has(key)) continue
      seen.add(key)

      result.push({
        id: key,
        source: fromNode,
        target: toNode
      })
    }
  }

  return result
})
</script>

<style scoped>
.island-graph {
  width: 100%;
  padding: 12px 20px 20px;
  box-sizing: border-box;
  position: relative;
}

.graph-svg {
  width: 100%;
  height: 420px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e5e5ea;
}

.island-graph.expanded .graph-svg {
  height: 680px;
}

.edge-line {
  stroke: #c7c7cc;
  stroke-width: 1.5;
}

.node-group {
  cursor: default;
}

.node-circle {
  stroke: #ffffff;
  stroke-width: 2;
  fill: #ff9500; /* default: non-A chains */
}

.node-circle[data-chain='A'] {
  fill: #007aff; /* chain A always blue */
}

.node-label {
  font-size: 16px;
  font-weight: bold;
  fill: #1d1d1f;
}

.node-label.align-right {
  text-anchor: end;
}

.node-label.align-left {
  text-anchor: start;
}
</style>

