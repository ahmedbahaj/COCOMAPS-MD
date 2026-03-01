"""
Interactive CLI prompts using rich for styled output.

Two main entry points:
  - show_config_summary()  → display-only, no prompting
  - interactive_customize() → numbered section picker for expert tweaking
"""
import copy
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
    DEFAULT_CHART_OPTIONS,
    get_interaction_color_hex,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def show_config_summary(pipeline: dict, cocomaps: dict, chart_opts: dict):
    """
    Render a rich summary of ALL current settings (pipeline, CoCoMaps, charts).
    Pure display — no prompting.
    """
    # ── Pipeline parameters ──
    pt = Table(
        title="Pipeline Parameters",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    pt.add_column("Parameter", style="bold")
    pt.add_column("Value", style="green")

    pt.add_row("Chain A", pipeline['chain_a'])
    pt.add_row("Chain B", pipeline['chain_b'])
    pt.add_row("Start Frame", str(pipeline['scope']['start_frame'] + 1))
    pt.add_row("End Frame", str(pipeline['scope']['end_frame']))
    pt.add_row("Frame Step", str(pipeline['scope']['frame_step']))
    pt.add_row("Use Reduce", "Yes" if pipeline.get('use_reduce') else "No")
    pt.add_row("Interface Cutoff", f"{pipeline['interface_cutoff']} Å")
    pt.add_row("Water Cutoff", f"{pipeline['water_cutoff']} Å")

    console.print()
    console.print(pt)

    # ── CoCoMaps parameters ──
    ct = Table(
        title="CoCoMaps Parameters",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    ct.add_column("Parameter", style="bold")
    ct.add_column("Value", style="green")
    for key, value in cocomaps.items():
        ct.add_row(key, str(value))
    console.print(ct)

    # ── Chart settings ──
    cht = Table(
        title="Chart Settings",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    cht.add_column("Chart", style="bold")
    cht.add_column("Enabled", justify="center")
    cht.add_column("Key Options", style="dim")

    g = chart_opts['global']
    cht.add_row(
        "Global",
        "—",
        f"threshold={int(g['conservation_threshold']*100)}%, "
        f"time_unit={g['time_unit'] or 'Frame'}, "
        f"excluded={','.join(g['excluded_types']) or 'none'}",
    )

    m = chart_opts['conservation_matrix']
    cht.add_row(
        "Conservation Matrix",
        _yn_colored(m['enabled']),
        f"pair={int(m['pair_threshold']*100)}%, type={int(m['type_threshold']*100)}%, mode={m['atom_change_mode']}",
    )
    h = chart_opts['heatmap']
    cht.add_row("Interaction Heatmap", _yn_colored(h['enabled']), f"labels={_yn(h['show_labels'])}")

    t = chart_opts['trends']
    cht.add_row("Interaction Trends", _yn_colored(t['enabled']), f"log_scale={_yn(t['log_scale'])}")

    d = chart_opts['distribution']
    cht.add_row("Distance Distribution", _yn_colored(d['enabled']), f"min_conservation={d['min_conservation']}%")

    a = chart_opts['area']
    cht.add_row("Area Composition", _yn_colored(a['enabled']), f"stats={_yn(a['show_stats'])}, pct={_yn(a['show_percentages'])}")

    ci = chart_opts['conserved_islands']
    cht.add_row("Conserved Islands", _yn_colored(ci['enabled']), "")

    console.print(cht)


def _yn(val) -> str:
    """Format a bool as Yes/No."""
    return "Yes" if val else "No"


def _yn_colored(val) -> str:
    """Format a bool as Yes/No with green/red markup."""
    return "[green]Yes[/green]" if val else "[red]No[/red]"


# ─────────────────────────────────────────────────────────────────────────────
# Interactive customization (--customize mode)
# ─────────────────────────────────────────────────────────────────────────────

def interactive_customize(pipeline: dict, cocomaps: dict, chart_opts: dict):
    """
    Numbered section picker for expert customization.
    Modifies all three dicts in-place.
    """
    while True:
        console.print()
        console.print(Panel(
            "[bold]Which section would you like to customize?[/bold]\n\n"
            "  [cyan]1.[/cyan] Pipeline (chains, frames, cutoffs)\n"
            "  [cyan]2.[/cyan] CoCoMaps parameters\n"
            "  [cyan]3.[/cyan] Chart settings\n"
            "  [cyan]4.[/cyan] Done — run with current settings",
            title="Customize",
            border_style="yellow",
        ))

        choice = Prompt.ask("  Section", choices=["1", "2", "3", "4"], default="4")

        if choice == "1":
            _customize_pipeline(pipeline)
        elif choice == "2":
            _customize_cocomaps(cocomaps)
        elif choice == "3":
            _customize_charts(chart_opts)
        else:
            break

    # Re-show the final config
    show_config_summary(pipeline, cocomaps, chart_opts)


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: Pipeline customization
# ─────────────────────────────────────────────────────────────────────────────

def _customize_pipeline(pipeline: dict):
    """Inline editing of pipeline parameters."""
    console.print()
    console.print("[bold]Pipeline parameters[/bold]  [dim](type KEY=VALUE, 'done' to finish)[/dim]")
    console.print("  [dim]Editable: chain_a, chain_b, start_frame, end_frame, frame_step,[/dim]")
    console.print("  [dim]          use_reduce (yes/no), interface_cutoff, water_cutoff[/dim]")

    # Flatten scope into pipeline for editing
    flat = {
        'chain_a': pipeline['chain_a'],
        'chain_b': pipeline['chain_b'],
        'start_frame': pipeline['scope']['start_frame'],
        'end_frame': pipeline['scope']['end_frame'],
        'frame_step': pipeline['scope']['frame_step'],
        'use_reduce': pipeline.get('use_reduce', False),
        'interface_cutoff': pipeline['interface_cutoff'],
        'water_cutoff': pipeline['water_cutoff'],
    }

    while True:
        entry = Prompt.ask("  ", default="done")
        if entry.lower() == "done":
            break
        if "=" not in entry:
            console.print("  [red]Use format: KEY=VALUE[/red]")
            continue
        key, value = entry.split("=", 1)
        key, value = key.strip(), value.strip()

        if key not in flat:
            console.print(f"  [yellow]Unknown parameter: {key}[/yellow]")
            continue

        if key == 'use_reduce':
            flat[key] = value.lower() in ('yes', 'true', '1', 'y')
            console.print(f"  [green]✓[/green] {key} = {'Yes' if flat[key] else 'No'}")
        elif key in ('chain_a', 'chain_b'):
            flat[key] = value
            console.print(f"  [green]✓[/green] {key} = {value}")
        else:
            try:
                if key in ('start_frame', 'end_frame', 'frame_step'):
                    flat[key] = int(value)
                else:
                    flat[key] = float(value)
                console.print(f"  [green]✓[/green] {key} = {flat[key]}")
            except ValueError:
                console.print(f"  [red]Invalid value for {key}[/red]")

    # Write back
    pipeline['chain_a'] = flat['chain_a']
    pipeline['chain_b'] = flat['chain_b']
    pipeline['scope'] = {
        'start_frame': flat['start_frame'],
        'end_frame': flat['end_frame'],
        'frame_step': flat['frame_step'],
    }
    pipeline['use_reduce'] = flat['use_reduce']
    pipeline['interface_cutoff'] = flat['interface_cutoff']
    pipeline['water_cutoff'] = flat['water_cutoff']


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: CoCoMaps customization
# ─────────────────────────────────────────────────────────────────────────────

def _customize_cocomaps(cocomaps: dict):
    """Inline editing of CoCoMaps parameters or load from JSON."""
    console.print()
    console.print("[bold]CoCoMaps parameters[/bold]")
    mode = Prompt.ask(
        "  Edit inline or load from JSON file?",
        choices=["inline", "json"],
        default="inline",
    )

    if mode == "json":
        json_path = Prompt.ask("  Path to JSON file")
        if Path(json_path).exists():
            with open(json_path) as f:
                overrides = json.load(f)
            for key, value in overrides.items():
                if key in cocomaps:
                    cocomaps[key] = value
                    console.print(f"  [green]✓[/green] {key} = {value}")
                else:
                    console.print(f"  [yellow]Unknown key: {key}[/yellow]")
        else:
            console.print(f"  [red]File not found: {json_path}[/red]")
        return

    console.print("  [dim]Type KEY=VALUE (e.g. HBOND_DIST=3.5), 'done' to finish.[/dim]")
    while True:
        entry = Prompt.ask("  ", default="done")
        if entry.lower() == "done":
            break
        if "=" not in entry:
            console.print("  [red]Use format: KEY=VALUE[/red]")
            continue
        key, value = entry.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in cocomaps:
            try:
                cocomaps[key] = type(cocomaps[key])(value)
                console.print(f"  [green]✓[/green] {key} = {cocomaps[key]}")
            except ValueError:
                console.print(f"  [red]Invalid value for {key}[/red]")
        else:
            console.print(f"  [yellow]Unknown parameter: {key}[/yellow]")


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: Chart customization
# ─────────────────────────────────────────────────────────────────────────────

def _customize_charts(chart_opts: dict):
    """
    Show all chart settings and let the user toggle/modify them.
    """
    console.print()
    console.print("[bold]Chart settings[/bold]")

    # ── Global settings ──
    console.print("\n  [bold underline]Global[/bold underline]")

    g = chart_opts['global']
    t_pct = IntPrompt.ask("  Conservation threshold (0–100%)", default=int(g['conservation_threshold'] * 100))
    g['conservation_threshold'] = max(0, min(100, t_pct)) / 100.0

    time_input = Prompt.ask("  Time unit (Frame, fs, ps, ns, μs, ms, custom)", default=g['time_unit'] or "Frame")
    g['time_unit'] = None if time_input.lower() == "frame" else time_input

    if Confirm.ask("  Modify interaction type filter?", default=False):
        _toggle_interaction_filter(g['excluded_types'])

    # ── Per-chart toggles and options ──
    chart_sections = [
        ('conservation_matrix', 'Conservation Matrix', [
            ('pair_threshold', 'Pair threshold (0–100%)', 'pct'),
            ('type_threshold', 'Type threshold (50–100%)', 'pct'),
            ('atom_change_mode', 'Mode (previous/dominant/first)', 'choice:previous,dominant,first'),
        ]),
        ('heatmap', 'Interaction Heatmap', [
            ('show_labels', 'Show residue labels?', 'bool'),
        ]),
        ('trends', 'Interaction Trends', [
            ('log_scale', 'Use logarithmic scale?', 'bool'),
        ]),
        ('distribution', 'Distance Distribution', [
            ('min_conservation', 'Min conservation (0–100%)', 'int'),
        ]),
        ('area', 'Area Composition', [
            ('show_stats', 'Show Mean ± Std Dev bands?', 'bool'),
            ('show_percentages', 'Show percentages?', 'bool'),
        ]),
        ('conserved_islands', 'Conserved Islands', []),
    ]

    for key, label, options in chart_sections:
        section = chart_opts[key]
        console.print(f"\n  [bold underline]{label}[/bold underline]  [{'green' if section['enabled'] else 'red'}]{'ON' if section['enabled'] else 'OFF'}[/{'green' if section['enabled'] else 'red'}]")
        section['enabled'] = Confirm.ask(f"  Enable {label}?", default=section['enabled'])

        if section['enabled'] and options:
            for opt_key, opt_label, opt_type in options:
                current = section[opt_key]
                if opt_type == 'bool':
                    section[opt_key] = Confirm.ask(f"    {opt_label}", default=current)
                elif opt_type == 'pct':
                    val = IntPrompt.ask(f"    {opt_label}", default=int(current * 100))
                    section[opt_key] = max(0, min(100, val)) / 100.0
                elif opt_type == 'int':
                    section[opt_key] = IntPrompt.ask(f"    {opt_label}", default=current)
                elif opt_type.startswith('choice:'):
                    choices = opt_type.split(':')[1].split(',')
                    section[opt_key] = Prompt.ask(f"    {opt_label}", choices=choices, default=current)


def _toggle_interaction_filter(excluded: set):
    """Toggle interaction types on/off."""
    def _print_list():
        for idx, t in enumerate(INTERACTION_TYPES, 1):
            color_hex = get_interaction_color_hex(t['label'])
            state = "[red]OFF[/red]" if t['id'] in excluded else "[green]ON[/green]"
            console.print(f"    {idx:2d}. [{color_hex}]●[/{color_hex}] {t['label']}  {state}")

    _print_list()
    console.print("  [dim]Enter a number to toggle, or 'done' to finish.[/dim]")

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
