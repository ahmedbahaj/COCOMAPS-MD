"""
Chart generation — server-side PNG export.

• Highcharts charts → via highcharts-export-server (Node.js CLI)
• Violin plots     → via plotly + kaleido (pure Python)
• Conserved Islands → printed to terminal via rich tables
"""
import csv
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

from cli.constants import (
    INTERACTION_TYPES,
    INTERACTION_COLOR_RULES,
    TRENDS_KEYS,
    find_interaction_color,
    rgb_to_hex,
    get_interaction_color_hex,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(path: str) -> list[dict]:
    """Read a CSV file into a list of dicts."""
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _read_json(path: str) -> dict:
    """Read a JSON file."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _export_highcharts_png(chart_options: dict, output_path: str, width: int = 1600, scale: int = 2):
    """
    Export a Highcharts chart to PNG using highcharts-export-server.

    Writes the options JSON to a temp file, invokes the CLI, and saves the PNG.
    """
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    ) as tmp:
        json.dump(chart_options, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    try:
        cmd = [
            'highcharts-export-server',
            '--infile', tmp_path,
            '--outfile', output_path,
            '--type', 'png',
            '--width', str(width),
            '--scale', str(scale),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            console.print(f"  [red]Export error:[/red] {result.stderr[:200]}")
            return False
        return True
    except FileNotFoundError:
        console.print(
            "[red]Error: highcharts-export-server not found.[/red]\n"
            "  Install it with: [bold]npm install -g highcharts-export-server[/bold]"
        )
        return False
    except subprocess.TimeoutExpired:
        console.print("[red]Export timed out.[/red]")
        return False
    finally:
        os.unlink(tmp_path)


def _matches_selected_types(types_string: str, excluded_type_ids: set) -> bool:
    """Check if an interaction type string matches included types (not excluded)."""
    types_lower = types_string.lower()
    for itype in INTERACTION_TYPES:
        if itype['id'] in excluded_type_ids:
            continue
        for kw in itype['keywords']:
            if kw.lower() in types_lower:
                return True
    return False


def _aggregate_interactions(system_dir: str) -> list[dict]:
    """
    Read raw _interactions.csv (per-frame rows) and aggregate into
    per-residue-pair entries with computed consistency.

    Mirrors backend data.py `_get_interactions_from_csv` exactly.

    Returns list of dicts with keys:
        resName1, resNum1, chain1, resName2, resNum2, chain2,
        consistency (float 0-1), types (set of type strings),
        typePersistence (dict type->float)
    """
    interactions_file = Path(system_dir) / '_interactions.csv'
    metadata_file = Path(system_dir) / '_metadata.json'

    if not interactions_file.exists():
        return []

    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 1)

    rows = _read_csv(str(interactions_file))

    # Group by residue pair
    pair_map = {}
    for row in rows:
        r1 = f"{row.get('resName1','')}{row.get('resNum1','')}_{row.get('chain1','')}"
        r2 = f"{row.get('resName2','')}{row.get('resNum2','')}_{row.get('chain2','')}"
        key = f"{r1}__{r2}"
        frame_num = int(row.get('frame', 0))

        if key not in pair_map:
            pair_map[key] = {
                'resName1': row.get('resName1', ''),
                'resNum1': row.get('resNum1', ''),
                'chain1': row.get('chain1', ''),
                'resName2': row.get('resName2', ''),
                'resNum2': row.get('resNum2', ''),
                'chain2': row.get('chain2', ''),
                'frames': set(),
                'types': set(),
                'typeFrames': {},
            }

        pair_map[key]['frames'].add(frame_num)
        for t in (row.get('types') or '').split(';'):
            t = t.strip()
            if t:
                pair_map[key]['types'].add(t)
                if t not in pair_map[key]['typeFrames']:
                    pair_map[key]['typeFrames'][t] = set()
                pair_map[key]['typeFrames'][t].add(frame_num)

    # Build aggregated list
    result = []
    for key, entry in pair_map.items():
        consistency = len(entry['frames']) / total_frames if total_frames > 0 else 0
        type_persistence = {
            t: len(frames) / total_frames
            for t, frames in entry['typeFrames'].items()
        }
        result.append({
            'resName1': entry['resName1'],
            'resNum1': entry['resNum1'],
            'chain1': entry['chain1'],
            'resName2': entry['resName2'],
            'resNum2': entry['resNum2'],
            'chain2': entry['chain2'],
            'consistency': consistency,
            'types': entry['types'],
            'typePersistence': type_persistence,
        })

    result.sort(key=lambda x: x['consistency'], reverse=True)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Chart builders
# ─────────────────────────────────────────────────────────────────────────────

def _common_chart_style() -> dict:
    """Common Highcharts styling matching the GUI."""
    return {
        'chart': {
            'backgroundColor': '#ffffff',
        },
        'credits': {'enabled': False},
        'title': {
            'style': {
                'fontSize': '24px',
                'fontWeight': '600',
                'color': '#1d1d1f',
            }
        },
    }


def generate_interaction_trends(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    time_unit: str | None = None,
    log_scale: bool = False,
) -> bool:
    """Generate Interaction Trends line chart PNG."""
    trends_file = Path(system_dir) / '_trends.csv'
    metadata_file = Path(system_dir) / '_metadata.json'

    if not trends_file.exists():
        console.print("  [yellow]Warning: _trends.csv not found, skipping trends chart[/yellow]")
        return False

    # Read metadata for frame numbers
    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 0)
    frame_numbers = metadata.get('frameNumbers', [])

    # Read trends CSV
    rows = _read_csv(str(trends_file))
    if not rows:
        return False

    # Build data per interaction type
    # The trends CSV has columns: frame, and one per trend key
    fieldnames = list(rows[0].keys())

    # Use actual frame numbers from CSV rows
    if not frame_numbers:
        frame_numbers = [int(r.get('frame', i + 1)) for i, r in enumerate(rows)]

    categories = [str(fn) for fn in frame_numbers]

    # Build series
    series = []
    for itype in INTERACTION_TYPES:
        trend_key = itype['trendLabel']
        # Try to find the matching column
        col_name = None
        for fn in fieldnames:
            if fn.strip() == trend_key:
                col_name = fn
                break

        data = []
        has_nonzero = False
        if col_name:
            for row in rows:
                val = row.get(col_name, '0')
                try:
                    v = int(float(val))
                except (ValueError, TypeError):
                    v = 0
                if log_scale and v == 0:
                    data.append(None)
                else:
                    data.append(v)
                if v > 0:
                    has_nonzero = True
        else:
            data = [None] * len(rows)

        color = get_interaction_color_hex(itype['label'])
        series.append({
            'name': itype['label'],
            'data': data if has_nonzero else [],
            'color': color,
            'lineWidth': 2,
            'marker': {'enabled': has_nonzero, 'radius': 2.5},
            'showInLegend': True,
        })

    # Sort: active series first
    series.sort(key=lambda s: 0 if any(v and v > 0 for v in s['data']) else 1)

    x_title = f'Time ({time_unit})' if time_unit else 'Frame'

    chart_options = {
        **_common_chart_style(),
        'chart': {
            'type': 'line',
            'backgroundColor': '#ffffff',
            'height': 650,
            'width': 1600,
        },
        'title': {
            'text': f'{system_name} - Interaction Type Trends Across Frames',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'xAxis': {
            'categories': categories,
            'title': {
                'text': x_title,
                'style': {'fontSize': '15px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '12px', 'fontWeight': '500', 'color': '#1d1d1f'}},
        },
        'yAxis': {
            'type': 'logarithmic' if log_scale else 'linear',
            'title': {
                'text': f'Number of Interactions{"- Log Scale" if log_scale else ""}',
                'style': {'fontSize': '15px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '12px', 'fontWeight': '500', 'color': '#1d1d1f'}},
            'min': 0.1 if log_scale else 0,
        },
        'legend': {
            'align': 'right',
            'verticalAlign': 'middle',
            'layout': 'vertical',
            'itemStyle': {'fontSize': '13px', 'fontWeight': '500', 'color': '#1d1d1f'},
        },
        'plotOptions': {
            'line': {
                'lineWidth': 2,
                'states': {'hover': {'lineWidth': 3}},
                'marker': {'enabled': True, 'radius': 2.5},
            }
        },
        'series': series,
    }

    return _export_highcharts_png(chart_options, output_path)


def generate_area_chart(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    time_unit: str | None = None,
    show_stats: bool = True,
    show_percentages: bool = False,
) -> bool:
    """Generate Area Composition (BSA) line chart PNG."""
    area_file = Path(system_dir) / '_area.csv'
    if not area_file.exists():
        console.print("  [yellow]Warning: _area.csv not found, skipping area chart[/yellow]")
        return False

    rows = _read_csv(str(area_file))
    if not rows:
        return False

    # Sort by frame number
    rows.sort(key=lambda r: int(r.get('frame', 0)))

    categories = [str(r.get('frame', '')) for r in rows]

    def safe_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    total_bsa = [safe_float(r.get('totalBSA')) for r in rows]
    polar_bsa = [safe_float(r.get('polarBSA')) for r in rows]
    nonpolar_bsa = [safe_float(r.get('nonPolarBSA')) for r in rows]

    def calc_stats(data):
        if not data:
            return {'mean': 0, 'stdDev': 0, 'lower': 0, 'upper': 0}
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std = math.sqrt(variance)
        return {'mean': mean, 'stdDev': std, 'lower': max(0, mean - std), 'upper': mean + std}

    x_title = f'Time ({time_unit})' if time_unit else 'Frame'

    series = [
        {
            'id': 'total-bsa',
            'name': 'Total BSA',
            'data': total_bsa,
            'color': '#3B6EF5',
            'dashStyle': 'Solid',
            'zIndex': 2,
            'marker': {'symbol': 'circle'},
        },
        {
            'id': 'polar-bsa',
            'name': 'Total POLAR Buried Area',
            'data': polar_bsa,
            'color': '#FF3B30',
            'dashStyle': 'Dash',
            'zIndex': 2,
            'marker': {'symbol': 'square'},
        },
        {
            'id': 'nonpolar-bsa',
            'name': 'Total NON POLAR Buried Area',
            'data': nonpolar_bsa,
            'color': '#34C759',
            'dashStyle': 'Dot',
            'zIndex': 2,
            'marker': {'symbol': 'triangle'},
        },
    ]

    if show_stats:
        for base_id, data, color in [
            ('total-bsa', total_bsa, '#3B6EF5'),
            ('polar-bsa', polar_bsa, '#FF3B30'),
            ('nonpolar-bsa', nonpolar_bsa, '#34C759'),
        ]:
            stats = calc_stats(data)
            if stats['stdDev'] > 0:
                range_data = [[i, stats['lower'], stats['upper']] for i in range(len(data))]
                series.append({
                    'type': 'arearange',
                    'linkedTo': base_id,
                    'data': range_data,
                    'color': color,
                    'fillOpacity': 0.12,
                    'lineWidth': 0,
                    'enableMouseTracking': False,
                    'showInLegend': False,
                    'zIndex': 0,
                    'marker': {'enabled': False},
                })

    chart_options = {
        **_common_chart_style(),
        'chart': {
            'type': 'line',
            'backgroundColor': '#ffffff',
            'height': 650,
            'width': 1600,
        },
        'title': {
            'text': f'{system_name} - Total Buried Surface Area Across Frames',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'xAxis': {
            'categories': categories,
            'title': {
                'text': x_title,
                'style': {'fontSize': '15px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '12px', 'fontWeight': '500', 'color': '#1d1d1f'}},
        },
        'yAxis': {
            'title': {
                'text': 'Total Buried Surface Area (Å²)',
                'style': {'fontSize': '15px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '12px', 'fontWeight': '500', 'color': '#1d1d1f'}},
        },
        'legend': {
            'align': 'center',
            'verticalAlign': 'top',
            'layout': 'horizontal',
            'itemStyle': {'fontSize': '14px', 'fontWeight': '500', 'color': '#1d1d1f'},
        },
        'plotOptions': {
            'line': {
                'lineWidth': 2,
                'marker': {'enabled': True, 'radius': 3, 'lineWidth': 1, 'lineColor': '#ffffff'},
                'states': {'hover': {'lineWidth': 3}},
            }
        },
        'series': series,
    }

    return _export_highcharts_png(chart_options, output_path)


def generate_interaction_heatmap(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    conservation_threshold: float = 0.5,
    excluded_types: set | None = None,
    show_labels: bool = True,
) -> bool:
    """Generate Interaction Heatmap PNG."""
    if excluded_types is None:
        excluded_types = {'proximal'}

    # Aggregate raw per-frame data into per-pair entries with consistency
    aggregated = _aggregate_interactions(system_dir)
    if not aggregated:
        console.print("  [yellow]Warning: _interactions.csv not found or empty, skipping heatmap[/yellow]")
        return False

    # Filter by threshold and excluded types
    interactions = []
    for entry in aggregated:
        if entry['consistency'] < conservation_threshold:
            continue
        # Check if any non-excluded type exists
        has_included_type = False
        for t in entry['types']:
            if _matches_selected_types(t, excluded_types):
                has_included_type = True
                break
        if has_included_type:
            interactions.append(entry)

    if not interactions:
        console.print("  [yellow]Warning: No interactions pass filters for heatmap[/yellow]")
        return False

    # Build residue ID sets
    def fmt_res(entry, suffix):
        return f"{entry[f'resName{suffix}']}{entry[f'resNum{suffix}']}_{entry[f'chain{suffix}']}"

    res1_set = sorted(set(fmt_res(e, '1') for e in interactions))
    res2_set = sorted(set(fmt_res(e, '2') for e in interactions))

    # Build heatmap data
    heatmap_data = []
    for entry in interactions:
        r1 = fmt_res(entry, '1')
        r2 = fmt_res(entry, '2')
        c = entry['consistency']
        x = res1_set.index(r1)
        y = res2_set.index(r2)
        # Use the color of the most persistent type
        types_list = list(entry['types'])
        main_type = types_list[0] if types_list else ''
        color_rgb = find_interaction_color(main_type)
        heatmap_data.append({
            'x': x,
            'y': y,
            'value': round(c * 100, 1),
            'color': f'rgba({color_rgb[0]},{color_rgb[1]},{color_rgb[2]},{0.3 + c * 0.6})',
        })

    chart_height = max(600, len(res2_set) * 25 + 200)

    chart_options = {
        'chart': {
            'type': 'heatmap',
            'backgroundColor': '#ffffff',
            'height': chart_height,
            'width': max(1200, len(res1_set) * 25 + 400),
        },
        'title': {
            'text': f'{system_name} - Interaction Heatmap',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'credits': {'enabled': False},
        'xAxis': {
            'categories': res1_set if show_labels else [],
            'title': {'text': 'Residue (Chain A side)'},
            'labels': {
                'rotation': -45 if len(res1_set) > 20 else 0,
                'style': {'fontSize': '10px' if len(res1_set) > 40 else '12px'},
            },
        },
        'yAxis': {
            'categories': res2_set if show_labels else [],
            'title': {'text': 'Residue (Chain B side)'},
            'labels': {
                'style': {'fontSize': '10px' if len(res2_set) > 40 else '12px'},
            },
            'reversed': True,
        },
        'colorAxis': {
            'min': 0,
            'max': 100,
            'stops': [
                [0, '#ffffff'],
                [0.5, '#4b0082'],
                [1, '#4b0082'],
            ],
        },
        'series': [{
            'name': 'Conservation %',
            'borderWidth': 1,
            'borderColor': '#ffffff',
            'data': heatmap_data,
            'dataLabels': {
                'enabled': len(heatmap_data) < 200,
                'style': {'fontSize': '9px', 'color': '#ffffff', 'textOutline': 'none'},
            },
        }],
    }

    return _export_highcharts_png(chart_options, output_path, width=chart_options['chart']['width'])


def generate_conservation_matrix(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    time_unit: str | None = None,
    excluded_types: set | None = None,
    pair_threshold: float = 0.5,
    type_threshold: float = 0.5,
    atom_change_mode: str = 'previous',
) -> bool:
    """Generate Conservation Matrix chart PNG."""
    if excluded_types is None:
        excluded_types = {'proximal'}

    # Aggregate raw per-frame data
    aggregated = _aggregate_interactions(system_dir)
    if not aggregated:
        console.print("  [yellow]Warning: _interactions.csv not found or empty, skipping conservation matrix[/yellow]")
        return False

    # Filter by pair threshold and excluded types, using typePersistence for per-type thresholds
    filtered_pairs = []
    for entry in aggregated:
        if entry['consistency'] < pair_threshold:
            continue
        # Filter types by type_threshold and excluded
        included_types = {}
        for t, persistence in entry['typePersistence'].items():
            if persistence >= type_threshold and _matches_selected_types(t, excluded_types):
                included_types[t] = persistence
        if included_types:
            entry['filtered_types'] = included_types
            filtered_pairs.append(entry)

    if not filtered_pairs:
        console.print("  [yellow]Warning: No interactions pass filters for conservation matrix[/yellow]")
        return False

    # Build heatmap: x = residue pair, y = interaction type
    def fmt_res(e, s):
        return f"{e[f'resName{s}']}{e[f'resNum{s}']}_{e[f'chain{s}']}"

    pair_labels = [f"{fmt_res(p, '1')} ↔ {fmt_res(p, '2')}" for p in filtered_pairs]
    all_types = sorted(set(t for p in filtered_pairs for t in p['filtered_types']))

    heatmap_data = []
    for xi, pair in enumerate(filtered_pairs):
        for yi, itype in enumerate(all_types):
            c = pair['filtered_types'].get(itype, 0)
            if c > 0:
                color_rgb = find_interaction_color(itype)
                opacity = 0.3 + c * 0.6
                heatmap_data.append({
                    'x': xi,
                    'y': yi,
                    'value': round(c * 100, 1),
                    'color': f'rgba({color_rgb[0]},{color_rgb[1]},{color_rgb[2]},{opacity})',
                })

    chart_height = max(600, len(all_types) * 40 + 300)
    chart_width = max(1200, len(filtered_pairs) * 60 + 400)

    chart_options = {
        'chart': {
            'type': 'heatmap',
            'backgroundColor': '#ffffff',
            'height': chart_height,
            'width': chart_width,
        },
        'title': {
            'text': f'{system_name} - Interaction Conservation Matrix',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'subtitle': {
            'text': f'Pair threshold: {int(pair_threshold*100)}% | Type threshold: {int(type_threshold*100)}% | Mode: {atom_change_mode}',
            'style': {'fontSize': '14px', 'color': '#6e6e73'},
        },
        'credits': {'enabled': False},
        'xAxis': {
            'categories': pair_labels,
            'title': {'text': 'Residue Pairs'},
            'labels': {
                'rotation': -45,
                'style': {'fontSize': '10px' if len(pair_labels) > 30 else '12px'},
            },
        },
        'yAxis': {
            'categories': all_types,
            'title': {'text': 'Interaction Type'},
            'labels': {
                'style': {'fontSize': '12px'},
            },
        },
        'colorAxis': {
            'min': 0,
            'max': 100,
            'stops': [
                [0, '#f5f5f7'],
                [0.5, '#4b0082'],
                [1, '#1d1d1f'],
            ],
        },
        'series': [{
            'name': 'Conservation %',
            'borderWidth': 1,
            'borderColor': '#ffffff',
            'data': heatmap_data,
            'dataLabels': {
                'enabled': len(heatmap_data) < 300,
                'format': '{point.value}%',
                'style': {'fontSize': '9px', 'color': '#ffffff', 'textOutline': 'none'},
            },
        }],
    }

    return _export_highcharts_png(chart_options, output_path, width=chart_width)


def generate_violin_plots(
    system_dir: str,
    output_dir: str,
    system_name: str = 'System',
    interaction_types: list[str] | None = None,
    min_conservation: int = 50,
    conservation_threshold: float = 0.5,
    excluded_types: set | None = None,
) -> list[str]:
    """
    Generate violin plot PNGs using Plotly + Kaleido.

    One PNG per interaction type.
    Returns list of generated file paths.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        console.print("[red]plotly not installed. Run: pip install plotly kaleido[/red]")
        return []

    atom_pairs_file = Path(system_dir) / '_atom_pairs.csv'
    metadata_file = Path(system_dir) / '_metadata.json'
    interactions_file = Path(system_dir) / '_interactions.csv'

    if not atom_pairs_file.exists():
        console.print("  [yellow]Warning: _atom_pairs.csv not found, skipping violin plots[/yellow]")
        return []

    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 1)

    if excluded_types is None:
        excluded_types = {'proximal'}

    # Read atom pairs CSV to discover available interaction types
    ap_rows = _read_csv(str(atom_pairs_file))

    # The column is 'interactionType' (not 'type')
    available_types_set = set()
    for row in ap_rows:
        itype = row.get('interactionType', '').strip()
        if itype and _matches_selected_types(itype, excluded_types):
            available_types_set.add(itype)
    available_types = sorted(available_types_set)

    if interaction_types:
        types_to_plot = [t for t in interaction_types if t in available_types]
    else:
        types_to_plot = available_types

    if not types_to_plot:
        console.print("  [yellow]Warning: No interaction types available for violin plots[/yellow]")
        return []

    # Read atom pairs
    ap_rows = _read_csv(str(atom_pairs_file))

    os.makedirs(output_dir, exist_ok=True)
    generated = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating violin plots", total=len(types_to_plot))

        for itype in types_to_plot:
            progress.update(task, description=f"Violin: {itype}")

            # Filter atom pairs for this interaction type
            # The column name is 'interactionType' (not 'type')
            filtered = [r for r in ap_rows if r.get('interactionType', '').strip() == itype]

            if not filtered:
                progress.update(task, advance=1)
                continue

            # Group by residue pair
            pair_distances = {}
            for r in filtered:
                pair_key = f"{r.get('resName1','')}{r.get('resNum1','')}{r.get('chain1','')} ↔ {r.get('resName2','')}{r.get('resNum2','')}{r.get('chain2','')}"
                dist = float(r.get('distance', 0))
                if pair_key not in pair_distances:
                    pair_distances[pair_key] = []
                pair_distances[pair_key].append(dist)

            # Limit to top 50 pairs
            sorted_pairs = sorted(pair_distances.items(), key=lambda x: -len(x[1]))[:50]

            if not sorted_pairs:
                progress.update(task, advance=1)
                continue

            color = get_interaction_color_hex(itype)

            # Build Plotly traces
            traces = []
            pair_labels = []
            for pair_label, distances in sorted_pairs:
                pair_labels.append(pair_label)
                traces.append(go.Violin(
                    y=distances,
                    x=[pair_label] * len(distances),
                    name=pair_label,
                    box_visible=False,
                    meanline_visible=False,
                    fillcolor=color,
                    opacity=0.45,
                    points='all',
                    pointpos=0,
                    jitter=0.3,
                    marker=dict(size=6, color=color, opacity=1.0),
                    scalemode='width',
                    width=0.9,
                    showlegend=False,
                ))

            # Global mean
            all_dists = [d for _, dists in sorted_pairs for d in dists]
            global_mean = sum(all_dists) / len(all_dists) if all_dists else 0

            chart_height = max(600, len(sorted_pairs) * 50)

            layout = go.Layout(
                title=dict(
                    text=f'{system_name} - Distance Distribution: {itype}',
                    font=dict(size=20, color='#1d1d1f'),
                ),
                shapes=[{
                    'type': 'line',
                    'x0': 0, 'x1': 1,
                    'xref': 'paper',
                    'y0': global_mean, 'y1': global_mean,
                    'yref': 'y',
                    'line': {'color': '#1d1d1f', 'width': 2.5, 'dash': 'dash'},
                    'layer': 'above',
                }],
                xaxis=dict(
                    title='Residue Pairs',
                    tickangle=-45,
                    tickfont=dict(size=11, color='#1d1d1f'),
                ),
                yaxis=dict(
                    title='Distance (\u00c5)',
                    tickfont=dict(size=12, color='#1d1d1f'),
                    gridcolor='#e5e5e7',
                    zeroline=False,
                ),
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                margin=dict(l=80, r=40, t=120, b=150),
                height=chart_height,
                hovermode='closest',
                violinmode='group',
            )

            fig = go.Figure(data=traces, layout=layout)

            safe_name = itype.replace('/', '_').replace(' ', '_').replace('\u03c0', 'pi')
            out_file = os.path.join(output_dir, f'dist_{safe_name}.png')
            try:
                fig.write_image(out_file, width=1400, height=chart_height, scale=2, engine='kaleido')
                generated.append(out_file)
            except Exception as e:
                console.print(f"  [red]Failed to export {itype}: {e}[/red]")

            progress.update(task, advance=1)

    return generated


