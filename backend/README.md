# Backend

Flask REST API that serves PDB analysis data to the Vue.js frontend. Reads pre-computed system-level CSVs and metadata produced by the [engine](../engine/).

## Running

From the **project root**:
```bash
python run_backend.py
```

The API will be available at `http://localhost:5001`.

## API Endpoints

### Systems

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/systems` | List all available systems (name, frames, chains, job info) |
| `GET` | `/api/systems/<id>` | Get details for a specific system |
| `POST` | `/api/systems/<id>/rename` | Update display name (stored in `.metadata.json`) |

### Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/systems/<id>/interactions` | Aggregated interactions with consistency scores and type persistence |
| `GET` | `/api/systems/<id>/area` | Buried surface area per frame (total, polar, non-polar) |
| `GET` | `/api/systems/<id>/trends` | Interaction type counts per frame (18 types) |
| `GET` | `/api/systems/<id>/atom-pairs?resName1=...&resNum1=...&chain1=...&resName2=...&resNum2=...&chain2=...` | Atom-level detail for a specific residue pair |
| `POST` | `/api/systems/<id>/atom-pairs/batch` | Atom-level detail for multiple residue pairs in one request |
| `GET` | `/api/systems/<id>/interaction-distances` | Distance data for all interactions across all frames |
| `GET` | `/api/systems/<id>/distance-distributions?interaction_types=H-bond,Salt-bridge` | Distance distributions filtered by interaction type |
| `GET` | `/api/systems/<id>/conserved-islands` | Conserved island data from `_conserved_islands.json` |
| `GET` | `/api/systems/<id>/frame/<n>/pdb` | Serve a frame's PDB file (for Mol\* viewer) |

### Upload & Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a PDB file and start async processing |
| `GET` | `/api/status/<job_id>` | Poll processing status (progress %, step label) |
| `GET` | `/api/jobs` | List all jobs (active, completed, failed) |

#### Upload form fields

| Field | Default | Description |
|-------|---------|-------------|
| `file` | — | PDB file (required) |
| `job_name` | filename stem | Display name for the system |
| `email` | — | Owner email (stored in metadata) |
| `chain1` / `chain2` | `A` / `B` | Chain IDs |
| `interface_cutoff` | `5.0` | Interface selection cutoff (Å) |
| `start_frame` | `1` | First frame (1-indexed) |
| `end_frame` | `-1` | Last frame (-1 = all) |
| `frame_step` | `1` | Analyze every Nth frame |
| `reduce` | `false` | Use reduce version of CoCoMaps |

## Modules

### [`app.py`](app.py)
Flask application factory. Enables CORS, sets 2GB upload limit, registers the three route blueprints under `/api`.

### [`routes/systems.py`](routes/systems.py)
System discovery and management. Scans `systems/` for directories containing `frame_N/` folders, reads chain patterns from CSV filenames, and pulls job metadata from `_metadata.json`.

### [`routes/data.py`](routes/data.py)
Data retrieval — the largest module (721 lines). Reads from the aggregated CSVs (`_interactions.csv`, `_area.csv`, `_trends.csv`, `_atom_pairs.csv`) and `_conserved_islands.json`. Computes consistency scores, type persistence, atom-pair statistics, and distance distributions on the fly.

### [`routes/upload.py`](routes/upload.py)
Async file upload and processing. Saves the PDB to a temp directory, spawns a background thread running `engine.run_pipeline()`, and tracks progress via an in-memory dict persisted to `.jobs.json`.

## Configuration

Docker image selection (via `.env` or environment variables):
- `COCOMAPS_IMAGE_REDUCE` — Docker image with hydrogen addition (default: `andrpet/cocomaps-backend:0.0.19`)
- `COCOMAPS_IMAGE_NO_REDUCE` — Docker image without reduce (default: `sattamaltwaim/cocomaps-backend:no-reduce`)
- Per-upload override: send `reduce=true` or `reduce=false` in the upload form
