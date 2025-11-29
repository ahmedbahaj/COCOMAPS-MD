"""
Routes for PDB file upload and processing
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import subprocess
import threading
import json

# Processing functions (previously in upload_server.py, now integrated here)
try:
    import MDAnalysis as mda
    from MDAnalysis.coordinates import PDB
    HAS_MDA = True
except ImportError:
    HAS_MDA = False

bp = Blueprint('upload', __name__)

# Store processing status
processing_status = {}

ALLOWED_EXTENSIONS = {'pdb'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def split_pdb(pdb_file, pdb_name):
    """Split PDB file into frames"""
    if not HAS_MDA:
        raise Exception("MDAnalysis not available")
    
    try:
        u = mda.Universe(pdb_file)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        systems_folder = os.path.join(upload_folder, 'systems')
        main_folder = os.path.join(systems_folder, pdb_name)
        
        # Create systems and main folder
        os.makedirs(systems_folder, exist_ok=True)
        os.makedirs(main_folder, exist_ok=True)
        
        # Iterate through frames
        frame_count = 0
        for i, ts in enumerate(u.trajectory):
            frame_folder = os.path.join(main_folder, f"frame_{i+1}")
            os.makedirs(frame_folder, exist_ok=True)
            
            frame_file = os.path.join(frame_folder, f"frame_{i+1}.pdb")
            with PDB.PDBWriter(frame_file) as W:
                W.write(u.atoms)
            
            # Create example_input.json for each frame
            create_example_input(frame_folder, f"frame_{i+1}.pdb")
            
            frame_count += 1
            if pdb_name in processing_status:
                processing_status[pdb_name]['progress'] = int((i + 1) / len(u.trajectory) * 30)
        
        return frame_count
    except Exception as e:
        raise Exception(f"Error splitting PDB: {str(e)}")

def create_example_input(frame_folder, pdb_filename):
    """Create example_input.json for CoCoMaps"""
    input_data = {
        "pdb_file": f"/app/data/{pdb_filename}",
        "chains_set_1": ["A"],
        "chains_set_2": ["B"],
        "ranges_1": [[0, 100000]],
        "ranges_2": [[0, 100000], [0, 100000]],
        "HBOND_DIST": 3.9,
        "HBOND_ANGLE": 90,
        "SBRIDGE_DIST": 4.5,
        "WBRIDGE_DIST": 3.9,
        "CH_ON_DIST": 3.6,
        "CH_ON_ANGLE": 110,
        "CUT_OFF": 5,
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

def run_cocomaps_analysis(pdb_name, frame_count):
    """Run CoCoMaps analysis on all frames"""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        host_root_dir = os.path.abspath(os.path.join(upload_folder, 'systems', pdb_name))
        docker_image = "andrpet/cocomaps-backend:0.0.19"
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
            
            subprocess.run(
                docker_command, shell=True, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True 
            )
            
            # Update progress (30% for splitting, 70% for analysis)
            progress = 30 + int((i / frame_count) * 70)
            if pdb_name in processing_status:
                processing_status[pdb_name]['progress'] = progress
        
        if pdb_name in processing_status:
            processing_status[pdb_name]['status'] = 'completed'
            processing_status[pdb_name]['progress'] = 100
        
    except Exception as e:
        if pdb_name in processing_status:
            processing_status[pdb_name]['status'] = 'failed'
            processing_status[pdb_name]['error'] = str(e)

def process_pdb_async(pdb_file, pdb_name):
    """Process PDB file asynchronously"""
    try:
        processing_status[pdb_name]['status'] = 'splitting'
        processing_status[pdb_name]['progress'] = 0
        
        # Split PDB into frames
        frame_count = split_pdb(pdb_file, pdb_name)
        
        processing_status[pdb_name]['status'] = 'analyzing'
        processing_status[pdb_name]['frames'] = frame_count
        
        # Run CoCoMaps analysis
        run_cocomaps_analysis(pdb_name, frame_count)
        
    except Exception as e:
        if pdb_name in processing_status:
            processing_status[pdb_name]['status'] = 'failed'
            processing_status[pdb_name]['error'] = str(e)

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
        
        # Save file
        file.save(filepath)
        
        # Initialize processing status
        processing_status[pdb_name] = {
            'status': 'queued',
            'progress': 0,
            'frames': 0
        }
        
        # Start processing in background thread
        thread = threading.Thread(target=process_pdb_async, args=(filepath, pdb_name))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'id': pdb_name,
            'message': 'Upload successful. Processing started.'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/status/<pdb_id>', methods=['GET'])
def get_status(pdb_id):
    """Get processing status"""
    if pdb_id not in processing_status:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify(processing_status[pdb_id])

