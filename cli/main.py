"""
CLI entry point for PDB trajectory analysis.

Usage:
    pdb-cli [pdb_file] [OPTIONS]
    python -m cli [pdb_file] [OPTIONS]
"""
import argparse
import os
import sys
import warnings
from pathlib import Path

# Suppress noisy MDAnalysis/NumPy warnings — keep terminal clean
warnings.filterwarnings('ignore', module='MDAnalysis')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='numpy')

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

# ── Ensure the project root is on sys.path ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _print_welcome():
    """Show the welcome banner."""
    console.print()
    console.print(Panel(
        "[bold]PDB Trajectory Analysis CLI[/bold]\n"
        "[dim]Local version of the web GUI pipeline[/dim]\n\n"
        "Analyze PDB trajectories, compute residue-level interactions\n"
        "via CoCoMaps, and generate publication-ready charts.",
        border_style="blue",
        padding=(1, 4),
    ))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='pdb-cli',
        description='PDB Trajectory Analysis CLI — local tool matching the web GUI pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  pdb-cli                                          # interactive mode
  pdb-cli systems/my_protein.pdb
  pdb-cli systems/my_protein.pdb -c A B
  pdb-cli systems/my_protein.pdb --interface --interface-cutoff 7.0
  pdb-cli systems/my_protein.pdb --no-interactive --no-charts
  pdb-cli systems/my_protein.pdb -p custom_params.json
        """,
    )

    parser.add_argument('pdb_file', nargs='?', default=None,
                        help='Path to input PDB file (prompted if omitted)')
    parser.add_argument('-c', '--chains', nargs=2, metavar=('A', 'B'),
                        help='Chain IDs to analyze (default: auto-detect)')
    parser.add_argument('-o', '--output', help='Output directory (default: systems/<pdb_name>)')
    parser.add_argument('--use-reduce', action='store_true', default=False,
                        help='Use reduce version of CoCoMaps')
    parser.add_argument('--interface', action='store_true', default=False,
                        help='Enable per-frame interface selection')
    parser.add_argument('--interface-cutoff', type=float, default=5.0,
                        help='Interface selection cutoff in Å (default: 5.0)')
    parser.add_argument('--water-cutoff', type=float, default=None,
                        help='Bridging water cutoff in Å (default: same as interface-cutoff)')
    parser.add_argument('-p', '--params-json', default=None,
                        help='Path to JSON file with CoCoMaps parameters')
    parser.add_argument('--no-interactive', action='store_true', default=False,
                        help='Skip all interactive prompts, use defaults')
    parser.add_argument('--no-charts', action='store_true', default=False,
                        help='Skip chart generation after analysis')

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── Welcome banner ──
    _print_welcome()

    # ── Prompt for PDB file if not provided ──
    if args.pdb_file is None:
        from rich.prompt import Prompt
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

    # ── Chain selection ──
    from cli.prompts import (
        prompt_chain_selection,
        prompt_trajectory_scope,
        prompt_parameters,
        prompt_global_chart_controls,
        prompt_conservation_matrix_options,
        prompt_heatmap_options,
        prompt_trends_options,
        prompt_distribution_options,
        prompt_area_options,
        prompt_conserved_islands_options,
    )
    from cli.constants import DEFAULT_COCOMAPS_PARAMS

    if args.chains:
        chain_a, chain_b = args.chains
        console.print(f"\n  Chains (from args): [bold cyan]{chain_a}[/bold cyan] and [bold cyan]{chain_b}[/bold cyan]")
    elif args.no_interactive:
        chains = info['chains']
        chain_a = chains[0] if len(chains) >= 1 else 'A'
        chain_b = chains[1] if len(chains) >= 2 else 'B'
        console.print(f"\n  Chains (auto): [bold cyan]{chain_a}[/bold cyan] and [bold cyan]{chain_b}[/bold cyan]")
    else:
        chain_a, chain_b = prompt_chain_selection(info['chains'])

    # ── Trajectory scope ──
    if args.no_interactive:
        scope = {'start_frame': 0, 'end_frame': info['total_frames'], 'frame_step': 1}
        console.print(f"\n  Trajectory: all {info['total_frames']} frames")
    else:
        scope = prompt_trajectory_scope(info['total_frames'])

    # ── Output directory ──
    if args.output:
        output_dir = args.output
    else:
        pdb_stem = Path(args.pdb_file).stem
        output_dir = os.path.join('systems', pdb_stem)

    if not args.no_interactive:
        console.print()
        console.print(Panel(
            f"[bold]Results will be saved to:[/bold] {os.path.abspath(output_dir)}",
            title="Output Directory",
            border_style="cyan",
        ))
        if not Confirm.ask("  Use this output path?", default=True):
            output_dir = Prompt.ask("  Enter output directory path", default=output_dir)
        console.print(f"  → Output: [bold]{os.path.abspath(output_dir)}[/bold]")

    # ── Water cutoff ──
    water_cutoff = args.water_cutoff if args.water_cutoff is not None else args.interface_cutoff

    # ── CoCoMaps parameters ──
    cocomaps_params = dict(DEFAULT_COCOMAPS_PARAMS)
    if args.params_json:
        import json
        try:
            with open(args.params_json) as f:
                overrides = json.load(f)
            for key, value in overrides.items():
                if key in cocomaps_params:
                    cocomaps_params[key] = value
            console.print(f"\n  [green]Loaded parameters from {args.params_json}[/green]")
        except Exception as e:
            console.print(f"\n  [red]Failed to load params JSON: {e}[/red]")

    # ── Parameter review ──
    if args.no_interactive:
        params = {
            'chain_a': chain_a,
            'chain_b': chain_b,
            'scope': scope,
            'use_reduce': args.use_reduce,
            'select_interface': args.interface,
            'interface_cutoff': args.interface_cutoff,
            'water_cutoff': water_cutoff,
            'cocomaps_params': cocomaps_params,
        }
    else:
        params = prompt_parameters(
            chain_a, chain_b, scope,
            args.use_reduce, args.interface,
            args.interface_cutoff, water_cutoff,
            cocomaps_params,
        )

    # ── Confirm and run ──
    if not args.no_interactive:
        console.print()
        if not Confirm.ask("[bold green]Start analysis?[/bold green]", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            sys.exit(0)

    # ── Run pipeline ──
    from cli.runner import run_pipeline

    output_dir = run_pipeline(
        pdb_file=args.pdb_file,
        output_dir=output_dir,
        chain_a=params['chain_a'],
        chain_b=params['chain_b'],
        start_frame=params['scope']['start_frame'],
        end_frame=params['scope']['end_frame'],
        frame_step=params['scope']['frame_step'],
        use_reduce=params['use_reduce'],
        select_interface=params['select_interface'],
        interface_cutoff=params['interface_cutoff'],
        water_cutoff=params['water_cutoff'],
        cocomaps_params=params['cocomaps_params'],
    )

    # ── Chart generation ──
    if args.no_charts:
        console.print("\n[dim]Chart generation skipped (--no-charts).[/dim]")
        sys.exit(0)

    from cli.charts import generate_all_charts

    system_name = Path(args.pdb_file).stem

    if args.no_interactive:
        # Use defaults
        global_controls = {
            'conservation_threshold': 0.5,
            'time_unit': None,
            'excluded_types': {'proximal'},
        }
        matrix_opts = {
            'pair_threshold': 0.5,
            'type_threshold': 0.5,
            'atom_change_mode': 'previous',
        }
        heatmap_opts = {'show_labels': True}
        trends_opts = {'log_scale': False}
        area_opts = {'show_stats': True, 'show_percentages': False}
        # Find available interaction types from _atom_pairs.csv
        import csv
        atom_pairs_file = os.path.join(output_dir, '_atom_pairs.csv')
        available_types = []
        if os.path.exists(atom_pairs_file):
            with open(atom_pairs_file, newline='') as f:
                for row in csv.DictReader(f):
                    itype = row.get('interactionType', '').strip()
                    if itype and itype not in available_types:
                        available_types.append(itype)
        distribution_opts = {'types': sorted(available_types), 'min_conservation': 50}
        show_islands = True
    else:
        # Interactive prompts for chart generation
        global_controls = prompt_global_chart_controls()
        matrix_opts = prompt_conservation_matrix_options()
        heatmap_opts = prompt_heatmap_options()
        trends_opts = prompt_trends_options()

        # Determine available types from _atom_pairs.csv
        import csv
        atom_pairs_file = os.path.join(output_dir, '_atom_pairs.csv')
        available_types = []
        if os.path.exists(atom_pairs_file):
            with open(atom_pairs_file, newline='') as f:
                for row in csv.DictReader(f):
                    itype = row.get('interactionType', '').strip()
                    if itype and itype not in available_types:
                        available_types.append(itype)

        distribution_opts = prompt_distribution_options(sorted(available_types))
        area_opts = prompt_area_options()
        show_islands = prompt_conserved_islands_options()

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
