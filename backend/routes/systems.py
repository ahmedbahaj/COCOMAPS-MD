"""
Routes for system management
"""
from flask import Blueprint, jsonify, current_app
from pathlib import Path
import os
import re

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
                    # Count frames
                    frame_count = len(frame_folders)
                    
                    # Get chain pattern from first frame folder
                    first_frame = sorted(frame_folders, key=lambda f: f.name)[0]
                    chain1, chain2 = _get_chain_pattern(first_frame)
                    
                    systems.append({
                        'id': item.name,
                        'name': item.name,
                        'path': item.name,
                        'frames': frame_count,
                        'chain1': chain1,
                        'chain2': chain2
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
        
        # Count frames
        frame_folders = [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')]
        frame_count = len(frame_folders)
        
        # Get chain pattern from first frame folder
        chain1, chain2 = ("A", "B")  # default
        if frame_folders:
            first_frame = sorted(frame_folders, key=lambda f: f.name)[0]
            chain1, chain2 = _get_chain_pattern(first_frame)
        
        return jsonify({
            'id': system_id,
            'name': system_id,
            'path': system_id,
            'frames': frame_count,
            'chain1': chain1,
            'chain2': chain2
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

