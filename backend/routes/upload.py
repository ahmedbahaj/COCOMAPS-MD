"""
Routes for PDB file upload and processing
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import sys
import uuid
import json
import threading
from datetime import datetime
from distutils.util import strtobool
import subprocess

# Ensure project root is on path for interface_selector and analyze_pdb
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Processing functions (previously in upload_server.py, now integrated here)
try:
    import MDAnalysis as mda
    from MDAnalysis.coordinates import PDB
    HAS_MDA = True
except ImportError:
    HAS_MDA = False

bp = Blueprint('upload', __name__)

# In-memory cache of job statuses (also persisted to disk)
_jobs = {}
_jobs_lock = threading.Lock()

ALLOWED_EXTENSIONS = {'pdb'}

# ---------------------------------------------------------------------------
# Persistent job helpers
# ---------------------------------------------------------------------------

def _jobs_file_path(app):
    """Return the path to the persistent .jobs.json file."""
    data_folder = app.config.get('DATA_FOLDER', app.config['UPLOAD_FOLDER'])
    systems_folder = os.path.join(data_folder, 'systems')
    os.makedirs(systems_folder, exist_ok=True)
    return os.path.join(systems_folder, '.jobs.json')


def _load_jobs(app):
    """Load jobs from disk into memory (called once at startup)."""
    global _jobs
    path = _jobs_file_path(app)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                _jobs = json.load(f)
        except Exception:
            _jobs = {}


def _persist_jobs(app):
    """Write the in-memory jobs dict to disk."""
    path = _jobs_file_path(app)
    try:
        with open(path, 'w') as f:
            json.dump(_jobs, f, indent=2)
    except Exception as e:
        print(f"[jobs] Warning: could not persist jobs: {e}")


def _update_job(app, job_id, **fields):
    """Update a job's fields and persist to disk."""
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)
            _persist_jobs(app)


def _init_jobs_for_app(app):
    """Ensure jobs are loaded for this app (idempotent)."""
    with _jobs_lock:
        if not _jobs:
            _load_jobs(app)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def split_pdb(app, job_id, pdb_file, pdb_name, chain1='A', chain2='B', interface_cutoff=5.0, water_cutoff=None, start_frame=0, end_frame=-1, frame_step=1):
    """Split PDB file into frames with per-frame interface selection (always on)."""
    if not HAS_MDA:
        raise Exception("MDAnalysis not available")

    if water_cutoff is None:
        water_cutoff = interface_cutoff

    try:
        u = mda.Universe(pdb_file)
        upload_folder = app.config['UPLOAD_FOLDER']
        systems_folder = os.path.join(upload_folder, 'systems')
        main_folder = os.path.join(systems_folder, pdb_name)

        os.makedirs(systems_folder, exist_ok=True)
        os.makedirs(main_folder, exist_ok=True)

        # Per-frame interface selection (always on)
        from interface_selector import get_atom_selections, select_interface_atoms
        from analyze_pdb import rename_waters_to_hoh
        selections = get_atom_selections(u, chain1, chain2)

        # Determine frame range
        total_frames = len(u.trajectory)
        if end_frame == -1 or end_frame > total_frames:
            end_frame = total_frames
        if start_frame < 0:
            start_frame = 0
        if frame_step < 1:
            frame_step = 1

        frames_to_process = list(range(start_frame, end_frame, frame_step))
        num_frames = len(frames_to_process)

        # Iterate through selected frames
        frame_count = 0
        for idx, frame_idx in enumerate(frames_to_process):
            u.trajectory[frame_idx]

            result = select_interface_atoms(u, selections, chain1, chain2, interface_cutoff, water_cutoff)
            output_atoms = result['atoms']
            rename_waters_to_hoh(output_atoms)

            output_frame_num = idx + 1
            frame_folder = os.path.join(main_folder, f"frame_{output_frame_num}")
            os.makedirs(frame_folder, exist_ok=True)

            frame_file = os.path.join(frame_folder, f"frame_{output_frame_num}.pdb")
            if len(output_atoms) > 0:
                output_atoms.write(frame_file)
            else:
                with open(frame_file, 'w') as f:
                    f.write("REMARK   Empty frame - no interface atoms found\nEND\n")

            create_example_input(frame_folder, f"frame_{output_frame_num}.pdb", chain1, chain2, interface_cutoff)

            frame_count += 1
            progress = int((idx + 1) / num_frames * 30)
            _update_job(app, job_id,
                        progress=progress,
                        step_label=f"Splitting frame {idx + 1}/{num_frames}")

        return frame_count
    except Exception as e:
        raise Exception(f"Error splitting PDB: {str(e)}")


