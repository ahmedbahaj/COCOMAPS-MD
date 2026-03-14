# CLI

Command-line interface for the PDB Trajectory Analysis pipeline. A local, distributable alternative to the web GUI — runs the same analysis engine with interactive configuration, rich terminal output, and publication-ready chart generation.

## Quick Start

```bash
# Run with defaults (prompts for missing info)
python -m cli my_protein.pdb

# Specify everything upfront
python -m cli my_protein.pdb -c A B -o results/ -i 7.0 -t 70

# Interactive customization mode
python -m cli my_protein.pdb -C
```

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `pdb_file` | Input PDB file (prompted if omitted) | — |
| `-c A B` | Chain IDs to analyze | Auto-detected |
| `-o DIR` | Output directory | `systems/<pdb_name>` |
| `-r` | Use reduce version of CoCoMaps | Off |
| `-i` | Interface selection cutoff (Å) | `5.0` |
| `-w` | Bridging water cutoff (Å) | Same as `-i` |
| `-p FILE` | JSON file with CoCoMaps parameter overrides | — |
| `-s N` | Start frame (1-indexed) | `1` |
| `-e N` | End frame (1-indexed, inclusive) | Last frame |
| `-n N` | Frame step (every Nth frame) | `1` |
| `-t N` | Conservation threshold % for charts (0–100) | `50` |
| `-u UNIT` | Time axis label (fs, ps, ns, etc.) | `Frame` |
| `-C` | Enter interactive customization before running | Off |

## What Happens

The CLI runs a 5-step pipeline with rich progress bars, then generates charts:

```
1. Split PDB into frames (with optional interface selection)
2. Create CoCoMaps input JSON files
3. Run CoCoMaps Docker analysis on each frame
4. Run conserved island analysis
5. Aggregate per-frame CSVs into system-level files
   └──→ Generate publication-ready PNG charts
```

## Modules

### [`main.py`](main.py)
Entry point. Parses CLI arguments, inspects the PDB file (frame count, chains, atoms), builds pipeline and chart configuration, then orchestrates the run. Supports both non-interactive (flags) and interactive (`-C`) modes.

### [`runner.py`](runner.py)
Executes the analysis pipeline with `rich` progress bars. Handles frame splitting, CoCoMaps Docker execution (with workaround for paths with spaces), conserved island analysis, and CSV aggregation. Delegates to the `engine` package for core logic.

### [`charts.py`](charts.py)
Generates publication-ready PNG charts using two rendering backends:

- **Highcharts** (via `highcharts-export-server` Node.js CLI) for:
  - Interaction Trends — line chart of interaction type counts per frame
  - Area Composition — BSA (buried surface area) with optional ±σ bands
  - Interaction Heatmap — residue × residue conservation matrix
  - Conservation Matrix — frame × pair-type timeline heatmap
- **Plotly + Kaleido** (pure Python) for:
  - Distance Distribution — violin plots per interaction type

Also prints **Conserved Islands** summary tables to the terminal via `rich`.

### [`prompts.py`](prompts.py)
Interactive customization using `rich`. Provides:
- `show_config_summary()` — display-only config tables (pipeline, CoCoMaps, charts)
- `interactive_customize()` — numbered section picker for editing pipeline parameters, CoCoMaps thresholds, and per-chart toggle/options

### [`constants.py`](constants.py)
Single source of truth for shared constants (mirrors the frontend's `constants.js` and `chartHelpers.js`):
- **18 interaction types** with IDs, labels, keywords, and trend labels
- **Color palette** — RGB values for each interaction type
- **Default CoCoMaps parameters** — distance/angle thresholds
- **Default chart options** — enabled charts, conservation thresholds, display settings
- **Trends CSV keys** — column ordering for `_trends.csv`

### [`inspect_pdb.py`](inspect_pdb.py)
Lightweight PDB file inspection. Counts frames by scanning `MODEL` records (handles variable atom counts), loads the first frame for metadata (chains, atom count, residue count). Used by `main.py` to auto-detect structure properties.

## Chart Generation Requirements

For Highcharts-based PNGs:
```bash
npm install -g highcharts-export-server
```

For violin plots:
```bash
pip install plotly kaleido
```