def display_conserved_islands(system_dir: str, system_name: str = 'System'):
    """Print conserved islands as a formatted table to the terminal."""
    islands_file = Path(system_dir) / '_conserved_islands.json'
    if not islands_file.exists():
        console.print("  [yellow]Warning: _conserved_islands.json not found[/yellow]")
        return

    data = _read_json(str(islands_file))
    islands = data if isinstance(data, list) else data.get('islands', [])

    if not islands:
        console.print("  [dim]No conserved islands found.[/dim]")
        return

    console.print()
    console.print(Panel(
        f"[bold]{len(islands)} Conserved Island(s)[/bold] (70% threshold)",
        title=f"🏝  {system_name} — Conserved Islands",
        border_style="cyan",
    ))

    for island in islands:
        table = Table(
            title=f"Island {island.get('id', '?')} — {island.get('size', '?')} residues | Chains: {', '.join(island.get('chains', []))}",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold",
        )
        table.add_column("Chain", style="cyan")
        table.add_column("Res #", style="green")
        table.add_column("Res Name")

        for res in island.get('residues', []):
            table.add_row(
                str(res.get('chain', '')),
                str(res.get('resNum', '')),
                str(res.get('resName', '—')),
            )

        console.print(table)
        console.print()


# ─────────────────────────────────────────────────────────────────────────────
# Master chart generation function
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_charts(
    system_dir: str,
    system_name: str,
    global_controls: dict,
    matrix_opts: dict | None,
    heatmap_opts: dict | None,
    trends_opts: dict | None,
    distribution_opts: dict | None,
    area_opts: dict | None,
    show_islands: bool = True,
) -> list[str]:
    """
    Generate all requested charts.

    Returns list of generated file paths.
    """
    charts_dir = os.path.join(system_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    generated = []

    threshold = global_controls.get('conservation_threshold', 0.5)
    time_unit = global_controls.get('time_unit')
    excluded = global_controls.get('excluded_types', {'proximal'})

    console.print()
    console.print(Panel(
        "[bold]Generating charts …[/bold]",
        title="Chart Export",
        border_style="green",
    ))

    # 1. Conservation Matrix
    if matrix_opts is not None:
        console.print("\n  [bold]Conservation Matrix[/bold] …")
        out = os.path.join(charts_dir, 'conservation_matrix.png')
        ok = generate_conservation_matrix(
            system_dir, out, system_name,
            time_unit=time_unit,
            excluded_types=excluded,
            pair_threshold=matrix_opts.get('pair_threshold', 0.5),
            type_threshold=matrix_opts.get('type_threshold', 0.5),
            atom_change_mode=matrix_opts.get('atom_change_mode', 'previous'),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")

    # 2. Interaction Heatmap
    if heatmap_opts is not None:
        console.print("\n  [bold]Interaction Heatmap[/bold] …")
        out = os.path.join(charts_dir, 'interaction_heatmap.png')
        ok = generate_interaction_heatmap(
            system_dir, out, system_name,
            conservation_threshold=threshold,
            excluded_types=excluded,
            show_labels=heatmap_opts.get('show_labels', True),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")

    # 3. Interaction Trends
    if trends_opts is not None:
        console.print("\n  [bold]Interaction Trends[/bold] …")
        out = os.path.join(charts_dir, 'interaction_trends.png')
        ok = generate_interaction_trends(
            system_dir, out, system_name,
            time_unit=time_unit,
            log_scale=trends_opts.get('log_scale', False),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")

    # 4. Area Composition
    if area_opts is not None:
        console.print("\n  [bold]Area Composition[/bold] …")
        out = os.path.join(charts_dir, 'area_composition.png')
        ok = generate_area_chart(
            system_dir, out, system_name,
            time_unit=time_unit,
            show_stats=area_opts.get('show_stats', True),
            show_percentages=area_opts.get('show_percentages', False),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")

    # 5. Distance Distribution (violin plots)
    if distribution_opts is not None:
        console.print("\n  [bold]Distance Distribution[/bold] ...")
        files = generate_violin_plots(
            system_dir,
            os.path.join(charts_dir, 'distance_distribution'),
            system_name,
            interaction_types=distribution_opts.get('types'),
            min_conservation=distribution_opts.get('min_conservation', 50),
            conservation_threshold=threshold,
            excluded_types=excluded,
        )
        generated.extend(files)
        if files:
            console.print(f"  [green]\u2713[/green] {len(files)} Distance Distribution chart(s) generated")

    # 6. Conserved Islands
    if show_islands:
        display_conserved_islands(system_dir, system_name)

    # Summary
    console.print()
    if generated:
        console.print(Panel(
            f"[bold green]{len(generated)} chart(s) saved to:[/bold green] {charts_dir}",
            title="Charts Complete",
            border_style="green",
        ))
    else:
        console.print("[yellow]No charts were generated.[/yellow]")

    return generated