def create_example_input(frame_folder, pdb_filename, chain1='A', chain2='B', interface_cutoff=5.0):
    """Create example_input.json for CoCoMaps with specified chains"""
    input_data = {
        "pdb_file": f"/app/data/{pdb_filename}",
        "chains_set_1": [chain1],
        "chains_set_2": [chain2],
        "ranges_1": [[0, 100000]],
        "ranges_2": [[0, 100000], [0, 100000]],
        "HBOND_DIST": 3.9,
        "HBOND_ANGLE": 90,
        "SBRIDGE_DIST": 4.5,
        "WBRIDGE_DIST": 3.9,
        "CH_ON_DIST": 3.6,
        "CH_ON_ANGLE": 110,
        "CUT_OFF": interface_cutoff,
        "APOLAR_TOLERANCE": 0.5,
        "POLAR_TOLERANCE": 0.5,
        "PI_PI_DIST": 5.5,
        "PI_PI_THETA": 80,
        "PI_PI_GAMMA": 90,
        "ANION_PI_DIST": 5,
        "LONEPAIR_PI_DIST": 5,
        "AMINO_PI_DIST": 5,
        "CATION_PI_DIST": 5,
        "METAL_DIST": 3.2,
        "HALOGEN_THETA1": 165,
        "HALOGEN_THETA2": 120,
        "C_H_PI_DIST": 5.0,
        "C_H_PI_THETA1": 120,
        "C_H_PI_THETA2": 30,
        "NSOH_PI_DIST": 4.5,
        "NSOH_PI_THETA1": 120,
        "NSOH_PI_THETA2": 30
    }

    json_path = os.path.join(frame_folder, "example_input.json")
    with open(json_path, 'w') as f:
        json.dump(input_data, f, indent=4)


def _get_docker_image(use_reduce: bool) -> str:
    """Select docker image based on reduce flag and environment overrides."""
    reduce_image = os.environ.get("COCOMAPS_IMAGE_REDUCE", "andrpet/cocomaps-backend:0.0.19")
    no_reduce_image = os.environ.get(
        "COCOMAPS_IMAGE_NO_REDUCE", "sattamaltwaim/cocomaps-backend:no-reduce"
    )
    return reduce_image if use_reduce else no_reduce_image


