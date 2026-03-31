"""
CLI entry point for COCOMAPS-MD.

Usage:
    coco-md [pdb_file] [OPTIONS]
    python -m cli [pdb_file] [OPTIONS]
"""
import argparse
import copy
import csv
import os
import sys
import warnings
from pathlib import Path

# Suppress noisy MDAnalysis/NumPy warnings — keep terminal clean
warnings.filterwarnings('ignore', module='MDAnalysis')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='numpy')

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# ── Ensure the project root is on sys.path ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _print_welcome():
    """Show the welcome banner."""
    console.print()
    console.print(Panel(
        "[bold]COCOMAPS-MD CLI[/bold]\n"
        "[dim]Local version of the web GUI pipeline[/dim]\n\n"
        "Analyze PDB trajectories, compute residue-level interactions\n"
        "via CoCoMaps, and generate publication-ready charts.",
        border_style="blue",
        padding=(1, 4),
    ))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='coco-md',
        description='COCOMAPS-MD CLI — local tool matching the web GUI pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  coco-md my_protein.pdb                        # run with defaults
  coco-md my_protein.pdb -o results/run1         # specify output dir
  coco-md my_protein.pdb -C                      # interactive customization
  coco-md my_protein.pdb -c A B -o out/ -s 1 -e 100 -n 2 -i 7.0 -t 70
        """,
    )

    parser.add_argument('pdb_file', nargs='?', default=None,
                        help='Path to input PDB file (prompted if omitted)')

    # ── Pipeline flags ──
    parser.add_argument('-c', '--chains', nargs=2, metavar=('A', 'B'),
                        help='Chain IDs to analyze (default: auto-detect)')
    parser.add_argument('-o', '--output',
                        help='Output directory (default: systems/<pdb_name>)')
    parser.add_argument('-r', '--reduce', action='store_true', default=False,
                        help='Use reduce version of CoCoMaps')
    parser.add_argument('-i', '--cutoff', type=float, default=5.0,
                        help='Interface selection cutoff in Å (default: 5.0)')
    parser.add_argument('-w', '--water', type=float, default=None,
                        help='Bridging water cutoff in Å (default: same as --cutoff)')
    parser.add_argument('-p', '--params', default=None,
                        help='Path to JSON file with CoCoMaps parameter overrides')

    # ── Trajectory scope flags ──
    parser.add_argument('-s', '--start', type=int, default=None,
                        help='Start frame, 1-indexed (default: 1)')
    parser.add_argument('-e', '--end', type=int, default=None,
                        help='End frame, 1-indexed inclusive (default: last frame)')
    parser.add_argument('-n', '--step', type=int, default=1,
                        help='Frame step — analyze every Nth frame (default: 1)')

    # ── Chart flags ──
    parser.add_argument('-t', '--threshold', type=int, default=None,
                        help='Conservation threshold %% for charts, 0-100 (default: 50)')
    parser.add_argument('-u', '--unit', default=None,
                        help='Time axis label, e.g. fs, ps, ns (default: Frame)')

    # ── Mode ──
    parser.add_argument('-C', '--customize', action='store_true', default=False,
                        help='Enter interactive customization after showing defaults')

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── Welcome banner ──
    _print_welcome()

    # ── Prompt for PDB file if not provided ──
    if args.pdb_file is None:
        console.print("  [dim]No PDB file provided. Enter the path below.[/dim]")
        pdb_path = Prompt.ask("  PDB file path")
        args.pdb_file = pdb_path.strip()

    # ── Validate input ──
    if not args.pdb_file or not os.path.exists(args.pdb_file):
        console.print(f"[red]Error: PDB file not found: {args.pdb_file}[/red]")
        sys.exit(1)

    # ── Inspect PDB ──
    console.print("\n[bold]Inspecting PDB file …[/bold]")
    from cli.inspect_pdb import inspect_pdb

    info = inspect_pdb(args.pdb_file)
    console.print(f"  File:     [cyan]{args.pdb_file}[/cyan]")
    console.print(f"  Frames:   [bold]{info['total_frames']}[/bold]")
    console.print(f"  Chains:   [bold]{', '.join(info['chains']) or 'none detected'}[/bold]")
    console.print(f"  Atoms:    {info['n_atoms']}")
    console.print(f"  Residues: {info['n_residues']}")

    # ── Resolve chain selection ──
    chains = info['chains']
    if args.chains:
        chain_a, chain_b = args.chains
    else:
        chain_a = chains[0] if len(chains) >= 1 else 'A'
        chain_b = chains[1] if len(chains) >= 2 else 'B'

    # ── Resolve trajectory scope ──
    total_frames = info['total_frames']
    start_frame = (args.start - 1) if args.start is not None else 0
    end_frame = args.end if args.end is not None else total_frames
    frame_step = args.step

    # ── Resolve cutoffs ──
    interface_cutoff = args.cutoff
    water_cutoff = args.water if args.water is not None else interface_cutoff

    # ── Build pipeline params dict ──
    from cli.constants import DEFAULT_COCOMAPS_PARAMS, DEFAULT_CHART_OPTIONS
    cocomaps_params = dict(DEFAULT_COCOMAPS_PARAMS)

    # Apply JSON overrides if provided
    if args.params:
        import json
        try:
            with open(args.params) as f:
                overrides = json.load(f)
            for key, value in overrides.items():
                if key in cocomaps_params:
                    cocomaps_params[key] = value
            console.print(f"\n  [green]Loaded parameters from {args.params}[/green]")
        except Exception as e:
            console.print(f"\n  [red]Failed to load params JSON: {e}[/red]")

    pipeline = {
        'chain_a': chain_a,
        'chain_b': chain_b,
        'scope': {
            'start_frame': start_frame,
            'end_frame': end_frame,
            'frame_step': frame_step,
        },
        'use_reduce': args.reduce,
        'select_interface': True,
        'interface_cutoff': interface_cutoff,
        'water_cutoff': water_cutoff,
    }

    # ── Build chart options ──
    chart_opts = copy.deepcopy(DEFAULT_CHART_OPTIONS)
    if args.threshold is not None:
        chart_opts['global']['conservation_threshold'] = max(0, min(100, args.threshold)) / 100.0
    if args.unit is not None:
        chart_opts['global']['time_unit'] = None if args.unit.lower() == "frame" else args.unit

    # ── Output directory ──
    if args.output:
        output_dir = args.output
    else:
        pdb_stem = Path(args.pdb_file).stem
        default_dir = os.path.join('systems', pdb_stem)
        console.print()
        console.print(Panel(
            f"[bold]Results will be saved to:[/bold] {os.path.abspath(default_dir)}",
            title="Output Directory",
            border_style="cyan",
        ))
        output_dir = Prompt.ask("  Output directory", default=default_dir)

    console.print(f"  → Output: [bold]{os.path.abspath(output_dir)}[/bold]")

    # ── Show full config summary ──
    from cli.prompts import show_config_summary, interactive_customize

    show_config_summary(pipeline, cocomaps_params, chart_opts)

    # ── Customize or run ──
    if args.customize:
        interactive_customize(pipeline, cocomaps_params, chart_opts)
    else:
        from rich.prompt import Confirm
        console.print()
        if Confirm.ask("  [bold]Customize settings before running?[/bold]", default=False):
            interactive_customize(pipeline, cocomaps_params, chart_opts)

    # ── Run pipeline ──
    console.print()
    console.print("[bold green]Starting analysis…[/bold green]")

    from cli.runner import run_pipeline

    output_dir = run_pipeline(
        pdb_file=args.pdb_file,
        output_dir=output_dir,
        chain_a=pipeline['chain_a'],
        chain_b=pipeline['chain_b'],
        start_frame=pipeline['scope']['start_frame'],
        end_frame=pipeline['scope']['end_frame'],
        frame_step=pipeline['scope']['frame_step'],
        use_reduce=pipeline['use_reduce'],
        select_interface=pipeline['select_interface'],
        interface_cutoff=pipeline['interface_cutoff'],
        water_cutoff=pipeline['water_cutoff'],
        cocomaps_params=cocomaps_params,
    )

    # ── Chart generation (always runs) ──
    from cli.charts import generate_all_charts

    system_name = Path(args.pdb_file).stem

    # Determine available interaction types from output
    atom_pairs_file = os.path.join(output_dir, '_atom_pairs.csv')
    available_types = []
    if os.path.exists(atom_pairs_file):
        with open(atom_pairs_file, newline='') as f:
            for row in csv.DictReader(f):
                itype = row.get('interactionType', '').strip()
                if itype and itype not in available_types:
                    available_types.append(itype)

    # Build chart args from chart_opts
    g = chart_opts['global']
    global_controls = {
        'conservation_threshold': g['conservation_threshold'],
        'time_unit': g['time_unit'],
        'excluded_types': g['excluded_types'],
    }

    m = chart_opts['conservation_matrix']
    matrix_opts = {
        'pair_threshold': m['pair_threshold'],
        'type_threshold': m['type_threshold'],
        'atom_change_mode': m['atom_change_mode'],
    } if m['enabled'] else None

    h = chart_opts['heatmap']
    heatmap_opts = {'show_labels': h['show_labels']} if h['enabled'] else None

    t = chart_opts['trends']
    trends_opts = {'log_scale': t['log_scale']} if t['enabled'] else None

    d = chart_opts['distribution']
    distribution_opts = {
        'types': sorted(available_types),
        'min_conservation': d['min_conservation'],
    } if d['enabled'] else None

    a = chart_opts['area']
    area_opts = {
        'show_stats': a['show_stats'],
        'show_percentages': a['show_percentages'],
    } if a['enabled'] else None

    show_islands = chart_opts['conserved_islands']['enabled']

    generate_all_charts(
        system_dir=output_dir,
        system_name=system_name,
        global_controls=global_controls,
        matrix_opts=matrix_opts,
        heatmap_opts=heatmap_opts,
        trends_opts=trends_opts,
        distribution_opts=distribution_opts,
        area_opts=area_opts,
        show_islands=show_islands,
    )

    console.print("\n[bold green]All done![/bold green]\n")


if __name__ == '__main__':
    main()
