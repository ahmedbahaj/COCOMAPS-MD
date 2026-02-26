"""
Interactive CLI prompts using rich for styled output.
"""
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import box

from cli.constants import (
    INTERACTION_TYPES,
    DEFAULT_COCOMAPS_PARAMS,
    get_interaction_color_hex,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Pre-analysis prompts
# ─────────────────────────────────────────────────────────────────────────────

def prompt_chain_selection(chains: list[str]) -> tuple[str, str]:
    """
    Display detected chains and ask the user to pick two.

    Returns (chain_a, chain_b).
    """
    console.print()
    console.print(Panel(
        f"[bold]Detected chains:[/bold] {', '.join(chains)}",
        title="Chain Detection",
        border_style="cyan",
    ))

    if len(chains) < 2:
        console.print("[yellow]Warning: Less than 2 chains detected.[/yellow]")
        chain_a = Prompt.ask("  Enter Chain A", default=chains[0] if chains else "A")
        chain_b = Prompt.ask("  Enter Chain B", default="B")
    elif len(chains) == 2:
        console.print(f"  Using [bold]{chains[0]}[/bold] and [bold]{chains[1]}[/bold]")
        if not Confirm.ask("  Use these chains?", default=True):
            chain_a = Prompt.ask("  Enter Chain A", default=chains[0])
            chain_b = Prompt.ask("  Enter Chain B", default=chains[1])
        else:
            chain_a, chain_b = chains[0], chains[1]
    else:
        chain_a = Prompt.ask(
            f"  Select Chain A",
            default=chains[0],
            choices=chains,
        )
        remaining = [c for c in chains if c != chain_a]
        chain_b = Prompt.ask(
            f"  Select Chain B",
            default=remaining[0] if remaining else chains[1],
            choices=remaining if remaining else chains,
        )

    console.print(f"  → Chains: [bold cyan]{chain_a}[/bold cyan] and [bold cyan]{chain_b}[/bold cyan]")
    return chain_a, chain_b


def prompt_trajectory_scope(total_frames: int) -> dict:
    """
    Ask the user about the trajectory scope.

    Returns dict with keys: start_frame, end_frame, frame_step
    (0-indexed start, exclusive end, like Python range)
    """
    console.print()
    console.print(Panel(
        f"[bold]Total frames in trajectory:[/bold] {total_frames}",
        title="Trajectory Scope",
        border_style="cyan",
    ))

    if Confirm.ask(f"  Analyze the entire trajectory ({total_frames} frames)?", default=True):
        # Offer step size if many frames
        if total_frames > 50:
            console.print(f"  [dim]Tip: {total_frames} frames is large. You can use a step size to sample.[/dim]")
            use_step = Confirm.ask("  Use a step size to sub-sample?", default=False)
            if use_step:
                while True:
                    step = IntPrompt.ask("  Step size (every Nth frame)", default=1)
                    step = max(1, step)
                    effective = len(range(0, total_frames, step))
                    console.print(f"  → Will analyze [bold]{effective}[/bold] frames (step={step})")
                    if Confirm.ask("  Continue with this selection?", default=True):
                        return {'start_frame': 0, 'end_frame': total_frames, 'frame_step': step}
                    console.print("  [dim]Enter a different step size.[/dim]")

        return {'start_frame': 0, 'end_frame': total_frames, 'frame_step': 1}
    else:
        # Choose mode
        mode = Prompt.ask(
            "  Select mode",
            choices=["interval", "step"],
            default="interval",
        )

        if mode == "interval":
            start = IntPrompt.ask("  Start frame (1-indexed)", default=1)
            end = IntPrompt.ask("  End frame (1-indexed, inclusive)", default=total_frames)
            start = max(1, min(start, total_frames))
            end = max(start, min(end, total_frames))
            effective = end - start + 1
            console.print(f"  → Frames {start} to {end} ({effective} frames)")
            return {'start_frame': start - 1, 'end_frame': end, 'frame_step': 1}
        else:
            while True:
                step = IntPrompt.ask("  Step size (every Nth frame)", default=2)
                step = max(1, step)
                effective = len(range(0, total_frames, step))
                console.print(f"  → Will analyze [bold]{effective}[/bold] frames (step={step})")
                if Confirm.ask("  Continue with this selection?", default=True):
                    return {'start_frame': 0, 'end_frame': total_frames, 'frame_step': step}
                console.print("  [dim]Enter a different step size.[/dim]")


def prompt_parameters(
    chain_a: str,
    chain_b: str,
    scope: dict,
    use_reduce: bool,
    select_interface: bool,
    interface_cutoff: float,
    water_cutoff: float,
    cocomaps_params: dict | None = None,
) -> dict:
    """
    Display the full parameter table and allow modification.

    Returns the final parameters dict (including CoCoMaps params).
    """
    if cocomaps_params is None:
        cocomaps_params = dict(DEFAULT_COCOMAPS_PARAMS)

    # Mutable pipeline params dict for inline editing (interface selection always on)
    pipeline = {
        'chain_1': chain_a,
        'chain_2': chain_b,
        'use_reduce': use_reduce,
        'select_interface': True,
        'interface_cutoff': interface_cutoff,
        'water_cutoff': water_cutoff,
    }

    console.print()

    # ── Pipeline parameters table ──
    pipeline_table = Table(
        title="Pipeline Parameters",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    pipeline_table.add_column("Parameter", style="bold")
    pipeline_table.add_column("Value", style="green")

    pipeline_table.add_row("chain_1", pipeline['chain_1'])
    pipeline_table.add_row("chain_2", pipeline['chain_2'])
    pipeline_table.add_row("Start Frame", str(scope['start_frame'] + 1))
    pipeline_table.add_row("End Frame", str(scope['end_frame']))
    pipeline_table.add_row("Frame Step", str(scope['frame_step']))
    pipeline_table.add_row("use_reduce", "Yes" if pipeline['use_reduce'] else "No")
    pipeline_table.add_row("select_interface", "Yes" if pipeline['select_interface'] else "No")
    pipeline_table.add_row("interface_cutoff", f"{pipeline['interface_cutoff']} Å")
    pipeline_table.add_row("water_cutoff", f"{pipeline['water_cutoff']} Å")

    console.print(pipeline_table)

    # ── CoCoMaps parameters table ──
    coco_table = Table(
        title="CoCoMaps Parameters",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    coco_table.add_column("Parameter", style="bold")
    coco_table.add_column("Value", style="green")

    for key, value in cocomaps_params.items():
        coco_table.add_row(key, str(value))

    console.print(coco_table)

    # ── Modify? ──
    if Confirm.ask("\n  Modify parameters?", default=False):
        json_path = Prompt.ask(
            "  Enter path to JSON parameter file (or 'inline' for manual editing)",
            default="inline",
        )

        # All editable keys (pipeline + cocomaps)
        all_params = {**pipeline, **cocomaps_params}

        if json_path != "inline" and Path(json_path).exists():
            with open(json_path) as f:
                overrides = json.load(f)

            # Apply overrides to both pipeline and cocomaps
            for key, value in overrides.items():
                if key in pipeline:
                    pipeline[key] = value
                    console.print(f"  [green]✓[/green] {key} = {value}")
                elif key in cocomaps_params:
                    cocomaps_params[key] = value
                    console.print(f"  [green]✓[/green] {key} = {value}")
                else:
                    console.print(f"  [yellow]Warning: Unknown key: {key}[/yellow]")

            console.print(f"  [green]Loaded {len(overrides)} override(s) from {json_path}[/green]")
        elif json_path == "inline":
            console.print("  [dim]Editable pipeline keys: chain_1, chain_2, use_reduce (yes/no),[/dim]")
            console.print("  [dim]  interface_cutoff, water_cutoff (interface selection is always on)[/dim]")
            console.print("  [dim]Editable CoCoMaps keys: any key shown above (e.g. HBOND_DIST=3.5)[/dim]")
            console.print("  [dim]Enter changes as key=value. Type 'done' when finished.[/dim]")
            while True:
                entry = Prompt.ask("  ", default="done")
                if entry.lower() == "done":
                    break
                if "=" not in entry:
                    console.print("  [red]Use format: KEY=VALUE[/red]")
                    continue
                key, value = entry.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key in pipeline:
                    # Handle booleans (select_interface is always on and not editable)
                    if key == 'select_interface':
                        console.print("  [dim]Interface selection is always on; change ignored.[/dim]")
                    elif key == 'use_reduce':
                        pipeline[key] = value.lower() in ('yes', 'true', '1', 'y')
                        console.print(f"  [green]✓[/green] {key} = {'Yes' if pipeline[key] else 'No'}")
                    # Handle floats
                    elif key in ('interface_cutoff', 'water_cutoff'):
                        try:
                            pipeline[key] = float(value)
                            console.print(f"  [green]✓[/green] {key} = {pipeline[key]}")
                        except ValueError:
                            console.print(f"  [red]Invalid float for {key}[/red]")
                    # Handle strings (chains)
                    else:
                        pipeline[key] = value
                        console.print(f"  [green]✓[/green] {key} = {value}")
                elif key in cocomaps_params:
                    try:
                        cocomaps_params[key] = type(cocomaps_params[key])(value)
                        console.print(f"  [green]✓[/green] {key} = {cocomaps_params[key]}")
                    except ValueError:
                        console.print(f"  [red]Invalid value for {key}[/red]")
                else:
                    console.print(f"  [yellow]Unknown parameter: {key}[/yellow]")
        else:
            console.print(f"  [red]File not found: {json_path}[/red]")

    return {
        'chain_a': pipeline['chain_1'],
        'chain_b': pipeline['chain_2'],
        'scope': scope,
        'use_reduce': pipeline['use_reduce'],
        'select_interface': True,
        'interface_cutoff': pipeline['interface_cutoff'],
        'water_cutoff': pipeline['water_cutoff'],
        'cocomaps_params': cocomaps_params,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Post-analysis prompts (chart generation)
# ─────────────────────────────────────────────────────────────────────────────

def prompt_global_chart_controls() -> dict:
    """
    Prompt for global chart controls shared across multiple charts.

    Returns dict with:
        conservation_threshold: float (0.0–1.0)
        time_unit: str | None
        excluded_interaction_types: set of type IDs to EXCLUDE
    """
    console.print()
    console.print(Panel(
        "[bold]Configure chart generation settings[/bold]",
        title="Chart Generation",
        border_style="green",
    ))

    # ── Conservation threshold ──
    threshold_pct = IntPrompt.ask(
        "  Conservation threshold (0–100%)",
        default=50,
    )
    threshold_pct = max(0, min(100, threshold_pct))
    threshold = threshold_pct / 100.0
    console.print(f"  → Conservation threshold: [bold]{threshold_pct}%[/bold]")

    # ── Time unit ──
    console.print()
    console.print("  [bold]Time axis label:[/bold]")
    console.print("  [dim]Options: Frame (default), fs, ps, ns, μs, ms, or custom[/dim]")
    time_unit_input = Prompt.ask("  Time unit", default="Frame")
    time_unit = None if time_unit_input.lower() == "frame" else time_unit_input

    # ── Interaction type filter ──
    console.print()
    console.print("  [bold]Interaction type filter:[/bold]")
    console.print("  [dim]By default, all types except 'Proximal contacts' are included.[/dim]")

    if Confirm.ask("  Modify interaction type filter?", default=False):
        # Start with proximal excluded by default
        excluded = {'proximal'}

        # Show numbered list with current state
        def _print_type_list():
            for idx, t in enumerate(INTERACTION_TYPES, 1):
                color_hex = get_interaction_color_hex(t['label'])
                state = "[red]OFF[/red]" if t['id'] in excluded else "[green]ON[/green]"
                console.print(f"    {idx:2d}. [{color_hex}]●[/{color_hex}] {t['label']}  {state}")

        _print_type_list()
        console.print()
        console.print("  [dim]Enter a number to toggle on/off, or 'done' to finish.[/dim]")

        while True:
            entry = Prompt.ask("  Toggle #", default="done")
            if entry.lower() == "done":
                break
            try:
                num = int(entry)
                if 1 <= num <= len(INTERACTION_TYPES):
                    tid = INTERACTION_TYPES[num - 1]['id']
                    label = INTERACTION_TYPES[num - 1]['label']
                    if tid in excluded:
                        excluded.discard(tid)
                        console.print(f"    [green]ON[/green]  {label}")
                    else:
                        excluded.add(tid)
                        console.print(f"    [red]OFF[/red] {label}")
                else:
                    console.print(f"  [red]Invalid number. Use 1-{len(INTERACTION_TYPES)}.[/red]")
            except ValueError:
                console.print("  [red]Enter a number or 'done'.[/red]")
    else:
        excluded = {'proximal'}

    included_count = len(INTERACTION_TYPES) - len(excluded)
    console.print(f"  → {included_count}/{len(INTERACTION_TYPES)} interaction types selected")

    return {
        'conservation_threshold': threshold,
        'time_unit': time_unit,
        'excluded_types': excluded,
    }


def prompt_conservation_matrix_options() -> dict | None:
    """Prompt for Conservation Matrix chart-specific options. Returns None if skipped."""
    console.print()
    if not Confirm.ask("  Generate [bold]Conservation Matrix[/bold]?", default=True):
        return None

    pair_threshold = IntPrompt.ask(
        "    Pair conservation threshold (0–100%)", default=50,
    )
    pair_threshold = max(0, min(100, pair_threshold)) / 100.0

    type_threshold = IntPrompt.ask(
        "    Interaction type conservation threshold (50–100%)", default=50,
    )
    type_threshold = max(50, min(100, type_threshold)) / 100.0

    console.print("    [bold]Atom change detection mode:[/bold]")
    console.print("    [dim]  previous — compare to the previous frame[/dim]")
    console.print("    [dim]  dominant — compare to the most frequent atom pair[/dim]")
    console.print("    [dim]  first    — compare to the first frame[/dim]")
    atom_change_mode = Prompt.ask(
        "    Mode",
        choices=["previous", "dominant", "first"],
        default="previous",
    )

    return {
        'pair_threshold': pair_threshold,
        'type_threshold': type_threshold,
        'atom_change_mode': atom_change_mode,
    }


def prompt_heatmap_options() -> dict | None:
    """Prompt for Interaction Heatmap chart-specific options. Returns None if skipped."""
    console.print()
    if not Confirm.ask("  Generate [bold]Interaction Heatmap[/bold]?", default=True):
        return None

    show_labels = Confirm.ask("    Show residue labels?", default=True)
    return {'show_labels': show_labels}


def prompt_trends_options() -> dict | None:
    """Prompt for Interaction Trends chart-specific options. Returns None if skipped."""
    console.print()
    if not Confirm.ask("  Generate [bold]Interaction Trends[/bold] (line chart)?", default=True):
        return None

    log_scale = Confirm.ask("    Use logarithmic scale?", default=False)
    return {'log_scale': log_scale}


def prompt_distribution_options(available_types: list[str]) -> dict | None:
    """Prompt for Distance Distribution (violin) chart options. Returns None if skipped."""
    console.print()
    if not Confirm.ask("  Generate [bold]Distance Distribution[/bold] (violin plots)?", default=True):
        return None

    if not available_types:
        console.print("    [yellow]No interaction types available for Distance Distribution.[/yellow]")
        return None

    console.print("    [dim]One chart will be generated per interaction type.[/dim]")
    console.print("    [bold]Available types:[/bold]")
    for t in available_types:
        color_hex = get_interaction_color_hex(t)
        console.print(f"      [{color_hex}]●[/{color_hex}] {t}")

    min_conservation = IntPrompt.ask(
        "    Min conservation threshold for pairs (0–100%)", default=50,
    )
    min_conservation = max(0, min(100, min_conservation))

    return {
        'types': available_types,
        'min_conservation': min_conservation,
    }


def prompt_area_options() -> dict | None:
    """Prompt for Area Composition chart-specific options. Returns None if skipped."""
    console.print()
    if not Confirm.ask("  Generate [bold]Area Composition[/bold] (BSA chart)?", default=True):
        return None

    show_stats = Confirm.ask("    Show Mean ± Std Dev bands?", default=True)
    show_percentages = Confirm.ask("    Show percentages?", default=False)
    return {'show_stats': show_stats, 'show_percentages': show_percentages}


def prompt_conserved_islands_options() -> bool:
    """Prompt whether to display Conserved Islands summary. Returns True/False."""
    console.print()
    return Confirm.ask("  Display [bold]Conserved Islands[/bold] summary?", default=True)
