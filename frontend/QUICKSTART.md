# Vue.js Frontend - Quick Start Guide

## Phase 2 Complete! ✅

The Vue.js frontend structure has been created with all necessary components.

## Installation

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Run development server:**
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── charts/              # Chart components
│   │   │   ├── FilteredHeatmap.vue
│   │   │   ├── AreaChart.vue
│   │   │   ├── LineChart.vue
│   │   │   ├── InteractionConservationMatrix.vue
│   │   │   └── ViolinChart.vue
│   │   ├── Sidebar.vue
│   │   ├── ChartSelector.vue
│   │   ├── ControlsPanel.vue
│   │   ├── ChartContainer.vue
│   │   └── UploadModal.vue
│   ├── stores/
│   │   └── dataStore.js         # Pinia store for state management
│   ├── services/
│   │   └── api.js               # API client for Flask backend
│   ├── utils/
│   │   ├── constants.js          # Color schemes, interaction types
│   │   └── chartHelpers.js      # Chart utility functions
│   ├── views/
│   │   └── Home.vue             # Main view
│   ├── router/
│   │   └── index.js             # Vue Router config
│   ├── App.vue
│   └── main.js
├── package.json
├── vite.config.js
└── index.html
```

## Features Implemented

✅ **Component Architecture**
- Modular Vue components
- Reusable chart components
- Separation of concerns

✅ **State Management**
- Pinia store for global state
- Reactive data loading
- UI state management

✅ **API Integration**
- Axios-based API client
- Error handling
- Loading states

✅ **Chart Components**
- Filtered Heatmap
- Area Chart
- Line Chart (Interaction Trends)
- Interaction Conservation Matrix
- Violin Chart (Distance Distribution)

✅ **UI Components**
- Sidebar with system selection
- Chart selector
- Controls panel
- Upload modal

## Next Steps

1. **Start the backend:**
```bash
python run_backend.py
```

2. **Start the frontend:**
```bash
cd frontend
npm install
npm run dev
```

3. **Test the application:**
- Open `http://localhost:5173`
- Select a system from the sidebar
- Switch between chart types
- Test all functionality

## Development Notes

- The frontend proxies API requests to `http://localhost:5000` (configured in `vite.config.js`)
- All chart components use Highcharts
- State is managed centrally in Pinia store
- Components are reactive and update automatically when data changes