def run_cocomaps_analysis(app, job_id, pdb_name, frame_count, use_reduce=True):
    """Run CoCoMaps analysis on all frames"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        host_root_dir = os.path.abspath(os.path.join(upload_folder, 'systems', pdb_name))
        docker_image = _get_docker_image(use_reduce)
        container_execution = "python /app/coco2/begin.py"
        input_file_name = "example_input.json"

        for i in range(1, frame_count + 1):
            frame_folder = f"frame_{i}"
            container_input_path = f"/app/data/{input_file_name}"

            docker_command = (
                f"docker run --rm "
                f'-v "{host_root_dir}/{frame_folder}":/app/data '
                f"{docker_image} "
                f"{container_execution} "
                f"{container_input_path}"
            )

            _update_job(app, job_id,
                        step_label=f"Analyzing frame {i}/{frame_count}")

            subprocess.run(
                docker_command, shell=True, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )

            # Update progress (30% for splitting, 60% for analysis, remaining 10% for finalization)
            progress = 30 + int((i / frame_count) * 60)
            _update_job(app, job_id, progress=progress)

    except Exception as e:
        _update_job(app, job_id,
                    status='failed',
                    step_label='Failed',
                    error=str(e))


def process_pdb_async(app, job_id, pdb_file, pdb_name, use_reduce=True, chain1='A', chain2='B', interface_cutoff=5.0, start_frame=0, end_frame=-1, frame_step=1):
    """Process PDB file asynchronously — full pipeline"""
    with app.app_context():
        try:
            upload_folder = app.config['UPLOAD_FOLDER']
            system_dir = os.path.join(upload_folder, 'systems', pdb_name)

            # Step 1: Split PDB into frames
            _update_job(app, job_id,
                        status='splitting',
                        progress=0,
                        step_label='Preprocessing file')

            frame_count = split_pdb(app, job_id, pdb_file, pdb_name, chain1, chain2, interface_cutoff, start_frame, end_frame, frame_step)

            # Step 2: Run CoCoMaps analysis on each frame
            _update_job(app, job_id,
                        status='analyzing',
                        frames=frame_count,
                        step_label=f'Analyzing frame 1/{frame_count}')

            run_cocomaps_analysis(app, job_id, pdb_name, frame_count, use_reduce)

            # If CoCoMaps marked the job as failed, stop here
            with _jobs_lock:
                if _jobs.get(job_id, {}).get('status') == 'failed':
                    return

            # Step 3: Conserved island analysis
            _update_job(app, job_id,
                        status='finalizing',
                        progress=92,
                        step_label='Running conserved island analysis')

            try:
                import sys
                sys.path.insert(0, upload_folder)
                from conserved_islands import run_conserved_islands
                run_conserved_islands(
                    system_dir,
                    min_consistency=0.70,
                    min_island_size=2,
                    verbose=True,
                )
            except Exception as e:
                print(f"[jobs] Warning: conserved islands analysis failed: {e}")

            # Step 4: Aggregate per-frame CSVs into system-level files
            _update_job(app, job_id,
                        progress=96,
                        step_label='Aggregating results')

            try:
                from aggregate_csv import aggregate_system
                aggregate_system(system_dir, verbose=True)
            except Exception as e:
                print(f"[jobs] Warning: CSV aggregation failed: {e}")

            # Done!
            _update_job(app, job_id,
                        status='completed',
                        progress=100,
                        step_label='Completed')

        except Exception as e:
            _update_job(app, job_id,
                        status='failed',
                        step_label='Failed',
                        error=str(e))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDB files allowed'}), 400

    try:
        filename = secure_filename(file.filename)
        pdb_name = Path(filename).stem
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)

        # Extract chain parameters (defaults to A and B)
        chain1 = request.form.get('chain1', 'A')
        chain2 = request.form.get('chain2', 'B')

        # Extract cutoff parameters
        try:
            interface_cutoff = float(request.form.get('interface_cutoff', 5.0))
        except (ValueError, TypeError):
            interface_cutoff = 5.0

        # Extract frame interval parameters (1-indexed from frontend, convert to 0-indexed)
        try:
            start_frame = int(request.form.get('start_frame', 1)) - 1
            end_frame = int(request.form.get('end_frame', -1))
            if end_frame != -1:
                end_frame = end_frame
        except (ValueError, TypeError):
            start_frame = 0
            end_frame = -1

        # Extract frame step parameter
        try:
            frame_step = int(request.form.get('frame_step', 1))
            if frame_step < 1:
                frame_step = 1
        except (ValueError, TypeError):
            frame_step = 1

        # optional flag to choose no-reduce image (defaults to False for web interface)
        reduce_param = request.form.get('reduce', request.args.get('reduce'))
        use_reduce = False
        if reduce_param is not None:
            try:
                use_reduce = bool(strtobool(str(reduce_param)))
            except ValueError:
                use_reduce = False

        # Save file
        file.save(filepath)

        # Generate a unique job ID
        job_id = str(uuid.uuid4())

        # Ensure jobs are loaded
        _init_jobs_for_app(current_app)

        # Initialize job in persistent store
        with _jobs_lock:
            _jobs[job_id] = {
                'job_id': job_id,
                'pdb_name': pdb_name,
                'status': 'queued',
                'progress': 0,
                'step_label': 'Queued',
                'frames': 0,
                'reduce': use_reduce,
                'chain1': chain1,
                'chain2': chain2,
                'startFrame': start_frame + 1,
                'endFrame': end_frame if end_frame != -1 else 'all',
                'frameStep': frame_step,
                'created_at': datetime.now().isoformat()
            }
            _persist_jobs(current_app)

        # Start processing in background thread
        app_instance = current_app._get_current_object()
        thread = threading.Thread(
            target=process_pdb_async,
            args=(app_instance, job_id, filepath, pdb_name, use_reduce, chain1, chain2, interface_cutoff, start_frame, end_frame, frame_step)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'id': pdb_name,
            'message': 'Upload successful. Processing started.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status by job ID (UUID) or legacy pdb_name"""
    _init_jobs_for_app(current_app)

    with _jobs_lock:
        # Try direct job_id lookup first
        if job_id in _jobs:
            return jsonify(_jobs[job_id])

        # Fallback: search by pdb_name for backwards compatibility
        for jid, job in _jobs.items():
            if job.get('pdb_name') == job_id:
                return jsonify(job)

    return jsonify({'error': 'Not found'}), 404


@bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (active + completed + failed)"""
    _init_jobs_for_app(current_app)

    with _jobs_lock:
        jobs_list = list(_jobs.values())

    # Sort by created_at descending (newest first)
    jobs_list.sort(key=lambda j: j.get('created_at', ''), reverse=True)
    return jsonify(jobs_list)
