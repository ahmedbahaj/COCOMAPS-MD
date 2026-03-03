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


def _export_highcharts_png(
    chart_options: dict,
    output_path: str,
    width: int = 1600,
    scale: int = 2,
    callback_js: str | None = None,
):
    """
    Export a Highcharts chart to PNG using highcharts-export-server.

    Writes the options JSON to a temp file, invokes the CLI, and saves the PNG.
    If callback_js is provided, it is written to a .js temp file and passed via
    --callback + --allowCodeExecution so JS formatter functions work.
    """
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    ) as tmp:
        json.dump(chart_options, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    cb_path = None
    if callback_js:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.js', delete=False, encoding='utf-8'
        ) as cb_tmp:
            cb_tmp.write(callback_js)
            cb_path = cb_tmp.name

    try:
        cmd = [
            'highcharts-export-server',
            '--infile', tmp_path,
            '--outfile', output_path,
            '--type', 'png',
            '--width', str(width),
            '--scale', str(scale),
        ]
        if cb_path:
            cmd += ['--callback', cb_path, '--allowCodeExecution', '1']

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
        if cb_path:
            os.unlink(cb_path)


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

    total_stats = calc_stats(total_bsa)
    polar_stats = calc_stats(polar_bsa)
    nonpolar_stats = calc_stats(nonpolar_bsa)

    def build_legend_name(base_name, color, stats):
        if not show_stats:
            return base_name
        return (
            f'{base_name} <span style="color:{color};font-weight:600">'
            f'(Mean = {stats["mean"]:.2f}, ±Std = {stats["stdDev"]:.2f})</span>'
        )

    series = [
        {
            'id': 'total-bsa',
            'name': build_legend_name('Total BSA', '#3B6EF5', total_stats),
            'data': total_bsa,
            'color': '#3B6EF5',
            'dashStyle': 'Solid',
            'zIndex': 2,
            'marker': {'symbol': 'circle'},
        },
        {
            'id': 'polar-bsa',
            'name': build_legend_name('Total POLAR Buried Area', '#FF3B30', polar_stats),
            'data': polar_bsa,
            'color': '#FF3B30',
            'dashStyle': 'Dash',
            'zIndex': 2,
            'marker': {'symbol': 'square'},
        },
        {
            'id': 'nonpolar-bsa',
            'name': build_legend_name('Total NON POLAR Buried Area', '#34C759', nonpolar_stats),
            'data': nonpolar_bsa,
            'color': '#34C759',
            'dashStyle': 'Dot',
            'zIndex': 2,
            'marker': {'symbol': 'triangle'},
        },
    ]

    if show_stats:
        for base_id, stats, data, color in [
            ('total-bsa', total_stats, total_bsa, '#3B6EF5'),
            ('polar-bsa', polar_stats, polar_bsa, '#FF3B30'),
            ('nonpolar-bsa', nonpolar_stats, nonpolar_bsa, '#34C759'),
        ]:
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
            'useHTML': True,
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

    # Build residue ID sets — sort numerically by residue number
    def sort_key(res_id):
        import re
        match = re.search(r'\d+', res_id)
        return int(match.group()) if match else 0

    res1_set = sorted(set(fmt_res(e, '1') for e in interactions), key=sort_key)
    res2_set = sorted(set(fmt_res(e, '2') for e in interactions), key=sort_key)

    # Build heatmap data — value is 0-100 (percentage) for display
    heatmap_data = []
    for entry in interactions:
        r1 = fmt_res(entry, '1')
        r2 = fmt_res(entry, '2')
        c = entry['consistency']
        x = res1_set.index(r1)
        y = res2_set.index(r2)
        heatmap_data.append({
            'x': x,
            'y': y,
            'value': round(c * 100, 2),
        })

    # ── Dynamic label sizing (mirrors FilteredHeatmap.vue) ──
    x_count = len(res1_set)
    y_count = len(res2_set)

    if x_count <= 10:
        x_font, x_rot = '14px', 0
    elif x_count <= 25:
        x_font, x_rot = '12px', -30
    elif x_count <= 50:
        x_font, x_rot = '10px', -45
    elif x_count <= 80:
        x_font, x_rot = '9px', -60
    else:
        x_font, x_rot = '8px', -90

    if y_count <= 15:
        y_font = '14px'
    elif y_count <= 35:
        y_font = '12px'
    elif y_count <= 60:
        y_font = '10px'
    elif y_count <= 100:
        y_font = '9px'
    else:
        y_font = '8px'

    y_font_val = int(y_font.replace('px', ''))
    row_height = max(12, y_font_val + 4)
    chart_height = max(500, y_count * row_height + 250)

    chart_options = {
        'chart': {
            'type': 'heatmap',
            'backgroundColor': '#ffffff',
            'height': chart_height,
            'width': max(1200, x_count * 25 + 400),
        },
        'title': {
            'text': f'{system_name} - Residue Interaction Heatmap ({len(heatmap_data)} interactions)',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'subtitle': {'text': None},
        'credits': {'enabled': False},
        'xAxis': {
            'categories': res1_set if show_labels else [],
            'title': {
                'text': f'Chain 1 Residues',
                'style': {'fontSize': '18px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {
                'rotation': x_rot,
                'step': 1,
                'overflow': 'allow',
                'style': {
                    'fontSize': x_font,
                    'fontWeight': '700',
                    'color': '#1d1d1f',
                },
            },
            'gridLineWidth': 1,
            'gridLineColor': '#e5e7eb',
            'tickWidth': 1,
            'tickColor': '#d1d5db',
        },
        'yAxis': {
            'categories': res2_set if show_labels else [],
            'title': {
                'text': f'Chain 2 Residues',
                'style': {'fontSize': '18px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {
                'step': 1,
                'overflow': 'allow',
                'style': {
                    'fontSize': y_font,
                    'fontWeight': '700',
                    'color': '#1d1d1f',
                },
            },
            'reversed': True,
        },
        'colorAxis': {
            'min': 0,
            'max': 100,
            'reversed': False,
            'tickPositions': [0, 25, 50, 75, 100],
            'stops': [
                [0, '#f5f5f7'],
                [0.3, '#90CAF9'],
                [0.5, '#42A5F5'],
                [0.7, '#1E88E5'],
                [1, '#0D47A1'],
            ],
            'labels': {
                'format': '{value}%',
                'style': {
                    'fontSize': '12px',
                    'fontWeight': '500',
                    'color': '#1d1d1f',
                },
            },
        },
        'legend': {
            'align': 'right',
            'layout': 'vertical',
            'verticalAlign': 'middle',
            'symbolHeight': 300,
            'symbolWidth': 20,
            'reversed': False,
            'title': {
                'text': 'Conservation',
                'style': {
                    'fontSize': '14px',
                    'fontWeight': '600',
                    'color': '#1d1d1f',
                },
            },
        },
        'series': [{
            'name': 'Interaction Conservation',
            'data': heatmap_data,
            'turboThreshold': 10000,
            'borderWidth': 1,
            'borderColor': '#93c5fd',
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
    """
    Generate Conservation Matrix chart PNG.

    Mirrors InteractionConservationMatrix.vue: a timeline heatmap where
    X = frame number, Y = pair-type combination rows, and each interaction
    type has its own colored series.
    """
    interactions_file = Path(system_dir) / '_interactions.csv'
    metadata_file = Path(system_dir) / '_metadata.json'

    if not interactions_file.exists():
        console.print("  [yellow]Warning: _interactions.csv not found, skipping conservation matrix[/yellow]")
        return False

    if excluded_types is None:
        excluded_types = {'proximal'}

    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 1)

    # Aggregate to get per-pair consistency and type persistence
    aggregated = _aggregate_interactions(system_dir)
    if not aggregated:
        console.print("  [yellow]Warning: _interactions.csv empty, skipping conservation matrix[/yellow]")
        return False

    # Read raw per-frame rows to build the timeline
    raw_rows = _read_csv(str(interactions_file))

    # LEVEL 1: Filter pairs by pair conservation threshold
    stable_pairs = [e for e in aggregated if e['consistency'] >= pair_threshold]
    if not stable_pairs:
        console.print("  [yellow]Warning: No pairs pass pair threshold for conservation matrix[/yellow]")
        return False

    # Build pair-type combinations (Y-axis rows)
    def fmt_res(e, s):
        return f"{e[f'resName{s}']}{e[f'resNum{s}']}_{e[f'chain{s}']}"

    def fmt_pair(e):
        return f"{fmt_res(e, '1')} - {fmt_res(e, '2')}"

    # Sort pairs by residue number
    import re
    def pair_sort_key(e):
        num1 = int(re.search(r'\d+', e.get('resNum1', '0')).group()) if re.search(r'\d+', e.get('resNum1', '0')) else 0
        num2 = int(re.search(r'\d+', e.get('resNum2', '0')).group()) if re.search(r'\d+', e.get('resNum2', '0')) else 0
        return (num1, num2)

    stable_pairs.sort(key=pair_sort_key)

    pair_type_combos = []  # list of {'pair': str, 'type': str}
    pair_type_to_row = {}  # "pair__type" -> row index

    for entry in stable_pairs:
        pair_label = fmt_pair(entry)
        # LEVEL 2: filter types by type conservation threshold + excluded
        for t in sorted(entry.get('typePersistence', {}).keys()):
            persistence = entry['typePersistence'][t]
            if persistence < type_threshold:
                continue
            if not _matches_selected_types(t, excluded_types):
                continue
            row_key = f"{pair_label}__{t}"
            if row_key not in pair_type_to_row:
                pair_type_to_row[row_key] = len(pair_type_combos)
                pair_type_combos.append({'pair': pair_label, 'type': t})

    if not pair_type_combos:
        console.print("  [yellow]Warning: No pair-type combinations pass thresholds for conservation matrix[/yellow]")
        return False

    # Build a lookup: pair_key -> { type -> set of frame numbers }
    pair_type_frames = {}
    for row in raw_rows:
        r1 = f"{row.get('resName1','')}{row.get('resNum1','')}_{row.get('chain1','')}"
        r2 = f"{row.get('resName2','')}{row.get('resNum2','')}_{row.get('chain2','')}"
        pair_label = f"{r1} - {r2}"
        frame_num = int(row.get('frame', 0))
        for t in (row.get('types') or '').split(';'):
            t = t.strip()
            if not t:
                continue
            pt_key = f"{pair_label}__{t}"
            if pt_key in pair_type_to_row:
                if pt_key not in pair_type_frames:
                    pair_type_frames[pt_key] = set()
                pair_type_frames[pt_key].add(frame_num)

    # Build separate heatmap series per interaction type (like GUI)
    series_map = {}  # type -> list of data points
    for pt_key, frames in pair_type_frames.items():
        row_idx = pair_type_to_row.get(pt_key)
        if row_idx is None:
            continue
        itype = pair_type_combos[row_idx]['type']
        if itype not in series_map:
            series_map[itype] = []
        for frame_num in frames:
            series_map[itype].append({
                'x': frame_num,
                'y': row_idx,
                'value': 1,
            })

    # Build series list — each type gets its own colored series
    series = []
    types_with_data = set()
    for itype in sorted(series_map.keys()):
        color = get_interaction_color_hex(itype)
        bold_name = f'<span style="font-weight:700;font-size:12px;color:#1d1d1f">{itype}</span>'
        series.append({
            'type': 'heatmap',
            'name': bold_name,
            'data': series_map[itype],
            'color': color,
            'borderWidth': 1,
            'borderColor': '#e8e8ed',
            'nullColor': 'transparent',
            'colsize': 1,
            'rowsize': 1,
            'dataLabels': {'enabled': False},
            'showInLegend': True,
            '_hasData': True,
        })
        types_with_data.add(itype.lower())

    # ── Add ALL interaction types to legend (GUI parity) ─────────────
    # Types present in data → bold; absent types → grayed out

    def _type_already_in_series(it_entry):
        """Check if INTERACTION_TYPE already exists in series via keywords."""
        label_low = it_entry['label'].lower()
        if label_low in types_with_data:
            return True
        for kw in it_entry.get('keywords', []):
            kw_low = kw.lower()
            for name in types_with_data:
                if kw_low in name:
                    return True
        return False

    for it in INTERACTION_TYPES:
        # Skip excluded types
        if it['id'] in excluded_types:
            continue
        if _type_already_in_series(it):
            continue
        color = get_interaction_color_hex(it['label'])
        gray_name = f'<span style="color:#9ca3af;font-weight:400;font-size:12px">{it["label"]}</span>'
        series.append({
            'type': 'heatmap',
            'name': gray_name,
            'data': [],
            'color': color,
            'borderWidth': 1,
            'borderColor': '#e8e8ed',
            'nullColor': 'transparent',
            'colsize': 1,
            'rowsize': 1,
            'dataLabels': {'enabled': False},
            'showInLegend': True,
            '_hasData': False,
        })

    # ── Atom change detection (mirrors GUI hasAtomChange / scatter) ───
    atom_pairs_file = Path(system_dir) / '_atom_pairs.csv'
    if atom_pairs_file.exists():
        ap_rows = _read_csv(str(atom_pairs_file))

        # Build lookup: pair_label -> type -> frame_num -> [atomPair strings]
        ap_lookup = {}  # { "pair_label" : { type : { frame : [atom_pair, ...] } } }
        for r in ap_rows:
            r1 = f"{r.get('resName1','')}{r.get('resNum1','')}_{r.get('chain1','')}"
            r2 = f"{r.get('resName2','')}{r.get('resNum2','')}_{r.get('chain2','')}"
            pair_label = f"{r1} - {r2}"
            itype = r.get('interactionType', '').strip()
            if not itype:
                continue
            frame_num = int(r.get('frame', 0))
            atom1 = r.get('atom1', '')
            atom2 = r.get('atom2', '')
            atom_pair = f"{atom1}-{atom2}"

            ap_lookup.setdefault(pair_label, {}).setdefault(itype, {}).setdefault(frame_num, [])
            if atom_pair not in ap_lookup[pair_label][itype][frame_num]:
                ap_lookup[pair_label][itype][frame_num].append(atom_pair)

        # Sort atom pair lists for consistent comparison
        for pl in ap_lookup.values():
            for tp in pl.values():
                for fr in tp:
                    tp[fr] = sorted(tp[fr])

        def _has_overlap(set1, set2):
            s = set(set1)
            return any(p in s for p in set2)

        def _get_dominant(type_frames_map):
            """Most frequent atom-pair combination across all frames."""
            from collections import Counter
            combo_counts = Counter()
            for frame_num, pairs in type_frames_map.items():
                key = '|'.join(sorted(pairs))
                combo_counts[key] += 1
            if not combo_counts:
                return []
            top_key = combo_counts.most_common(1)[0][0]
            return top_key.split('|') if top_key else []

        def _get_first_frame_pairs(type_frames_map):
            """Atom pairs from the first frame where interaction appears."""
            if not type_frames_map:
                return []
            first_frame = min(type_frames_map.keys())
            return type_frames_map[first_frame]

        atom_change_data = []
        for pt in pair_type_combos:
            pair_label = pt['pair']
            itype = pt['type']
            row_idx = pair_type_to_row.get(f"{pair_label}__{itype}")
            if row_idx is None:
                continue

            type_frames_map = ap_lookup.get(pair_label, {}).get(itype, {})
            if not type_frames_map:
                continue

            # Get frames where this pair-type exists (from pair_type_frames lookup)
            pt_key = f"{pair_label}__{itype}"
            active_frames = sorted(pair_type_frames.get(pt_key, set()))

            for frame_num in active_frames:
                current_pairs = type_frames_map.get(frame_num, [])
                if not current_pairs:
                    continue

                ref_pairs = []
                if atom_change_mode == 'previous':
                    if frame_num <= 1:
                        continue
                    ref_pairs = type_frames_map.get(frame_num - 1, [])
                    if not ref_pairs:
                        continue  # New appearance, not a change
                elif atom_change_mode == 'dominant':
                    ref_pairs = _get_dominant(type_frames_map)
                    if not ref_pairs:
                        continue
                elif atom_change_mode == 'first':
                    ref_pairs = _get_first_frame_pairs(type_frames_map)
                    if not ref_pairs:
                        continue
                    if sorted(current_pairs) == sorted(ref_pairs):
                        continue  # Same as first frame
                else:
                    continue

                # TRUE CHANGE: no overlap between reference and current
                if not _has_overlap(ref_pairs, current_pairs):
                    atom_change_data.append({
                        'x': frame_num,
                        'y': row_idx,
                    })

        if atom_change_data:
            series.append({
                'type': 'scatter',
                'name': 'Atom Changes',
                'color': '#FF9500',
                'data': atom_change_data,
                'marker': {
                    'symbol': 'circle',
                    'radius': 4,
                    'fillColor': '#FF9500',
                    'lineColor': '#FFFFFF',
                    'lineWidth': 1,
                },
                'showInLegend': True,
                'enableMouseTracking': True,
                'zIndex': 10,
            })

    # Y-axis labels: pair labels (one per row)
    y_labels = [pt['pair'] for pt in pair_type_combos]

    unique_pairs = len(set(pt['pair'] for pt in pair_type_combos))
    x_title = f'Time ({time_unit})' if time_unit else 'Frame Number'
    tick_interval = max(1, total_frames // 20)

    chart_height = max(600, len(pair_type_combos) * 25 + 200)
    chart_width = max(1200, total_frames * 12 + 450)

    chart_options = {
        'chart': {
            'type': 'heatmap',
            'backgroundColor': '#ffffff',
            'height': chart_height,
            'width': chart_width,
            'zoomType': 'xy',
            'marginLeft': 250,
            'marginRight': 200,
        },
        'title': {
            'text': f'{system_name} - Interaction Conservation Timeline ({len(pair_type_combos)} pair-type combinations, {unique_pairs} unique pairs)',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'subtitle': {'text': None},
        'credits': {'enabled': False},
        'colors': None,
        'colorAxis': None,
        'xAxis': {
            'title': {
                'text': x_title,
                'style': {'fontSize': '15px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'min': 0.5,
            'max': total_frames + 0.5,
            'tickInterval': tick_interval,
            'labels': {
                'style': {'fontSize': '12px', 'fontWeight': '500', 'color': '#6e6e73'},
            },
            'gridLineWidth': 0,
            'lineWidth': 1,
            'lineColor': '#d2d2d7',
            'tickWidth': 1,
            'tickColor': '#d2d2d7',
            'plotLines': [{'value': i + 0.5, 'color': '#e8e8ed', 'width': 1, 'zIndex': 1} for i in range(total_frames + 1)],
        },
        'yAxis': {
            'title': {'text': ''},
            'min': -0.5,
            'max': len(pair_type_combos) - 0.5,
            'tickPositions': list(range(len(pair_type_combos))),
            'categories': y_labels,
            'labels': {
                'align': 'right',
                'x': -10,
                'style': {
                    'fontSize': '12px',
                    'fontWeight': '600',
                    'color': '#1d1d1f',
                    'textAlign': 'right',
                    'width': '220px',
                    'whiteSpace': 'nowrap',
                    'overflow': 'visible',
                },
            },
            'gridLineWidth': 0,
            'lineWidth': 1,
            'lineColor': '#d2d2d7',
            'tickWidth': 1,
            'tickColor': '#d2d2d7',
            'reversed': False,
            'startOnTick': False,
            'endOnTick': False,
            'plotLines': [{'value': i - 0.5, 'color': '#e8e8ed', 'width': 1, 'zIndex': 1} for i in range(len(pair_type_combos) + 1)],
        },
        'plotOptions': {
            'heatmap': {
                'borderWidth': 1,
                'borderColor': '#e8e8ed',
            },
        },
        'legend': {
            'enabled': True,
            'align': 'right',
            'verticalAlign': 'top',
            'layout': 'vertical',
            'y': 60,
            'useHTML': True,
            'itemStyle': {
                'fontSize': '12px',
                'fontWeight': '500',
                'color': '#1d1d1f',
            },
            'maxHeight': 400,
            'navigation': {
                'activeColor': '#3B6EF5',
                'inactiveColor': '#6e6e73',
            },
        },
        'series': series,
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
                raw_dist = r.get('distance', '').strip()
                if not raw_dist:
                    continue
                try:
                    dist = float(raw_dist)
                except ValueError:
                    continue
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
