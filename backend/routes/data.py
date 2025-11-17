"""
Routes for data retrieval
"""
from flask import Blueprint, jsonify, current_app
from pathlib import Path
import csv
import os

bp = Blueprint('data', __name__)

@bp.route('/systems/<system_id>/interactions', methods=['GET'])
def get_interactions(system_id):
    """
    Get all interaction data for a system across all frames
    Returns aggregated interaction data with consistency scores
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders and sort numerically by frame number
        frame_folders = sorted(
            [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')],
            key=lambda f: int(f.name.split('_')[1]) if '_' in f.name else f.name
        )
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        total_frames = len(frame_folders)
        interaction_map = {}
        
        # Process each frame
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_final_file.csv"
            
            if not csv_file.exists():
                continue
            
            # Parse CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip if required fields are missing
                    if not all(key in row for key in ['Res. Name 1', 'Res. Number 1', 'Chain 1', 
                                                      'Res. Name 2', 'Res. Number 2', 'Chain 2']):
                        continue
                    
                    # Create unique key for residue-residue interaction
                    key = f"{row['Res. Name 1']}{row['Res. Number 1']}_{row['Res. Name 2']}{row['Res. Number 2']}"
                    
                    if key not in interaction_map:
                        interaction_map[key] = {
                            'resName1': row['Res. Name 1'],
                            'resNum1': int(row['Res. Number 1']),
                            'chain1': row['Chain 1'],
                            'resName2': row['Res. Name 2'],
                            'resNum2': int(row['Res. Number 2']),
                            'chain2': row['Chain 2'],
                            'frames': [],
                            'types': set(),
                            'typeFrames': {}  # Track frames per interaction type
                        }
                    
                    interaction_map[key]['frames'].append(frame_num)
                    if row.get('Type of Interactions'):
                        # Handle multiple types separated by semicolon
                        types = [t.strip() for t in row['Type of Interactions'].split(';') if t.strip()]
                        for t in types:
                            interaction_map[key]['types'].add(t)
                            # Track which frames this type appears in
                            if t not in interaction_map[key]['typeFrames']:
                                interaction_map[key]['typeFrames'][t] = []
                            interaction_map[key]['typeFrames'][t].append(frame_num)
        
        # Convert to array with consistency scores
        interactions = []
        for key, entry in interaction_map.items():
            frame_set = set(entry['frames'])
            typesArray = list(entry['types'])
            
            # Calculate per-type persistence
            typePersistence = {}
            for interaction_type in typesArray:
                if interaction_type in entry['typeFrames']:
                    type_frame_set = set(entry['typeFrames'][interaction_type])
                    typePersistence[interaction_type] = len(type_frame_set) / total_frames
                else:
                    typePersistence[interaction_type] = 0.0
            
            interactions.append({
                'resName1': entry['resName1'],
                'resNum1': entry['resNum1'],
                'chain1': entry['chain1'],
                'resName2': entry['resName2'],
                'resNum2': entry['resNum2'],
                'chain2': entry['chain2'],
                'frameCount': len(frame_set),
                'consistency': len(frame_set) / total_frames,
                'id1': f"{entry['chain1']}-{entry['resName1']}{entry['resNum1']}",
                'id2': f"{entry['chain2']}-{entry['resName2']}{entry['resNum2']}",
                'typesArray': typesArray,
                'typePersistence': typePersistence,
                'frames': sorted(list(frame_set))  # Sorted list of frame numbers where interaction occurs
            })
        
        # Sort by consistency
        interactions.sort(key=lambda x: x['consistency'], reverse=True)
        
        return jsonify({
            'system': system_id,
            'totalFrames': total_frames,
            'interactions': interactions
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/systems/<system_id>/area', methods=['GET'])
def get_area_data(system_id):
    """
    Get area data (BSA) for a system across all frames
    Returns Total, POLAR, and NON POLAR buried surface area
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders
        frame_folders = sorted([f for f in system_path.iterdir() 
                               if f.is_dir() and f.name.startswith('frame_')])
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        frames_data = []
        
        # Process each frame
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_complex.pdb_Rsa_stats.csv"
            
            if not csv_file.exists():
                continue
            
            total_bsa = 0
            polar_bsa = 0
            non_polar_bsa = 0
            total_percent = 0
            polar_percent = 0
            non_polar_percent = 0
            
            # Parse CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Get row index from first column (empty header)
                    row_index_str = row.get('', '').strip()
                    if not row_index_str:
                        continue
                    
                    try:
                        row_index = int(row_index_str)
                    except ValueError:
                        continue
                    
                    value = row.get('Value', '')
                    
                    # Row 0: Total BSA
                    if row_index == 0:
                        match = __extract_first_number(value)
                        if match:
                            total_bsa = float(match)
                    
                    # Row 1: Total BSA percentage
                    elif row_index == 1:
                        match = __extract_first_number(value)
                        if match:
                            total_percent = float(match)
                    
                    # Row 2: POLAR BSA
                    elif row_index == 2:
                        match = __extract_first_number(value)
                        if match:
                            polar_bsa = float(match)
                    
                    # Row 3: POLAR percentage
                    elif row_index == 3:
                        match = __extract_first_number(value)
                        if match:
                            polar_percent = float(match)
                    
                    # Row 4: NON POLAR BSA
                    elif row_index == 4:
                        match = __extract_first_number(value)
                        if match:
                            non_polar_bsa = float(match)
                    
                    # Row 5: NON POLAR percentage
                    elif row_index == 5:
                        match = __extract_first_number(value)
                        if match:
                            non_polar_percent = float(match)
            
            frames_data.append({
                'frame': frame_num,
                'totalBSA': total_bsa,
                'polarBSA': polar_bsa,
                'nonPolarBSA': non_polar_bsa,
                'totalPercent': total_percent,
                'polarPercent': polar_percent,
                'nonPolarPercent': non_polar_percent
            })
        
        return jsonify({
            'system': system_id,
            'frames': frames_data
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/systems/<system_id>/trends', methods=['GET'])
def get_interaction_trends(system_id):
    """
    Get interaction type trends across frames
    Returns counts for each interaction type per frame
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders
        frame_folders = sorted([f for f in system_path.iterdir() 
                               if f.is_dir() and f.name.startswith('frame_')])
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        interaction_types = {
            'H-bonds': [],
            'Salt-bridges': [],
            'π-π interactions': [],
            'Cation-π interactions': [],
            'Anion-π interactions': [],
            'CH-O/N bonds': [],
            'CH-π interactions': [],
            'Halogen bonds': [],
            'Apolar vdW contacts': [],
            'Polar vdW contacts': [],
            'Proximal contacts': [],
            'Clashes': []
        }
        
        # Process each frame
        for frame_folder in frame_folders:
            csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_summary_table.csv"
            
            if not csv_file.exists():
                continue
            
            # Initialize frame values
            for key in interaction_types:
                interaction_types[key].append(0)
            
            # Parse CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    property_name = row.get('Property', '')
                    value = int(row.get('Value', 0))
                    
                    if 'H-bonds' in property_name:
                        interaction_types['H-bonds'][-1] = value
                    elif 'Salt-bridges' in property_name:
                        interaction_types['Salt-bridges'][-1] = value
                    elif 'π-π interactions' in property_name and 'Cation' not in property_name and 'Anion' not in property_name:
                        interaction_types['π-π interactions'][-1] = value
                    elif 'Cation-π' in property_name:
                        interaction_types['Cation-π interactions'][-1] = value
                    elif 'Anion-π' in property_name:
                        interaction_types['Anion-π interactions'][-1] = value
                    elif 'CH-O/N bonds' in property_name:
                        interaction_types['CH-O/N bonds'][-1] = value
                    elif 'CH-π interactions' in property_name:
                        interaction_types['CH-π interactions'][-1] = value
                    elif 'Halogen bonds' in property_name:
                        interaction_types['Halogen bonds'][-1] = value
                    elif 'Apolar vdW' in property_name:
                        interaction_types['Apolar vdW contacts'][-1] = value
                    elif 'Polar vdW' in property_name:
                        interaction_types['Polar vdW contacts'][-1] = value
                    elif 'Proximal contacts' in property_name:
                        interaction_types['Proximal contacts'][-1] = value
                    elif 'Clashes' in property_name:
                        interaction_types['Clashes'][-1] = value
        
        return jsonify({
            'system': system_id,
            'trends': interaction_types
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/systems/<system_id>/similarity-matrix', methods=['GET'])
def get_similarity_matrix(system_id):
    """
    Calculate Tanimoto similarity matrix for all frames
    Returns an N×N matrix where each cell represents similarity between two frames
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders and sort numerically
        frame_folders = sorted(
            [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')],
            key=lambda f: int(f.name.split('_')[1]) if '_' in f.name else f.name
        )
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        total_frames = len(frame_folders)
        
        # Extract actual frame numbers and create mapping
        actual_frame_numbers = []
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            actual_frame_numbers.append(frame_num)
        actual_frame_numbers.sort()
        frame_to_index = {frame_num: idx for idx, frame_num in enumerate(actual_frame_numbers)}
        index_to_frame = {idx: frame_num for idx, frame_num in enumerate(actual_frame_numbers)}
        
        # Step 1: Collect all unique residue pairs across all frames
        all_residue_pairs = set()
        frame_interactions = {}  # frame_num -> set of residue pair keys
        
        # Process each frame to build fingerprints
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_final_file.csv"
            
            if not csv_file.exists():
                frame_interactions[frame_num] = set()
                continue
            
            frame_pairs = set()
            
            # Parse CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip if required fields are missing
                    if not all(key in row for key in ['Res. Name 1', 'Res. Number 1', 'Chain 1', 
                                                      'Res. Name 2', 'Res. Number 2', 'Chain 2']):
                        continue
                    
                    # Create unique key for residue-residue interaction
                    # Normalize: always put smaller chain/residue first for consistency
                    chain1 = row['Chain 1']
                    chain2 = row['Chain 2']
                    res1 = f"{row['Res. Name 1']}{row['Res. Number 1']}"
                    res2 = f"{row['Res. Name 2']}{row['Res. Number 2']}"
                    
                    # Create normalized pair key (smaller chain first, then by residue number)
                    if chain1 < chain2 or (chain1 == chain2 and int(row['Res. Number 1']) < int(row['Res. Number 2'])):
                        pair_key = f"{chain1}-{res1}_{chain2}-{res2}"
                    else:
                        pair_key = f"{chain2}-{res2}_{chain1}-{res1}"
                    
                    frame_pairs.add(pair_key)
                    all_residue_pairs.add(pair_key)
            
            frame_interactions[frame_num] = frame_pairs
        
        # Step 2: Create sorted list of all residue pairs (for consistent indexing)
        sorted_pairs = sorted(list(all_residue_pairs))
        pair_to_index = {pair: idx for idx, pair in enumerate(sorted_pairs)}
        
        # Step 3: Build binary fingerprints for each frame (by index)
        fingerprints = {}
        for idx in range(total_frames):
            frame_num = index_to_frame[idx]
            fingerprint = [0] * len(sorted_pairs)
            if frame_num in frame_interactions:
                for pair in frame_interactions[frame_num]:
                    if pair in pair_to_index:
                        fingerprint[pair_to_index[pair]] = 1
            fingerprints[idx] = fingerprint
        
        # Step 4: Calculate pairwise Tanimoto similarity
        # Tanimoto = intersection / union = (A ∩ B) / (A ∪ B)
        similarity_matrix = []
        
        for i in range(total_frames):
            row = []
            fp_i = fingerprints[i]
            
            for j in range(total_frames):
                fp_j = fingerprints[j]
                
                # Calculate intersection (common interactions)
                intersection = sum(1 for k in range(len(fp_i)) if fp_i[k] == 1 and fp_j[k] == 1)
                
                # Calculate union (total unique interactions)
                union = sum(1 for k in range(len(fp_i)) if fp_i[k] == 1 or fp_j[k] == 1)
                
                # Tanimoto coefficient
                if union == 0:
                    similarity = 1.0  # Both frames have no interactions
                else:
                    similarity = intersection / union
                
                row.append(round(similarity, 4))
            
            similarity_matrix.append(row)
        
        return jsonify({
            'system': system_id,
            'totalFrames': total_frames,
            'matrix': similarity_matrix,
            'frameLabels': actual_frame_numbers
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def __extract_first_number(value_str):
    """Extract first numeric value from strings like '2331.8 / 1165.9' or '25.35%'"""
    import re
    if not value_str:
        return None
    slash_match = re.match(r'\s*([0-9]+(?:\.[0-9]+)?)\s*/', value_str)
    if slash_match:
        return slash_match.group(1)
    number_match = re.search(r'([0-9]+(?:\.[0-9]+)?)', value_str)
    return number_match.group(1) if number_match else None

