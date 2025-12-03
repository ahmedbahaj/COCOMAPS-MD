"""
Routes for data retrieval
"""
from flask import Blueprint, jsonify, current_app
from pathlib import Path
import csv
import os

bp = Blueprint('data', __name__)


def _normalize_interaction_type(type_label):
    """Map equivalent interaction labels to a single canonical value.
    Handles both singular and plural forms as they appear in final_file.csv
    """
    if not type_label:
        return None
    clean_label = type_label.strip()
    lower_label = clean_label.lower()

    # Normalize all interaction type variants to canonical names
    # Based on COCOMAPS2 output file naming conventions
    # Note: final_file.csv uses singular forms, but we normalize to plural for consistency
    
    if 'h-bond' in lower_label or 'hydrogen bond' in lower_label:
        return 'H-bond'
    elif 'salt-bridge' in lower_label or 'salt bridge' in lower_label:
        return 'Salt-bridge'
    elif 'π-π' in clean_label or 'pi-pi' in lower_label or 'pi pi' in lower_label:
        return 'π-π interactions'
    elif 'cation-π' in lower_label or 'cation-pi' in lower_label or 'cation_pi' in lower_label:
        return 'Cation-π interactions'
    elif 'anion-π' in lower_label or 'anion-pi' in lower_label or 'anion_pi' in lower_label:
        return 'Anion-π interactions'
    elif 'ch-o/n' in lower_label or 'c-h_on' in lower_label or 'c-h on' in lower_label or 'ch-on' in lower_label:
        return 'CH-O/N bonds'
    elif 'ch-π' in lower_label or 'ch-pi' in lower_label or 'c-h_pi' in lower_label or 'ch-π interaction' in lower_label:
        return 'CH-π interactions'
    elif 'halogen' in lower_label:
        return 'Halogen bonds'
    elif 'apolar vdw' in lower_label or 'apolar_vdw' in lower_label:
        return 'Apolar vdW contacts'
    elif 'polar vdw' in lower_label or 'polar_vdw' in lower_label:
        return 'Polar vdW contacts'
    elif 'proximal' in lower_label:
        return 'Proximal contacts'
    elif 'clash' in lower_label:
        return 'Clashes'
    elif 'metal mediated' in lower_label or 'metal_mediated' in lower_label or 'metal-mediated' in lower_label:
        return 'Metal-mediated contacts'
    elif 'n-s-o-h' in lower_label or 'n-s-o-h_pi' in lower_label or 'o/n/sh' in lower_label or 'ons-oh-pi' in lower_label:
        return 'O/N/SH-π interactions'
    elif 'lone pair' in lower_label or 'lone_pair' in lower_label or 'lp-π' in lower_label or 'lp-pi' in lower_label:
        return 'lp-π interactions'
    elif 'water mediated' in lower_label or 'water_mediated' in lower_label or 'water-mediated' in lower_label:
        return 'Water-mediated contacts'
    elif 's-s bond' in lower_label or 'ss bond' in lower_label or 'ss_bond' in lower_label or 's-s' in lower_label:
        return 'S-S bond'
    elif 'amino-pi' in lower_label or 'amino_pi' in lower_label or 'polar-π' in lower_label or 'polar-pi' in lower_label:
        return 'Amino-π interactions'
    
    return clean_label

