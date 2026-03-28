# PDB Analysis Application

A modern web application for analyzing protein-protein interactions from PDB files using molecular dynamics trajectory data.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn
- Docker Desktop (required for CoCoMaps analysis)

> **Apple Silicon (M Series) Mac note:** The CoCoMaps Docker images are built for `linux/amd64` only. Docker Desktop on Apple Silicon runs them automatically via Rosetta 2 emulation — no extra setup needed. The `--platform linux/amd64` flag is already included in the pipeline commands.
>
> **Linux ARM64 note:** Docker Engine on Linux does not include built-in amd64 emulation. You must install QEMU first:
> ```bash
> docker run --privileged --rm tonistiigi/binfmt --install amd64
> ```
> After that one-time setup, the pipeline will work the same as on amd64 machines (via emulation).

### Download Systems Data

The `systems/` folder contains large PDB analysis data files that are too large to include in the repository. You need to download and extract this data before running the application:

1. **Download systems.zip** from [Google Drive](https://drive.google.com/file/d/1iUyi2du7Fc5A9tcOVZidFzFf9EJpMV11/view?usp=sharing)

2. **Extract the archive** to the repository root:
   ```bash
   unzip systems.zip -d .
   ```

   This will create the `systems/` folder in the root directory with all the analysis data.

> **Note:** The systems folder is excluded from version control via `.gitignore` due to its large size. Make sure to extract it to the repository root directory.

### Backend Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the Flask backend:**
```bash
python run_backend.py
```

The API will be available at `http://localhost:5000`

### Frontend Setup

1. **Install Node dependencies:**
```bash
cd frontend
npm install
```

2. **Run the development server:**
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## 📁 Project Structure

```
PDB-examples/
├── backend/              # Flask REST API
│   ├── app.py           # Main Flask application
│   ├── routes/          # API route handlers
│   │   ├── systems.py   # System management
│   │   ├── data.py      # Data retrieval
│   │   └── upload.py    # File upload & processing
│
├── requirements.txt     # Python dependencies (project root)
│
├── frontend/            # Vue.js 3 frontend
│   ├── src/
│   │   ├── components/  # Vue components
│   │   │   ├── charts/  # Chart visualizations
│   │   │   ├── Sidebar.vue
│   │   │   ├── ChartSelector.vue
│   │   │   ├── ControlsPanel.vue
│   │   │   ├── ChartContainer.vue
│   │   │   └── UploadModal.vue
│   │   ├── stores/      # Pinia state management
│   │   ├── services/    # API client
│   │   ├── utils/       # Utilities & constants
│   │   └── views/       # Page views
│   └── package.json     # Node dependencies
│
├── archive/             # Archived legacy files
│   └── index.html       # Original single-file HTML app
│
└── [system folders]/    # PDB analysis data (1ULL, md_mohit_protein, etc.)
```

## 🎯 Features

### Data Visualizations
- **Filtered Heatmap**: Dynamic heatmap with consistency threshold
- **Heatmap**: 2D matrix of interaction consistency
- **Area Chart**: Buried surface area across frames (Total, Polar, Non-Polar)
- **Interaction Trends**: Line chart showing interaction type counts over time

### Interactive Controls
- Consistency threshold slider (0-100%)
- Color scheme selector (Classic, Vibrant, Pastel, Dark, Scientific)
- Interaction type filters with select all/deselect all
- Logarithmic scale toggle for area and trend charts

### File Management
- Upload PDB files for analysis
- Automatic system detection from frame folders
- Real-time processing status updates

## 🛠️ Technology Stack

### Backend
- **Flask**: Python web framework
- **Flask-CORS**: Cross-origin resource sharing
- **MDAnalysis**: Molecular dynamics analysis
- **pandas**: Data manipulation

### Frontend
- **Vue.js 3**: Progressive JavaScript framework
- **Pinia**: State management
- **Vue Router**: Client-side routing
- **Highcharts**: Interactive charting library
- **Axios**: HTTP client
- **Vite**: Build tool and dev server

## 📖 API Documentation

### Systems
- `GET /api/systems` - List all available systems
- `GET /api/systems/<system_id>` - Get system details

### Data
- `GET /api/systems/<system_id>/interactions` - Get interaction data with consistency scores
- `GET /api/systems/<system_id>/area` - Get buried surface area data
- `GET /api/systems/<system_id>/trends` - Get interaction type trends

### Upload
- `POST /api/upload` - Upload and process PDB file
- `GET /api/status/<pdb_id>` - Get processing status

## 🔧 Development

### Backend Development
```bash
# Run with auto-reload
python run_backend.py

# Or use Flask's development server
cd backend
python run.py
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Building for Production
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`

## 📝 Migration Notes

This application was migrated from a single-file HTML application to a modern Vue.js + Flask architecture. The original `index.html` has been archived in the `archive/` folder.

See `MIGRATION_SUMMARY.md` for detailed migration information.
