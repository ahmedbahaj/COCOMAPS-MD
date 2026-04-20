"""
Routes for system management
"""
from flask import Blueprint, jsonify, current_app, request
from pathlib import Path
import os
import re
from datetime import datetime
import json

bp = Blueprint('systems', __name__)


def _get_chain_pattern(frame_folder):
    """
    Detect the chain pattern (e.g., 'A_B', 'A_C') from CSV files in frame folder.
    Returns tuple (chain1, chain2) or ('A', 'B') as default fallback.
    """
    pattern = re.compile(r'\.pd[b_h\.]*_([A-Z])_([A-Z])_final_file\.csv$')
    for f in frame_folder.iterdir():
        if f.is_file():
            match = pattern.search(f.name)
            if match:
                return (match.group(1), match.group(2))
    return ("A", "B")  # fallback default


def _get_display_name(system_path, default_name):
    """Get display name from metadata file if it exists"""
    metadata_file = system_path / '.metadata.json'
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get('displayName', default_name)
        except:
            pass
    return default_name


def _get_frame_count_from_metadata(system_path, fallback_count):
    """Get totalFrames from _metadata.json when it exists, else return fallback (from frame folder count)."""
    meta = system_path / '_metadata.json'
    if meta.exists():
        try:
            with open(meta, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tf = data.get('totalFrames')
            if tf is not None and isinstance(tf, (int, float)) and tf > 0:
                return int(tf)
        except Exception:
            pass
    return fallback_count


def _get_job_info_from_metadata(system_path):
    """
    Read job-related fields from _metadata.json when available.
    Returns dict with keys: jobId, jobCreatedAt, jobExpiresAt (values may be None).
    """
    meta = system_path / '_metadata.json'
    result = {
        'jobId': None,
        'jobCreatedAt': None,
        'jobExpiresAt': None,
    }
    if not meta.exists():
        return result

    try:
        with open(meta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            result['jobId'] = data.get('jobId')
            result['jobCreatedAt'] = data.get('jobCreatedAt')
            result['jobExpiresAt'] = data.get('jobExpiresAt')
    except Exception:
        # Ignore metadata errors; job fields remain None.
        pass

    return result


def _is_example_system(system_path):
    """Check if a system is a bundled example (has isExample: true in _metadata.json)."""
    meta = system_path / '_metadata.json'
    if not meta.exists():
        return False
    try:
        with open(meta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return bool(data.get('isExample'))
    except Exception:
        return False


def _set_display_name(system_path, display_name, owner_email=None):
    """Set display name and optionally owner email in .metadata.json"""
    metadata_file = system_path / '.metadata.json'
    metadata = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception:
            pass
    metadata['displayName'] = display_name
    if owner_email is not None:
        metadata['ownerEmail'] = owner_email
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
        f.write('\n')


@bp.route('/systems', methods=['GET'])
def list_systems():
    """List all available systems"""
    try:
        data_folder = current_app.config['DATA_FOLDER']
        systems_folder = Path(data_folder) / 'systems'
        
        # Check if systems folder exists
        if not systems_folder.exists():
            return jsonify([])
        
        systems = []
        
        for item in systems_folder.iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
                # Check if it has frame folders
                frame_folders = [f for f in item.iterdir() if f.is_dir() and f.name.startswith('frame_')]
                
                if frame_folders:
                    # Use totalFrames from _metadata.json when available (deployment: CSVs only)
                    frame_count = _get_frame_count_from_metadata(item, len(frame_folders))

                    # Get chain pattern from first frame folder
                    first_frame = sorted(frame_folders, key=lambda f: f.name)[0]
                    chain1, chain2 = _get_chain_pattern(first_frame)
                    
                    # Get folder modification time as creation date
                    mod_time = os.path.getmtime(item)
                    date_created = datetime.fromtimestamp(mod_time).isoformat()
                    
                    # Get display name from metadata
                    display_name = _get_display_name(item, item.name)

                    # Get job info from _metadata.json (public analysis job id)
                    job_info = _get_job_info_from_metadata(item)
                    
                    systems.append({
                        'id': item.name,
                        'name': display_name,
                        'path': item.name,
                        'frames': frame_count,
                        'chain1': chain1,
                        'chain2': chain2,
                        'dateCreated': date_created,
                        'status': 'ready',
                        'jobId': job_info['jobId'],
                        'jobCreatedAt': job_info['jobCreatedAt'],
                        'jobExpiresAt': job_info['jobExpiresAt'],
                        'isExample': _is_example_system(item),
                    })
        
        # Sort by name
        systems.sort(key=lambda x: x['name'])
        
        return jsonify(systems)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/systems/<system_id>', methods=['GET'])
def get_system(system_id):
    """Get details for a specific system"""
    try:
        data_folder = current_app.config['DATA_FOLDER']
        systems_folder = Path(data_folder) / 'systems'
        system_path = systems_folder / system_id
        
        if not system_path.exists() or not system_path.is_dir():
            return jsonify({'error': 'System not found'}), 404
        
        # Use totalFrames from _metadata.json when available (deployment: CSVs only)
        frame_folders = [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')]
        frame_count = _get_frame_count_from_metadata(system_path, len(frame_folders))

        # Get chain pattern from first frame folder
        chain1, chain2 = ("A", "B")  # default
        if frame_folders:
            first_frame = sorted(frame_folders, key=lambda f: f.name)[0]
            chain1, chain2 = _get_chain_pattern(first_frame)
        
        # Get display name from metadata if exists
        display_name = _get_display_name(system_path, system_id)

        # Get job info from _metadata.json (public analysis job id)
        job_info = _get_job_info_from_metadata(system_path)
        
        # Get folder modification time
        mod_time = os.path.getmtime(system_path)
        date_created = datetime.fromtimestamp(mod_time).isoformat()
        
        return jsonify({
            'id': system_id,
            'name': display_name,
            'path': system_id,
            'frames': frame_count,
            'chain1': chain1,
            'chain2': chain2,
            'dateCreated': date_created,
            'status': 'ready',
            'jobId': job_info['jobId'],
            'jobCreatedAt': job_info['jobCreatedAt'],
            'jobExpiresAt': job_info['jobExpiresAt'],
            'isExample': _is_example_system(system_path),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/systems/<system_id>/rename', methods=['POST'])
def rename_system(system_id):
    """Rename a system (updates display name, not folder)"""
    try:
        data_folder = current_app.config['DATA_FOLDER']
        systems_folder = Path(data_folder) / 'systems'
        system_path = systems_folder / system_id
        
        if not system_path.exists() or not system_path.is_dir():
            return jsonify({'error': 'System not found'}), 404
        
        data = request.get_json()
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'error': 'Name is required'}), 400
        
        # Save display name to metadata
        _set_display_name(system_path, new_name)
        
        return jsonify({
            'success': True,
            'id': system_id,
            'name': new_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