@bp.route('/systems/<system_id>/interactions', methods=['GET'])
def get_interactions(system_id):
    """
    Get all interaction data for a system across all frames
    Returns aggregated interaction data with conservation scores
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id
        
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
                        raw_types = [t.strip() for t in row['Type of Interactions'].split(';') if t.strip()]
                        for raw_type in raw_types:
                            normalized_type = _normalize_interaction_type(raw_type)
                            if not normalized_type:
                                continue
                            interaction_map[key]['types'].add(normalized_type)
                            # Track which frames this type appears in
                            if normalized_type not in interaction_map[key]['typeFrames']:
                                interaction_map[key]['typeFrames'][normalized_type] = []
                            interaction_map[key]['typeFrames'][normalized_type].append(frame_num)
        
        # Convert to array with conservation scores
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
            
            # Convert typeFrames to a format the frontend can use
            typeFramesMap = {}
            for interaction_type in typesArray:
                if interaction_type in entry['typeFrames']:
                    typeFramesMap[interaction_type] = sorted(list(set(entry['typeFrames'][interaction_type])))
            
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
                'frames': sorted(list(frame_set)),  # Sorted list of frame numbers where interaction occurs
                'typeFrames': typeFramesMap  # Frames per interaction type
            })
        
        # Sort by conservation
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
        system_path = Path(data_folder) / 'systems' / system_id
        
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
        system_path = Path(data_folder) / 'systems' / system_id
        
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
        system_path = Path(data_folder) / 'systems' / system_id
        
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

def _get_interaction_csv_filename(interaction_type):
    """Map interaction type to CSV filename (matches actual CSV file naming)"""
    mapping = {
        'H-bond': 'H-bond',
        'H-bonds': 'H-bond',
        'Salt-bridge': 'Salt_bridge',
        'Salt-bridges': 'Salt_bridge',
        'π-π interactions': 'pi-pi',
        'pi-pi': 'pi-pi',
        'Cation-π interactions': 'Cation_pi',
        'Cation-π': 'Cation_pi',
        'Anion-π interactions': 'Anion_pi',
        'Anion-π': 'Anion_pi',
        'CH-O/N bonds': 'C-H_ON',
        'CH-O/N': 'C-H_ON',
        'CH-π interactions': 'C-H_pi',
        'CH-π': 'C-H_pi',
        'Halogen bonds': 'Halogen_bond',
        'Halogen bond': 'Halogen_bond',
        'Apolar vdW contacts': 'Apolar_vdw',
        'Apolar vdW': 'Apolar_vdw',
        'Polar vdW contacts': 'Polar_vdw',
        'Polar vdW': 'Polar_vdw',
        'Proximal contacts': 'Proximal',
        'Proximal contact': 'Proximal',
        'Clashes': 'Clash',
        'Clash': 'Clash',
        'Metal-mediated contacts': 'Metal_Mediated',
        'Metal mediated': 'Metal_Mediated',
        'O/N/SH-π interactions': 'N-S-O-H_pi',
        'lp-π interactions': 'Lone_pair_pi',
        'Lone pair-π': 'Lone_pair_pi',
        'Water mediated': 'Water_Mediated',
        'Water-mediated contacts': 'Water_Mediated',
        'S-S bond': 'SS_bond',
        'S / S-S bond': 'SS_bond',
        'Amino-π interactions': 'Amino_pi',
        'Polar-π (Amino-π)': 'Amino_pi'
    }
    return mapping.get(interaction_type, None)

@bp.route('/systems/<system_id>/atom-pairs', methods=['GET'])
def get_atom_pairs(system_id):
    """
    Get atom pair data for a specific residue pair across all frames
    Query params: resName1, resNum1, chain1, resName2, resNum2, chain2
    """
    from flask import request
    
    try:
        # Get query parameters
        res_name1 = request.args.get('resName1')
        res_num1 = request.args.get('resNum1')
        chain1 = request.args.get('chain1')
        res_name2 = request.args.get('resName2')
        res_num2 = request.args.get('resNum2')
        chain2 = request.args.get('chain2')
        
        if not all([res_name1, res_num1, chain1, res_name2, res_num2, chain2]):
            return jsonify({'error': 'Missing required parameters: resName1, resNum1, chain1, resName2, resNum2, chain2'}), 400
        
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders
        frame_folders = sorted(
            [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')],
            key=lambda f: int(f.name.split('_')[1]) if '_' in f.name else f.name
        )
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        total_frames = len(frame_folders)
        
        # First, get interaction types from final_file.csv to know which CSV files to check
        interaction_types = set()
        for frame_folder in frame_folders:
            csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_final_file.csv"
            if csv_file.exists():
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if (row.get('Res. Name 1') == res_name1 and 
                            row.get('Res. Number 1') == res_num1 and
                            row.get('Chain 1') == chain1 and
                            row.get('Res. Name 2') == res_name2 and
                            row.get('Res. Number 2') == res_num2 and
                            row.get('Chain 2') == chain2):
                            if row.get('Type of Interactions'):
                                raw_types = [t.strip() for t in row['Type of Interactions'].split(';') if t.strip()]
                                for raw_type in raw_types:
                                    normalized = _normalize_interaction_type(raw_type)
                                    if normalized:
                                        interaction_types.add(normalized)
        
        # Collect atom pair data from all relevant CSV files
        atom_pairs_by_frame = {}  # frame_num -> list of atom pair entries
        atom_pair_stats = {}  # atom_pair_key -> {frames: [], distances: [], count: 0, interactionType: ''}
        
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            atom_pairs_by_frame[frame_num] = []
            
            # Check each interaction type CSV file
            for interaction_type in interaction_types:
                csv_filename = _get_interaction_csv_filename(interaction_type)
                if not csv_filename:
                    continue
                
                csv_file = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_{csv_filename}.csv"
                if not csv_file.exists():
                    continue
                
                # Parse CSV
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Check if this row matches our residue pair
                        if (row.get('Res. Name 1') == res_name1 and 
                            row.get('Res. Number 1') == res_num1 and
                            row.get('Chain 1') == chain1 and
                            row.get('Res. Name 2') == res_name2 and
                            row.get('Res. Number 2') == res_num2 and
                            row.get('Chain 2') == chain2):
                            
                            atom1 = row.get('Atom 1', '').strip()
                            atom2 = row.get('Atom 2', '').strip()
                            
                            if atom1 and atom2:
                                atom_pair_key = f"{atom1}-{atom2}"
                                
                                # Get distance
                                distance_str = row.get('Distance (Å)', '').strip()
                                distance = None
                                if distance_str:
                                    # Remove asterisks and extract number
                                    distance_str = distance_str.replace('*', '').strip()
                                    try:
                                        distance = float(distance_str)
                                    except ValueError:
                                        pass
                                
                                # Get additional data (angle, etc.)
                                angle = None
                                if 'DHA Angle' in row:
                                    try:
                                        angle = float(row['DHA Angle'].strip())
                                    except (ValueError, AttributeError):
                                        pass
                                
                                atom_pair_entry = {
                                    'atom1': atom1,
                                    'atom2': atom2,
                                    'atomPair': atom_pair_key,
                                    'interactionType': interaction_type,
                                    'distance': distance,
                                    'angle': angle,
                                    'frame': frame_num
                                }
                                
                                atom_pairs_by_frame[frame_num].append(atom_pair_entry)
                                
                                # Update stats
                                if atom_pair_key not in atom_pair_stats:
                                    atom_pair_stats[atom_pair_key] = {
                                        'atom1': atom1,
                                        'atom2': atom2,
                                        'atomPair': atom_pair_key,
                                        'frames': [],
                                        'distances': [],
                                        'angles': [],
                                        'count': 0,
                                        'interactionTypes': set()
                                    }
                                
                                atom_pair_stats[atom_pair_key]['frames'].append(frame_num)
                                atom_pair_stats[atom_pair_key]['interactionTypes'].add(interaction_type)
                                atom_pair_stats[atom_pair_key]['count'] += 1
                                if distance is not None:
                                    atom_pair_stats[atom_pair_key]['distances'].append(distance)
                                if angle is not None:
                                    atom_pair_stats[atom_pair_key]['angles'].append(angle)
        
        # Calculate transitions between atom pairs
        transitions = []
        sorted_frames = sorted(atom_pairs_by_frame.keys())
        
        for i in range(len(sorted_frames) - 1):
            frame1 = sorted_frames[i]
            frame2 = sorted_frames[i + 1]
            
            pairs1 = set([entry['atomPair'] for entry in atom_pairs_by_frame[frame1]])
            pairs2 = set([entry['atomPair'] for entry in atom_pairs_by_frame[frame2]])
            
            # Find transitions (pairs that exist in frame1 and change in frame2)
            for pair1 in pairs1:
                if pair1 not in pairs2:
                    # This pair disappeared, find what replaced it
                    for pair2 in pairs2:
                        transitions.append({
                            'from': pair1,
                            'to': pair2,
                            'fromFrame': frame1,
                            'toFrame': frame2,
                            'type': 'transition'
                        })
        
        # Convert stats to list format
        atom_pair_list = []
        for key, stats in atom_pair_stats.items():
            frames_set = sorted(list(set(stats['frames'])))
            atom_pair_list.append({
                'atom1': stats['atom1'],
                'atom2': stats['atom2'],
                'atomPair': stats['atomPair'],
                'frames': frames_set,
                'frameCount': len(frames_set),
                'consistency': len(frames_set) / total_frames if total_frames > 0 else 0,
                'count': stats['count'],
                'interactionTypes': list(stats['interactionTypes']),
                'avgDistance': sum(stats['distances']) / len(stats['distances']) if stats['distances'] else None,
                'minDistance': min(stats['distances']) if stats['distances'] else None,
                'maxDistance': max(stats['distances']) if stats['distances'] else None,
                'avgAngle': sum(stats['angles']) / len(stats['angles']) if stats['angles'] else None
            })
        
        # Sort by conservation (most persistent first)
        atom_pair_list.sort(key=lambda x: x['consistency'], reverse=True)
        
        # Get all most common atom pairs (those with the highest consistency)
        most_common = []
        if atom_pair_list:
            max_consistency = atom_pair_list[0]['consistency']
            # Get all atom pairs that share the maximum consistency
            most_common = [pair for pair in atom_pair_list if pair['consistency'] == max_consistency]
        
        return jsonify({
            'residuePair': {
                'resName1': res_name1,
                'resNum1': int(res_num1),
                'chain1': chain1,
                'resName2': res_name2,
                'resNum2': int(res_num2),
                'chain2': chain2,
                'id1': f"{chain1}-{res_name1}{res_num1}",
                'id2': f"{chain2}-{res_name2}{res_num2}"
            },
            'totalFrames': total_frames,
            'atomPairs': atom_pair_list,
            'atomPairsByFrame': {str(k): v for k, v in atom_pairs_by_frame.items()},
            'transitions': transitions,
            'mostCommonAtomPairs': most_common,  # Changed to plural - now returns a list
            'interactionTypes': list(interaction_types)
        })
    
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@bp.route('/systems/<system_id>/interaction-distances', methods=['GET'])
def get_interaction_distances(system_id):
    """
    Get distance data for all interactions across all frames
    Returns a map: {pair_key: {frame: {type: distance}}}
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders
        frame_folders = sorted(
            [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')],
            key=lambda f: int(f.name.split('_')[1]) if '_' in f.name else f.name
        )
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        # Structure: {pair_key: {frame: {type: [distances]}}}
        distance_map = {}
        
        # Get all possible interaction type CSV filenames
        all_interaction_types = [
            'H-bond', 'Salt_bridge', 'pi-pi', 'Cation_pi', 'Anion_pi',
            'C-H_ON', 'C-H_pi', 'Halogen_bond', 'Apolar_vdw', 'Polar_vdw',
            'Proximal', 'Clash', 'Metal_Mediated', 'N-S-O-H_pi', 'Lone_pair_pi',
            'Water_Mediated', 'SS_bond', 'Amino_pi'
        ]
        
        # Map CSV filename back to normalized type name
        csv_to_type_map = {
            'H-bond': 'H-bond',
            'Salt_bridge': 'Salt-bridge',
            'pi-pi': 'π-π interactions',
            'Cation_pi': 'Cation-π interactions',
            'Anion_pi': 'Anion-π interactions',
            'C-H_ON': 'CH-O/N bonds',
            'C-H_pi': 'CH-π interactions',
            'Halogen_bond': 'Halogen bonds',
            'Apolar_vdw': 'Apolar vdW contacts',
            'Polar_vdw': 'Polar vdW contacts',
            'Proximal': 'Proximal contacts',
            'Clash': 'Clashes',
            'Metal_Mediated': 'Metal-mediated contacts',
            'N-S-O-H_pi': 'O/N/SH-π interactions',
            'Lone_pair_pi': 'lp-π interactions',
            'Water_Mediated': 'Water-mediated contacts',
            'SS_bond': 'S-S bond',
            'Amino_pi': 'Amino-π interactions'
        }
        
        # Scan all interaction type CSV files directly (more reliable than using final_file.csv)
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            
            for csv_filename in all_interaction_types:
                type_csv = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_{csv_filename}.csv"
                
                if not type_csv.exists():
                    continue
                
                normalized_type = csv_to_type_map.get(csv_filename)
                if not normalized_type:
                    continue
                
                # Parse the type-specific CSV to get distances
                try:
                    with open(type_csv, 'r', encoding='utf-8') as tf:
                        type_reader = csv.DictReader(tf)
                        for type_row in type_reader:
                            # Check if required fields exist
                            if not all(key in type_row for key in ['Res. Name 1', 'Res. Number 1', 'Chain 1', 
                                                                  'Res. Name 2', 'Res. Number 2', 'Chain 2']):
                                continue
                            
                            # Check if distance column exists
                            if 'Distance (Å)' not in type_row:
                                continue
                            
                            pair_key = f"{type_row['Chain 1']}-{type_row['Res. Name 1']}{type_row['Res. Number 1']}_{type_row['Chain 2']}-{type_row['Res. Name 2']}{type_row['Res. Number 2']}"
                            
                            # Get distance
                            distance_str = type_row.get('Distance (Å)', '').strip()
                            if distance_str:
                                # Remove asterisks and extract number
                                distance_str = distance_str.replace('*', '').strip()
                                try:
                                    distance = float(distance_str)
                                    
                                    if pair_key not in distance_map:
                                        distance_map[pair_key] = {}
                                    if frame_num not in distance_map[pair_key]:
                                        distance_map[pair_key][frame_num] = {}
                                    if normalized_type not in distance_map[pair_key][frame_num]:
                                        distance_map[pair_key][frame_num][normalized_type] = []
                                    
                                    distance_map[pair_key][frame_num][normalized_type].append(distance)
                                except ValueError:
                                    pass
                except Exception as e:
                    # Skip files that can't be read
                    continue
        
        # Convert to simpler structure: use minimum distance if multiple (closest interaction)
        simplified_map = {}
        for pair_key, frames in distance_map.items():
            simplified_map[pair_key] = {}
            for frame_num, types in frames.items():
                simplified_map[pair_key][frame_num] = {}
                for interaction_type, distances in types.items():
                    # Use the minimum distance (closest interaction) if multiple atom pairs exist
                    simplified_map[pair_key][frame_num][interaction_type] = min(distances) if distances else None
        
        return jsonify({
            'system': system_id,
            'distances': simplified_map
        })
    
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@bp.route('/systems/<system_id>/distance-distributions', methods=['GET'])
def get_distance_distributions(system_id):
    """
    Get distance distributions for residue pairs filtered by interaction types
    Query params: interaction_types (comma-separated list)
    Returns: {pairs: [{id, chain1, res1, chain2, res2, interaction_type, distances: []}]}
    """
    from flask import request
    
    try:
        # Get query parameters
        interaction_types_param = request.args.get('interaction_types', '')
        selected_types = [t.strip() for t in interaction_types_param.split(',') if t.strip()]
        
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id
        
        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        
        # Find all frame folders
        frame_folders = sorted(
            [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')],
            key=lambda f: int(f.name.split('_')[1]) if '_' in f.name else f.name
        )
        
        if not frame_folders:
            return jsonify({'error': 'No frames found for this system'}), 404
        
        total_frames = len(frame_folders)
        
        # Structure: {(pair_key, interaction_type): [distances]}
        pair_type_distances = {}
        pair_info = {}  # Store residue info for each pair
        
        # CSV filename mapping
        csv_to_type_map = {
            'H-bond': 'H-bond',
            'Salt_bridge': 'Salt-bridge',
            'pi-pi': 'π-π interactions',
            'Cation_pi': 'Cation-π interactions',
            'Anion_pi': 'Anion-π interactions',
            'C-H_ON': 'CH-O/N bonds',
            'C-H_pi': 'CH-π interactions',
            'Halogen_bond': 'Halogen bonds',
            'Apolar_vdw': 'Apolar vdW contacts',
            'Polar_vdw': 'Polar vdW contacts',
            'Proximal': 'Proximal contacts',
            'Clash': 'Clashes',
            'Metal_Mediated': 'Metal-mediated contacts',
            'N-S-O-H_pi': 'O/N/SH-π interactions',
            'Lone_pair_pi': 'lp-π interactions',
            'Water_Mediated': 'Water-mediated contacts',
            'SS_bond': 'S-S bond',
            'Amino_pi': 'Amino-π interactions'
        }
        
        # Filter CSV files to scan based on selected types
        csv_files_to_scan = []
        if selected_types:
            # Map selected types back to CSV filenames
            for csv_name, normalized_type in csv_to_type_map.items():
                if normalized_type in selected_types:
                    csv_files_to_scan.append((csv_name, normalized_type))
        else:
            # If no filter, scan all
            csv_files_to_scan = list(csv_to_type_map.items())
        
        # Scan all frames and collect distances
        for frame_folder in frame_folders:
            frame_num = int(frame_folder.name.split('_')[1])
            
            for csv_filename, normalized_type in csv_files_to_scan:
                type_csv = frame_folder / f"{frame_folder.name}.pd_h.pdb_A_B_{csv_filename}.csv"
                
                if not type_csv.exists():
                    continue
                
                # Parse the CSV file
                try:
                    with open(type_csv, 'r', encoding='utf-8') as tf:
                        type_reader = csv.DictReader(tf)
                        for row in type_reader:
                            # Check required fields
                            if not all(key in row for key in ['Res. Name 1', 'Res. Number 1', 'Chain 1', 
                                                              'Res. Name 2', 'Res. Number 2', 'Chain 2', 'Distance (Å)']):
                                continue
                            
                            # Extract distance
                            distance_str = row.get('Distance (Å)', '').strip()
                            if not distance_str:
                                continue
                            
                            # Remove asterisks and parse
                            distance_str = distance_str.replace('*', '').strip()
                            try:
                                distance = float(distance_str)
                            except ValueError:
                                continue
                            
                            # Create pair key
                            pair_key = f"{row['Chain 1']}:{row['Res. Name 1']}:{row['Res. Number 1']}-{row['Chain 2']}:{row['Res. Name 2']}:{row['Res. Number 2']}"
                            compound_key = (pair_key, normalized_type)
                            
                            # Store pair info
                            if pair_key not in pair_info:
                                pair_info[pair_key] = {
                                    'chain1': row['Chain 1'],
                                    'resName1': row['Res. Name 1'],
                                    'resNum1': int(row['Res. Number 1']),
                                    'chain2': row['Chain 2'],
                                    'resName2': row['Res. Name 2'],
                                    'resNum2': int(row['Res. Number 2'])
                                }
                            
                            # Store distance
                            if compound_key not in pair_type_distances:
                                pair_type_distances[compound_key] = []
                            pair_type_distances[compound_key].append(distance)
                
                except Exception as e:
                    continue
        
        # Format results
        pairs = []
        for (pair_key, interaction_type), distances in pair_type_distances.items():
            if pair_key in pair_info:
                info = pair_info[pair_key]
                pairs.append({
                    'id': pair_key,
                    'chain1': info['chain1'],
                    'resName1': info['resName1'],
                    'resNum1': info['resNum1'],
                    'chain2': info['chain2'],
                    'resName2': info['resName2'],
                    'resNum2': info['resNum2'],
                    'interactionType': interaction_type,
                    'distances': distances,
                    'frameCount': len(distances),
                    'consistency': len(distances) / total_frames if total_frames > 0 else 0,
                    'avgDistance': sum(distances) / len(distances) if distances else 0,
                    'minDistance': min(distances) if distances else 0,
                    'maxDistance': max(distances) if distances else 0
                })
        
        # Sort by consistency (most persistent first)
        pairs.sort(key=lambda x: x['consistency'], reverse=True)
        
        return jsonify({
            'system': system_id,
            'totalFrames': total_frames,
            'pairs': pairs
        })
    
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

