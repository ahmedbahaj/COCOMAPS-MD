# PDB Analysis Backend API

Flask REST API for serving PDB analysis data to the Vue.js frontend.

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the server:**
```bash
# From project root
python run_backend.py

# Or from backend directory
cd backend
python run.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Systems
- `GET /api/systems` - List all available systems
- `GET /api/systems/<system_id>` - Get system details

### Data
- `GET /api/systems/<system_id>/interactions` - Get all interaction data
- `GET /api/systems/<system_id>/area` - Get buried surface area data
- `GET /api/systems/<system_id>/trends` - Get interaction type trends

### Upload
- `POST /api/upload` - Upload and process PDB file
- `GET /api/status/<pdb_id>` - Get processing status

#### Selecting the CoCoMaps Docker image
- Default with REDUCE: `andrpet/cocomaps-backend:0.0.19`.
- Default no-reduce: `sattamaltwaim/cocomaps-backend:no-reduce` (pulled from Docker Hub).
- Environment overrides:
  - `COCOMAPS_IMAGE_REDUCE` (default `andrpet/cocomaps-backend:0.0.19`)
  - `COCOMAPS_IMAGE_NO_REDUCE` (default `sattamaltwaim/cocomaps-backend:no-reduce`)
  - `COCOMAPS_USE_REDUCE` (`true`/`false`) for the CLI helper in `run.py`.
- Per-upload override: send form/query field `reduce=false` to use the no-reduce image for that job.

## Project Structure

```
backend/
├── app.py              # Main Flask application
├── routes/
│   ├── systems.py     # System management endpoints
│   ├── data.py        # Data retrieval endpoints
│   └── upload.py      # Upload and processing endpoints
└── requirements.txt   # Python dependencies
```

