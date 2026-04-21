"""
Routes for PDB file upload and processing
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import sys
import tempfile
import uuid
import json
import threading
from datetime import datetime
from distutils.util import strtobool

# Ensure project root is on path for engine package
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

bp = Blueprint('upload', __name__)

# In-memory cache of job statuses (also persisted to disk)
_jobs = {}
_jobs_lock = threading.Lock()

ALLOWED_EXTENSIONS = {'pdb'}

MAX_WEB_FRAMES = 50
MAX_WEB_FRAMES_SLACK = 53

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


def count_pdb_frames(filepath):
    """Count frames in a PDB file using the same logic as CLI inspect_pdb.

    Counts MODEL records first; falls back to END records for files that
    delimit frames with END instead of MODEL/ENDMDL.
    """
    model_count = 0
    end_count = 0
    with open(filepath, 'r') as fh:
        for line in fh:
            rec = line[:6].strip()
            if rec == 'MODEL':
                model_count += 1
            elif rec == 'END':
                end_count += 1
    if model_count > 0:
        return model_count
    if end_count > 1:
        return end_count
    return 1


def compute_effective_frames(total_frames, start_frame, end_frame, frame_step):
    """Return the number of frames that will actually be processed."""
    eff_end = total_frames if (end_frame == -1 or end_frame > total_frames) else end_frame
    eff_start = max(0, start_frame)
    step = max(1, frame_step)
    return len(range(eff_start, eff_end, step))


def process_pdb_async(app, job_id, pdb_file, pdb_name, system_dir, use_reduce=True, chain1='A', chain2='B', interface_cutoff=5.0, start_frame=0, end_frame=-1, frame_step=1, job_name=None, email=None):
    """Process PDB file asynchronously — full pipeline. job_name and email are written to .metadata.json on success.
    pdb_file is a temp path; it is deleted after processing. system_dir is pre-resolved by the caller."""
    with app.app_context():
        try:

            # Run the full pipeline (engine package)
            from engine import run_pipeline

            def progress_callback(step_label, progress):
                _update_job(app, job_id, step_label=step_label, progress=progress)

            frame_count, error = run_pipeline(
                pdb_file,
                system_dir,
                chain_a=chain1,
                chain_b=chain2,
                interface_cutoff=interface_cutoff,
                water_cutoff=interface_cutoff,
                use_reduce=use_reduce,
                start_frame=start_frame,
                end_frame=end_frame if end_frame != -1 else -1,
                frame_step=frame_step,
                progress_callback=progress_callback,
                verbose=False,
            )

            if error:
                _update_job(app, job_id, status='failed', step_label='Failed', error=error)
                return

            _update_job(app, job_id, frames=frame_count)

            # Mol* viewer: slim PDB from original frame 1 (non-interface), drop non-interacting waters/metals
            try:
                from engine.viewer_pdb import write_viewer_frame_pdb
                write_viewer_frame_pdb(
                    system_dir,
                    start_frame=start_frame,
                    end_frame=end_frame if end_frame != -1 else -1,
                    frame_step=frame_step,
                    verbose=False,
                )
            except Exception as viewer_err:
                print(f"[jobs] Warning: viewer PDB not written: {viewer_err}")

            # Frame folders no longer needed after aggregation + viewer PDB
            try:
                from engine.analyze_pdb import cleanup_frame_folders
                cleanup_frame_folders(system_dir, verbose=False)
            except Exception as cleanup_err:
                print(f"[jobs] Warning: frame cleanup failed: {cleanup_err}")

            # Attach public analysis jobId (from _metadata.json) so frontend can link to /analysis/<jobId>
            analysis_job_id = None
            metadata_path = os.path.join(system_dir, '_metadata.json')
            if os.path.isfile(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    analysis_job_id = meta.get('jobId') if isinstance(meta.get('jobId'), str) else None
                except Exception:
                    pass

            # Write user-facing metadata (display name, email) to .metadata.json
            display_name = job_name if (job_name and job_name.strip()) else pdb_name
            try:
                from backend.routes.systems import _set_display_name
                _set_display_name(Path(system_dir), display_name, owner_email=email or None)
            except Exception as meta_err:
                print(f"[jobs] Warning: could not write .metadata.json: {meta_err}")

            # Done! Store public jobId so API and frontend use it as the canonical link.
            _update_job(app, job_id,
                        status='completed',
                        progress=100,
                        step_label='Completed',
                        analysis_job_id=analysis_job_id)

        except Exception as e:
            _update_job(app, job_id,
                        status='failed',
                        step_label='Failed',
                        error=str(e))
        finally:
            # Remove temp upload file and temp dir (no longer needed after process_frames)
            try:
                if pdb_file and os.path.isfile(pdb_file):
                    os.unlink(pdb_file)
                temp_dir = os.path.dirname(pdb_file)
                if temp_dir and os.path.isdir(temp_dir) and 'pdb_upload_' in temp_dir:
                    os.rmdir(temp_dir)
            except OSError as cleanup_err:
                print(f"[jobs] Warning: could not remove temp upload {pdb_file}: {cleanup_err}")


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

        # Save file FIRST, before reading request.form — multipart stream is consumed in order,
        # so reading form fields first can leave the file empty.
        # Use a temp dir + original filename so engine.process_frames() copies it with the right name.
        temp_dir = tempfile.mkdtemp(prefix='pdb_upload_')
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)

        file_size = os.path.getsize(filepath)

        # Reject empty uploads (avoids "No frames to process" from empty temp file)
        if file_size == 0:
            try:
                os.unlink(filepath)
                os.rmdir(temp_dir)
            except OSError:
                pass
            return jsonify({
                'error': 'Uploaded file is empty. Check file size limits or try uploading again.'
            }), 400

        # Now safe to read form (file already saved)
        job_name = (request.form.get('job_name') or '').strip() or pdb_name
        email = (request.form.get('email') or '').strip()
        chain1 = request.form.get('chain1', 'A')
        chain2 = request.form.get('chain2', 'B')
        try:
            interface_cutoff = float(request.form.get('interface_cutoff', 5.0))
        except (ValueError, TypeError):
            interface_cutoff = 5.0
        try:
            start_frame = int(request.form.get('start_frame', 1)) - 1
            end_frame = int(request.form.get('end_frame', -1))
            if end_frame is not None and end_frame <= 0:
                end_frame = -1
        except (ValueError, TypeError):
            start_frame = 0
            end_frame = -1
        try:
            frame_step = int(request.form.get('frame_step', 1))
            if frame_step < 1:
                frame_step = 1
        except (ValueError, TypeError):
            frame_step = 1
        reduce_param = request.form.get('reduce', request.args.get('reduce'))
        use_reduce = False
        if reduce_param is not None:
            try:
                use_reduce = bool(strtobool(str(reduce_param)))
            except ValueError:
                use_reduce = False

        # ── Backend frame-count verification ──
        total_frames_in_file = count_pdb_frames(filepath)
        effective = compute_effective_frames(total_frames_in_file, start_frame, end_frame, frame_step)

        if effective > MAX_WEB_FRAMES_SLACK:
            suggested_step = -(-total_frames_in_file // MAX_WEB_FRAMES)  # ceil division
            try:
                os.unlink(filepath)
                os.rmdir(temp_dir)
            except OSError:
                pass
            return jsonify({
                'error': (
                    f'Too many frames to process ({effective}). '
                    f'The web app allows at most {MAX_WEB_FRAMES_SLACK} frames per job. '
                    f'Your file contains {total_frames_in_file} frames — use a step size '
                    f'of at least {suggested_step} to stay within the limit, '
                    f'or use the CLI for unlimited trajectory length.'
                )
            }), 400

        # Generate a unique job ID
        job_id = str(uuid.uuid4())

        # Resolve the system output directory now (before the thread starts) so
        # the exact directory stem can be stored in the job record. This lets the
        # frontend suppress the prematurely-detected 'ready' filesystem entry by
        # matching on system_id rather than pdb_name (which may differ when a
        # suffix is appended to avoid collisions with an existing directory).
        upload_folder = current_app.config['UPLOAD_FOLDER']
        base_system_dir = os.path.join(upload_folder, 'systems', pdb_name)
        system_dir = base_system_dir if not os.path.exists(base_system_dir) else base_system_dir + '_' + job_id[:8]
        system_id = os.path.basename(system_dir)

        # Ensure jobs are loaded
        _init_jobs_for_app(current_app)

        # Initialize job in persistent store
        with _jobs_lock:
            _jobs[job_id] = {
                'job_id': job_id,
                'pdb_name': pdb_name,
                'system_id': system_id,
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
            args=(app_instance, job_id, filepath, pdb_name, system_dir, use_reduce, chain1, chain2, interface_cutoff, start_frame, end_frame, frame_step, job_name, email)
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
