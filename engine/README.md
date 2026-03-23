# Engine

Core analysis pipeline for processing PDB structures through [CoCoMaps](http://www.molnac.unisa.it/BioTools/cocomaps/) and detecting conserved interaction patterns across molecular dynamics (MD) trajectory frames.

## What It Does

This package takes a multi-model PDB file and:

1. **Splits** it into individual frames
2. **Selects** interface residues, bridging waters, and metals between two protein chains
3. **Runs** CoCoMaps interaction analysis on each frame via Docker
4. **Detects** conserved interaction islands — residue clusters that persist across frames
5. **Aggregates** all per-frame results into system-level CSVs and metadata

## Modules

### [`analyze_pdb.py`](analyze_pdb.py)
Main pipeline orchestrator and CLI entry point. Handles all file I/O: frame splitting, PDB writing, Docker execution, and progress reporting.

**Key functions:**
- `run_pipeline()` — Full pipeline entry point (used by both CLI and web backend)
- `process_frames()` — Splits PDB into frames with optional interface selection
- `run_cocomaps_analysis()` — Executes CoCoMaps Docker containers on each frame
- `create_input_jsons()` — Generates CoCoMaps configuration files

**CLI usage:**
```bash
# Basic analysis
python -m engine.analyze_pdb systems/my_protein.pdb

# Custom cutoff and chains
python -m engine.analyze_pdb systems/my_protein.pdb --interface-cutoff 7.0 -c A B

# With hydrogen addition (slower)
python -m engine.analyze_pdb systems/my_protein.pdb --use-reduce
```

### [`viewer_pdb.py`](viewer_pdb.py)
Web uploads only: builds `frame_1/frame_1_viewer.pdb` from the original uploaded PDB’s first processed frame (before interface trimming), removing waters and metals that never appear in `_interactions.csv`. Not invoked from the CLI.

### [`interface_selector.py`](interface_selector.py)
Pure selection logic — no file I/O. Identifies which atoms to keep for analysis.

- **Interface residues**: Residues within a distance cutoff of the partner chain
- **Bridging waters**: Water molecules within cutoff of *both* chains
- **Interface metals**: Metal ions bridging both chains (same criteria as waters)

Uses MDAnalysis distance arrays for efficient computation across all atom pairs.

### [`conserved_islands.py`](conserved_islands.py)
Detects groups of residues that maintain interactions across a high fraction of frames.

**Algorithm:**
1. Count how many frames each direct A–B residue pair interacts in
2. Build a graph keeping only edges where `count / total_frames ≥ threshold` (default: 70%)
3. Extract connected components — these are the conserved islands
4. Output includes per-residue connectivity data for visualization in Mol\*

**Standalone CLI:**
```bash
python conserved_islands.py systems/1ULL --threshold 0.80 --min-size 3
```

### [`aggregate_csv.py`](aggregate_csv.py)
Combines per-frame CoCoMaps output into system-level files:

| Output File | Content |
|-------------|---------|
| `_interactions.csv` | One row per residue pair per frame, with normalized interaction types |
| `_area.csv` | Buried surface area (BSA) per frame: total, polar, non-polar |
| `_trends.csv` | Interaction type counts per frame (H-bonds, salt bridges, π-π, etc.) |
| `_atom_pairs.csv` | Atom-level detail: specific atoms, distances, angles per interaction |
| `_metadata.json` | Frame count, chain pattern, and auto-generated job ID with expiry |

Handles 17+ interaction types with a normalization layer to map various CoCoMaps labels to canonical names.

### [`job_id.py`](job_id.py)
Generates unique job identifiers in the format `YYYYDDD-RRRRRRRR` (year + day-of-year + 8 random alphanumeric characters). Manages creation timestamps and 60-day expiry for metadata.

## Pipeline Flow

```
Input PDB
    │
    ▼
process_frames()          Split into frame_1/, frame_2/, ...
    │                     Select interface atoms per frame
    ▼
create_input_jsons()      Write CoCoMaps config for each frame
    │
    ▼
run_cocomaps_analysis()   Docker: CoCoMaps on each frame → CSVs
    │
    ▼
run_conserved_islands()   Graph analysis → _conserved_islands.json
    │
    ▼
aggregate_system()        Combine all frames → system-level CSVs
```

## Configuration

Settings are loaded from a `.env` file in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `COCOMAPS_USE_REDUCE` | `false` | Add hydrogens before analysis |
| `COCOMAPS_IMAGE_REDUCE` | `andrpet/cocomaps-backend:0.0.19` | Docker image (with reduce) |
| `COCOMAPS_IMAGE_NO_REDUCE` | `sattamaltwaim/cocomaps-backend:no-reduce` | Docker image (without reduce) |
| `DEFAULT_INTERFACE_CUTOFF` | `5.0` | Distance cutoff in Ångströms |
| `DEFAULT_CHAINS` | `A,B` | Chain IDs to analyze |
| `SELECT_INTERFACE` | `true` | Enable interface selection |
