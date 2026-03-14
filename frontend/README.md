# Frontend

Vue 3 single-page application for visualizing PDB trajectory analysis results. Communicates with the Flask [backend](../backend/) via REST API.

## Running

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

The Vite dev server proxies `/api` requests to `http://localhost:5001` (Flask backend).

## Routes

| Path | View | Description |
|------|------|-------------|
| `/` | `LandingPage` | Upload PDB, select chains, configure analysis, track processing |
| `/analysis/:jobId` | `Home` | Main analysis dashboard with charts and controls |
| `/jobs` | `JobsPage` | Sortable/searchable list of all jobs (active, completed, failed) |
| `/about` | `AboutPage` | Interaction type reference (18 types with criteria and colors) |
| `/references` | `ReferencesPage` | Citations (CoCoMaps 2.0), BibTeX, software dependencies |

## Architecture

```
src/
├── views/                      # Page-level components (5)
├── components/                 # Reusable UI components (15)
│   └── charts/                 # Chart visualizations (7)
├── composables/                # Vue composables
│   └── useConservationStatistics.js
├── services/
│   └── api.js                  # Axios API client (all backend endpoints)
├── stores/
│   └── dataStore.js            # Pinia store (systems, interactions, area, trends, islands)
├── utils/
│   ├── constants.js            # 18 interaction types (id, label, keywords)
│   ├── chartHelpers.js         # Color palette, type matching, residue formatting
│   └── highchartsConfig.js     # Shared Highcharts export configuration
├── router/
│   └── index.js                # Vue Router (5 routes, base: /BioTools/trajectory_analysis/)
├── App.vue                     # Root component
└── main.js                     # App entry (Pinia, Router, Highcharts modules)
```

## Key Components

### Analysis Dashboard (`Home.vue`)
System sidebar, chart selector tabs, dynamic chart container, conservation threshold slider, interaction type filters, stats panel, and conservation analysis summary.

### Charts (6 types, switchable via tabs)

| Chart | Library | Description |
|-------|---------|-------------|
| Interaction Conservation Matrix | Highcharts heatmap | Residue pair × frame timeline |
| Filtered Heatmap | Highcharts heatmap | Residue × residue conservation matrix |
| Interaction Trends | Highcharts line | Interaction type counts per frame |
| Area Composition | Highcharts area | BSA (total/polar/non-polar) with ±σ bands |
| Distance Distribution | Plotly violin | Per-interaction-type distance distributions |
| Conserved Islands | Custom | Island summary tables + force-directed graph |

### Deep-Dive Modals
- **InteractionTrajectoryModal** — Distance trajectory chart, interaction type timeline, atom connections per frame, frame-by-frame data table
- **AtomPairExplorer** — Atom pair frequency chart, frame timeline, transitions, conservation threshold slider

### 3D Structure
**MolStarViewer** — Embeds Mol\* for viewing frame PDB structures with residue highlighting.

## Data Flow

1. `LandingPage` uploads PDB via `api.uploadFileWithOptions()`, polls `api.getStatus()` until complete
2. On completion, redirects to `/analysis/:jobId`
3. `Home` loads systems, resolves jobId → systemId, calls `dataStore.setCurrentSystem()`
4. `dataStore` fetches interactions, area, trends, and conserved islands in parallel
5. `filteredInteractions` getter applies conservation threshold + interaction type filters
6. Charts and panels reactively update via Pinia store

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:5001/api` | Backend API base URL |
| `base` (vite.config.js) | `/BioTools/trajectory_analysis/` | Deploy path prefix |

## Tech Stack

- **Vue 3** + Composition API (`<script setup>`)
- **Pinia** for state management
- **Vue Router** with HTML5 history mode
- **Highcharts** + `highcharts-vue` for interactive charts (heatmaps, line, area)
- **Plotly.js** for violin plots
- **Mol\*** for 3D molecular visualization
- **Axios** for HTTP requests
- **Vite** for dev server and builds
- **Sass** for component styles
