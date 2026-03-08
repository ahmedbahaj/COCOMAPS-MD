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

# Ensure project root is on path for analyze_pdb (engine)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

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


def process_pdb_async(app, job_id, pdb_file, pdb_name, use_reduce=True, chain1='A', chain2='B', interface_cutoff=5.0, start_frame=0, end_frame=-1, frame_step=1, job_name=None, email=None):
    """Process PDB file asynchronously — full pipeline. job_name and email are written to .metadata.json on success.
    pdb_file is a temp path; it is deleted after processing."""
    with app.app_context():
        try:
            upload_folder = app.config['UPLOAD_FOLDER']
            system_dir = os.path.join(upload_folder, 'systems', pdb_name)

            # Run the full pipeline (engine lives in analyze_pdb.py only)
            from analyze_pdb import run_pipeline

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
        # Use a temp dir + original filename so analyze_pdb.process_frames() copies it with the right name.
        temp_dir = tempfile.mkdtemp(prefix='pdb_upload_')
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)

        # Reject empty uploads (avoids "No frames to process" from empty temp file)
        if os.path.getsize(filepath) == 0:
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
            args=(app_instance, job_id, filepath, pdb_name, use_reduce, chain1, chain2, interface_cutoff, start_frame, end_frame, frame_step, job_name, email)
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
