"""
Analysis pipeline runner with rich progress bars.
"""
import os
import sys
import json
import time
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel

from cli.constants import DEFAULT_COCOMAPS_PARAMS

console = Console()

# ── Resolve project root so we can import sibling modules ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _resolve_docker_image(use_reduce: bool) -> str:
    """Pick the correct Docker image based on .env / defaults."""
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / '.env')

    if use_reduce:
        return os.environ.get(
            "COCOMAPS_IMAGE_REDUCE", "andrpet/cocomaps-backend:0.0.19"
        )
    return os.environ.get(
        "COCOMAPS_IMAGE_NO_REDUCE", "sattamaltwaim/cocomaps-backend:no-reduce"
    )


def run_pipeline(
    pdb_file: str,
    output_dir: str,
    chain_a: str = 'A',
    chain_b: str = 'B',
    start_frame: int = 0,
    end_frame: int = -1,
    frame_step: int = 1,
    use_reduce: bool = False,
    select_interface: bool = True,
    interface_cutoff: float = 5.0,
    water_cutoff: float = 5.0,
    cocomaps_params: dict | None = None,
) -> str:
    """
    Run the full analysis pipeline with rich progress bars.

    Returns the output directory path.
    """
    if cocomaps_params is None:
        cocomaps_params = dict(DEFAULT_COCOMAPS_PARAMS)

    chains = [chain_a, chain_b]
    overall_start = time.time()

    console.print()
    console.print(Panel(
        "[bold]Starting PDB Analysis Pipeline[/bold]",
        title="Pipeline",
        border_style="green",
    ))

    # ──────────────────────────────────────────────────────────────────────
    # STEP 1: Split / process frames
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 1/5[/bold cyan] — Splitting PDB into frames …")

    # --- Raw-text frame splitting (handles variable atom counts) ---
    # Read MODEL/ENDMDL blocks from the PDB file so we don't rely on
    # MDAnalysis trajectory indexing, which crashes when atom counts
    # differ between frames.
    raw_frames = []  # list of frame text strings
    with open(pdb_file, 'r') as fh:
        current_frame_lines = []
        in_model = False
        for line in fh:
            record = line[:6].strip()
            if record == 'MODEL':
                in_model = True
                current_frame_lines = [line]
            elif record == 'ENDMDL':
                current_frame_lines.append(line)
                raw_frames.append(''.join(current_frame_lines))
                current_frame_lines = []
                in_model = False
            elif in_model:
                current_frame_lines.append(line)

    # Fallback: if no MODEL records, split by END records.
    # Some multi-frame PDBs use END instead of MODEL/ENDMDL.
    if not raw_frames:
        with open(pdb_file, 'r') as fh:
            current_frame_lines = []
            for line in fh:
                record = line[:6].strip()
                if record == 'END':
                    if current_frame_lines:
                        raw_frames.append(''.join(current_frame_lines))
                        current_frame_lines = []
                else:
                    current_frame_lines.append(line)
            # Capture any trailing content without a final END
            if current_frame_lines:
                raw_frames.append(''.join(current_frame_lines))

    total_frames_raw = len(raw_frames)

    # Determine slice
    if end_frame == -1 or end_frame > total_frames_raw:
        end_frame = total_frames_raw
    if start_frame < 0:
        start_frame = 0
    frame_step = max(1, frame_step)

    frames_to_process = list(range(start_frame, end_frame, frame_step))
    num_frames = len(frames_to_process)

    os.makedirs(output_dir, exist_ok=True)

    # Optionally copy original PDB
    original_name = Path(pdb_file).name
    dest = os.path.join(output_dir, original_name)
    if not os.path.exists(dest):
        shutil.copy(pdb_file, dest)

    # Rename waters helper
    from analyze_pdb import rename_waters_to_hoh

    import MDAnalysis as mda

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Splitting frames", total=num_frames)

        for idx, frame_idx in enumerate(frames_to_process):
            output_frame_num = idx + 1
            frame_folder = os.path.join(output_dir, f"frame_{output_frame_num}")
            os.makedirs(frame_folder, exist_ok=True)
            frame_file = os.path.join(frame_folder, f"frame_{output_frame_num}.pdb")

            # Write raw frame to a temp file, load it, apply interface selection
            raw_text = raw_frames[frame_idx]
            tmp_frame = os.path.join(frame_folder, '_tmp_raw.pdb')
            with open(tmp_frame, 'w') as f:
                f.write(raw_text)
                if not raw_text.rstrip().endswith('END'):
                    f.write('END\n')

            try:
                u = mda.Universe(tmp_frame)

                if select_interface:
                    from interface_selector import get_atom_selections, select_interface_atoms
                    selections = get_atom_selections(u, chain_a, chain_b)
                    result = select_interface_atoms(
                        u, selections, chain_a, chain_b, interface_cutoff, water_cutoff
                    )
                    output_atoms = result['atoms']
                else:
                    output_atoms = u.atoms

                rename_waters_to_hoh(output_atoms)

                if len(output_atoms) > 0:
                    output_atoms.write(frame_file)
                else:
                    with open(frame_file, 'w') as f:
                        f.write("REMARK   Empty frame - no interface atoms found\nEND\n")
            finally:
                if os.path.exists(tmp_frame):
                    os.remove(tmp_frame)

            progress.update(task, advance=1)

    console.print(f"  [green]✓[/green] Split into {num_frames} frames")

    # ──────────────────────────────────────────────────────────────────────
    # STEP 2: Create input JSON files (with merged CoCoMaps params)
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 2/5[/bold cyan] — Creating CoCoMaps input files …")

    input_file_name = os.environ.get("INPUT_FILE_NAME", "example_input.json")

    for i in range(1, num_frames + 1):
        frame_folder = os.path.join(output_dir, f"frame_{i}")
        json_data = {
            "pdb_file": f"/app/data/frame_{i}.pdb",
            "chains_set_1": [chain_a],
            "chains_set_2": [chain_b],
            "ranges_1": [[0, 100000]],
            "ranges_2": [[0, 100000], [0, 100000]],
            **cocomaps_params,
        }

        json_path = os.path.join(frame_folder, input_file_name)
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=4)

    console.print(f"  [green]✓[/green] Created {num_frames} input JSON files")

    # ──────────────────────────────────────────────────────────────────────
    # STEP 3: Run CoCoMaps Docker on each frame
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 3/5[/bold cyan] — Running CoCoMaps analysis …")

    docker_image = _resolve_docker_image(use_reduce)
    successful = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing frames", total=num_frames)

        for i in range(1, num_frames + 1):
            progress.update(task, description=f"Analyzing frame {i}/{num_frames}")
            frame_folder = f"frame_{i}"
            frame_path = os.path.join(output_dir, frame_folder)
            container_input_path = f"/app/data/{input_file_name}"

            abs_frame_path = os.path.abspath(frame_path)

            # Docker Desktop on macOS cannot mount paths with spaces/special chars.
            # Workaround: copy frame files to a temp dir under /tmp, run Docker there,
            # then copy results back.
            needs_tmp = ' ' in abs_frame_path or '!' in abs_frame_path
            tmp_dir = None

            try:
                if needs_tmp:
                    tmp_dir = tempfile.mkdtemp(prefix='pdb_cli_')
                    # Copy all files from frame dir to tmp
                    for fname in os.listdir(abs_frame_path):
                        src = os.path.join(abs_frame_path, fname)
                        dst = os.path.join(tmp_dir, fname)
                        if os.path.isfile(src):
                            shutil.copy2(src, dst)
                    mount_path = tmp_dir
                else:
                    mount_path = abs_frame_path

                docker_command = [
                    'docker', 'run', '--rm',
                    '-v', f'{mount_path}:/app/data',
                    docker_image,
                    'python', '/app/coco2/begin.py', container_input_path,
                ]

                subprocess.run(
                    docker_command, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                )
                successful += 1

                # Copy results back from tmp to real frame dir
                if needs_tmp and tmp_dir:
                    for fname in os.listdir(tmp_dir):
                        src = os.path.join(tmp_dir, fname)
                        dst = os.path.join(abs_frame_path, fname)
                        if os.path.isfile(src) and not os.path.exists(dst):
                            shutil.copy2(src, dst)

            except subprocess.CalledProcessError as e:
                failed += 1
                console.print(f"  [red]✗[/red] Frame {i} failed: {str(e.output)[:100]}")
            finally:
                if tmp_dir and os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir, ignore_errors=True)

            progress.update(task, advance=1)

    console.print(f"  [green]✓[/green] CoCoMaps: {successful}/{num_frames} successful, {failed} failed")

    # ──────────────────────────────────────────────────────────────────────
    # STEP 4: Conserved island analysis
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 4/5[/bold cyan] — Running conserved island analysis …")

    try:
        from conserved_islands import run_conserved_islands
        run_conserved_islands(
            output_dir,
            min_consistency=0.70,
            min_island_size=2,
            verbose=False,
        )
        console.print("  [green]✓[/green] Conserved island analysis complete")
    except Exception as e:
        console.print(f"  [yellow]Warning: Conserved islands failed: {e}[/yellow]")

    # ──────────────────────────────────────────────────────────────────────
    # STEP 5: Aggregate CSV files
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 5/5[/bold cyan] — Aggregating system CSV files …")

    try:
        from aggregate_csv import aggregate_system
        aggregate_system(output_dir, verbose=False)
        console.print("  [green]✓[/green] CSV aggregation complete")
    except Exception as e:
        console.print(f"  [yellow]Warning: Aggregation failed: {e}[/yellow]")

    # ── Summary ──
    total_time = time.time() - overall_start
    console.print()
    console.print(Panel(
        f"[bold green]Pipeline complete![/bold green]\n"
        f"Total time: {total_time:.1f}s ({total_time / 60:.1f} min)\n"
        f"Frames analyzed: {successful}/{num_frames}\n"
        f"Output: {output_dir}",
        title="Complete",
        border_style="green",
    ))

    return output_dir
