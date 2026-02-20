"""
Routes for data retrieval
"""
from flask import Blueprint, jsonify, current_app, send_file
from pathlib import Path
import csv
import os

bp = Blueprint('data', __name__)


def _get_chain_pattern(frame_folder):
    """
    Detect the chain pattern (e.g., 'A_B', 'A_C') from CSV files in frame folder.
    Returns the pattern found or 'A_B' as default fallback.
    """
    import re
    # Look for files like frame_1.pdb_A_C_final_file.csv or frame_1.pd_h.pdb_A_B_final_file.csv
    pattern = re.compile(r'\.pd[b_h\.]*_([A-Z])_([A-Z])_final_file\.csv$')
    for f in frame_folder.iterdir():
        if f.is_file():
            match = pattern.search(f.name)
            if match:
                return f"{match.group(1)}_{match.group(2)}"
    return "A_B"  # fallback default


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


def _format_residue_id(res_name, res_num, chain):
    """Return residue identifier in RES123_CHAIN format."""
    if res_name is None or res_num is None or chain is None:
        return ''
    res_str = str(res_name).strip()
    chain_str = str(chain).strip()
    try:
        res_num_clean = int(str(res_num).strip())
    except (TypeError, ValueError):
        res_num_clean = str(res_num).strip()
    return f"{res_str}{res_num_clean}_{chain_str}"


def _format_pair_key(res_id1, res_id2):
    """Stable residue pair key using a separator unlikely to appear in IDs."""
    return f"{res_id1}__{res_id2}"


@bp.route('/systems/<system_id>/conserved-islands', methods=['GET'])
def get_conserved_islands(system_id):
    """
    Get conserved island data for a system.
    Returns JSON from _conserved_islands.json if it exists.
    """
    import json
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id
        islands_file = system_path / '_conserved_islands.json'

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        if not islands_file.exists():
            return jsonify({
                'system': system_id,
                'islands': [],
                'message': 'No conserved islands data. Run the pipeline or conserved_islands.py to generate.'
            })

        with open(islands_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return jsonify({
            'system': system_id,
            'islands': data.get('islands', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/systems/<system_id>/frame/<int:frame_num>/pdb', methods=['GET'])
def get_frame_pdb(system_id, frame_num):
    """
    Serve the PDB file for a given frame.
    Used by Mol* viewer to display the first-frame structure.
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id
        frame_folder = system_path / f'frame_{frame_num}'

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404
        if not frame_folder.exists() or not frame_folder.is_dir():
            return jsonify({'error': f'Frame {frame_num} not found'}), 404

        # Prefer frame_N.pdb, fallback to frame_N.pd_h.pdb
        pdb_file = frame_folder / f'frame_{frame_num}.pdb'
        if not pdb_file.exists():
            pdb_file = frame_folder / f'frame_{frame_num}.pd_h.pdb'
        if not pdb_file.exists():
            return jsonify({'error': f'PDB file not found for frame {frame_num}'}), 404

        return send_file(
            pdb_file,
            mimetype='chemical/x-pdb',
            as_attachment=False,
            download_name=f'{system_id}_frame_{frame_num}.pdb'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _get_interactions_from_csv(system_path, total_frames):
    """Read _interactions.csv and build the interactions response payload."""
    interaction_map = {}
    with open(system_path / '_interactions.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            res_id1 = _format_residue_id(row['resName1'], row['resNum1'], row['chain1'])
            res_id2 = _format_residue_id(row['resName2'], row['resNum2'], row['chain2'])
            key = _format_pair_key(res_id1, res_id2)
            frame_num = int(row['frame'])

            if key not in interaction_map:
                interaction_map[key] = {
                    'resName1': row['resName1'],
                    'resNum1': int(row['resNum1']),
                    'chain1': row['chain1'],
                    'resName2': row['resName2'],
                    'resNum2': int(row['resNum2']),
                    'chain2': row['chain2'],
                    'frames': [],
                    'types': set(),
                    'typeFrames': {}
                }

            interaction_map[key]['frames'].append(frame_num)
            for t in (row.get('types') or '').split(';'):
                t = t.strip()
                if t:
                    interaction_map[key]['types'].add(t)
                    if t not in interaction_map[key]['typeFrames']:
                        interaction_map[key]['typeFrames'][t] = []
                    interaction_map[key]['typeFrames'][t].append(frame_num)

    interactions = []
    for key, entry in interaction_map.items():
        frame_set = set(entry['frames'])
        typesArray = list(entry['types'])
        typePersistence = {
            t: len(set(entry['typeFrames'].get(t, []))) / total_frames
            for t in typesArray
        }
        typeFramesMap = {
            t: sorted(list(set(entry['typeFrames'].get(t, []))))
            for t in typesArray
        }
        interactions.append({
            'resName1': entry['resName1'],
            'resNum1': entry['resNum1'],
            'chain1': entry['chain1'],
            'id1': _format_residue_id(entry['resName1'], entry['resNum1'], entry['chain1']),
            'resName2': entry['resName2'],
            'resNum2': entry['resNum2'],
            'chain2': entry['chain2'],
            'id2': _format_residue_id(entry['resName2'], entry['resNum2'], entry['chain2']),
            'frameCount': len(frame_set),
            'consistency': len(frame_set) / total_frames,
            'typesArray': typesArray,
            'typePersistence': typePersistence,
            'frames': sorted(list(frame_set)),
            'typeFrames': typeFramesMap
        })
    interactions.sort(key=lambda x: x['consistency'], reverse=True)
    return interactions


@bp.route('/systems/<system_id>/interactions', methods=['GET'])
def get_interactions(system_id):
    """
    Get all interaction data for a system across all frames.
    Requires _interactions.csv and _metadata.json (no fallback).
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404

        interactions_csv = system_path / '_interactions.csv'
        metadata_file = system_path / '_metadata.json'
        if not interactions_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _interactions.csv.'}), 404
        if not metadata_file.exists():
            return jsonify({'error': 'Metadata not found. Run the pipeline to generate _metadata.json.'}), 404

        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        total_frames = metadata.get('totalFrames', 0)
        if total_frames <= 0:
            return jsonify({'error': 'Invalid totalFrames in _metadata.json.'}), 404

        interactions = _get_interactions_from_csv(system_path, total_frames)
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
    Get area data (BSA) for a system across all frames.
    Requires _area.csv (no fallback).
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404

        area_csv = system_path / '_area.csv'
        if not area_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _area.csv.'}), 404

        frames_data = []
        with open(area_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                frames_data.append({
                    'frame': int(row['frame']),
                    'totalBSA': float(row.get('totalBSA', 0)),
                    'polarBSA': float(row.get('polarBSA', 0)),
                    'nonPolarBSA': float(row.get('nonPolarBSA', 0)),
                    'totalPercent': float(row.get('totalPercent', 0)),
                    'polarPercent': float(row.get('polarPercent', 0)),
                    'nonPolarPercent': float(row.get('nonPolarPercent', 0))
                })
        return jsonify({'system': system_id, 'frames': frames_data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

TRENDS_KEYS = [
    'H-bonds', 'Salt-bridges', 'π-π interactions', 'Cation-π interactions',
    'Anion-π interactions', 'CH-O/N bonds', 'CH-π interactions', 'Halogen bonds',
    'Apolar vdW contacts', 'Polar vdW contacts', 'Proximal contacts', 'Clashes',
    'Water mediated', 'Metal mediated', 'S-S bonds', 'Amino-π interactions',
    'Lone pair-π interactions', 'O/N/SH-π interactions'
]


@bp.route('/systems/<system_id>/trends', methods=['GET'])
def get_interaction_trends(system_id):
    """
    Get interaction type trends across frames.
    Requires _trends.csv (no fallback).
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404

        trends_csv = system_path / '_trends.csv'
        if not trends_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _trends.csv.'}), 404

        rows = []
        with open(trends_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        if not rows:
            return jsonify({'error': '_trends.csv is empty.'}), 404

        rows.sort(key=lambda r: int(r.get('frame', 0)))
        frame_numbers_with_data = [int(r['frame']) for r in rows]
        trends = {k: [] for k in TRENDS_KEYS}
        for row in rows:
            for k in TRENDS_KEYS:
                try:
                    trends[k].append(int(row.get(k, 0)))
                except (TypeError, ValueError):
                    trends[k].append(0)
        return jsonify({
            'system': system_id,
            'frameNumbers': frame_numbers_with_data,
            'trends': trends
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

def _get_atom_pairs_response_from_csv(system_path, res_name1, res_num1, chain1,
                                       res_name2, res_num2, chain2, total_frames):
    """Build atom-pairs response from _atom_pairs.csv filtered by residue pair."""
    res_num1_str = str(res_num1)
    res_num2_str = str(res_num2)
    atom_pairs_by_frame = {}
    atom_pair_stats = {}
    interaction_types = set()

    with open(system_path / '_atom_pairs.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            m1 = (row.get('resName1') == res_name1 and row.get('resNum1') == res_num1_str and
                  row.get('chain1') == chain1 and row.get('resName2') == res_name2 and
                  row.get('resNum2') == res_num2_str and row.get('chain2') == chain2)
            m2 = (row.get('resName1') == res_name2 and row.get('resNum1') == res_num2_str and
                  row.get('chain1') == chain2 and row.get('resName2') == res_name1 and
                  row.get('resNum2') == res_num1_str and row.get('chain2') == chain1)
            if not (m1 or m2):
                continue

            frame_num = int(row['frame'])
            interaction_type = row.get('interactionType', '')
            atom1 = row.get('atom1', '').strip()
            atom2 = row.get('atom2', '').strip()
            if not atom1 or not atom2:
                continue

            atom_pair_key = f"{atom1}-{atom2}"
            interaction_types.add(interaction_type)

            if frame_num not in atom_pairs_by_frame:
                atom_pairs_by_frame[frame_num] = []
            try:
                dist = float(row['distance']) if row.get('distance') else None
            except (ValueError, TypeError):
                dist = None
            try:
                ang = float(row['angle']) if row.get('angle') else None
            except (ValueError, TypeError):
                ang = None

            atom_pairs_by_frame[frame_num].append({
                'atom1': atom1, 'atom2': atom2, 'atomPair': atom_pair_key,
                'interactionType': interaction_type, 'distance': dist, 'angle': ang, 'frame': frame_num
            })

            if atom_pair_key not in atom_pair_stats:
                atom_pair_stats[atom_pair_key] = {
                    'atom1': atom1, 'atom2': atom2, 'atomPair': atom_pair_key,
                    'frames': [], 'distances': [], 'angles': [], 'count': 0, 'interactionTypes': set()
                }
            atom_pair_stats[atom_pair_key]['frames'].append(frame_num)
            atom_pair_stats[atom_pair_key]['interactionTypes'].add(interaction_type)
            atom_pair_stats[atom_pair_key]['count'] += 1
            if dist is not None:
                atom_pair_stats[atom_pair_key]['distances'].append(dist)
            if ang is not None:
                atom_pair_stats[atom_pair_key]['angles'].append(ang)

    # Transitions
    transitions = []
    sorted_frames = sorted(atom_pairs_by_frame.keys())
    for i in range(len(sorted_frames) - 1):
        f1, f2 = sorted_frames[i], sorted_frames[i + 1]
        pairs1 = set(e['atomPair'] for e in atom_pairs_by_frame[f1])
        pairs2 = set(e['atomPair'] for e in atom_pairs_by_frame[f2])
        for p1 in pairs1:
            if p1 not in pairs2:
                for p2 in pairs2:
                    transitions.append({'from': p1, 'to': p2, 'fromFrame': f1, 'toFrame': f2, 'type': 'transition'})

    # atom_pair_list
    atom_pair_list = []
    for stats in atom_pair_stats.values():
        frames_set = sorted(set(stats['frames']))
        atom_pair_list.append({
            'atom1': stats['atom1'], 'atom2': stats['atom2'], 'atomPair': stats['atomPair'],
            'frames': frames_set, 'frameCount': len(frames_set),
            'consistency': len(frames_set) / total_frames if total_frames > 0 else 0,
            'count': stats['count'], 'interactionTypes': list(stats['interactionTypes']),
            'avgDistance': sum(stats['distances']) / len(stats['distances']) if stats['distances'] else None,
            'minDistance': min(stats['distances']) if stats['distances'] else None,
            'maxDistance': max(stats['distances']) if stats['distances'] else None,
            'avgAngle': sum(stats['angles']) / len(stats['angles']) if stats['angles'] else None
        })
    atom_pair_list.sort(key=lambda x: x['consistency'], reverse=True)

    most_common = []
    if atom_pair_list and atom_pair_list[0]['consistency'] > 0:
        max_c = atom_pair_list[0]['consistency']
        most_common = [p for p in atom_pair_list if p['consistency'] == max_c]

    return {
        'residuePair': {
            'resName1': res_name1, 'resNum1': int(res_num1), 'chain1': chain1,
            'resName2': res_name2, 'resNum2': int(res_num2), 'chain2': chain2,
            'id1': _format_residue_id(res_name1, res_num1, chain1),
            'id2': _format_residue_id(res_name2, res_num2, chain2)
        },
        'totalFrames': total_frames,
        'atomPairs': atom_pair_list,
        'atomPairsByFrame': {str(k): v for k, v in atom_pairs_by_frame.items()},
        'transitions': transitions,
        'mostCommonAtomPairs': most_common,
        'interactionTypes': list(interaction_types)
    }


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
    Get atom pair data for a specific residue pair across all frames.
    Query params: resName1, resNum1, chain1, resName2, resNum2, chain2
    Requires _atom_pairs.csv and _metadata.json (no fallback).
    """
    from flask import request

    try:
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

        atom_pairs_csv = system_path / '_atom_pairs.csv'
        metadata_file = system_path / '_metadata.json'
        if not atom_pairs_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _atom_pairs.csv.'}), 404
        if not metadata_file.exists():
            return jsonify({'error': 'Metadata not found. Run the pipeline to generate _metadata.json.'}), 404

        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        total_frames = metadata.get('totalFrames', 0)
        if total_frames <= 0:
            return jsonify({'error': 'Invalid totalFrames in _metadata.json.'}), 404

        resp = _get_atom_pairs_response_from_csv(
            system_path, res_name1, res_num1, chain1, res_name2, res_num2, chain2, total_frames
        )
        return jsonify(resp)

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


# Fallback logic removed - all data endpoints now require aggregated CSVs


@bp.route('/systems/<system_id>/atom-pairs/batch', methods=['POST'])
def get_atom_pairs_batch(system_id):
    """
    Get atom pair data for multiple residue pairs at once.
    POST body: { "pairs": [ { "resName1", "resNum1", "chain1", "resName2", "resNum2", "chain2" }, ... ] }
    Returns: { "pairKey1": { atomPairs, atomPairsByFrame, ... }, "pairKey2": {...}, ... }
    Requires _atom_pairs.csv and _metadata.json (no fallback).
    """
    from flask import request

    try:
        data = request.get_json()
        if not data or 'pairs' not in data:
            return jsonify({'error': 'Missing pairs array in request body'}), 400

        pairs = data['pairs']
        if not pairs or len(pairs) == 0:
            return jsonify({}), 200

        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404

        atom_pairs_csv = system_path / '_atom_pairs.csv'
        metadata_file = system_path / '_metadata.json'
        if not atom_pairs_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _atom_pairs.csv.'}), 404
        if not metadata_file.exists():
            return jsonify({'error': 'Metadata not found. Run the pipeline to generate _metadata.json.'}), 404

        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        total_frames = metadata.get('totalFrames', 0)
        if total_frames <= 0:
            return jsonify({'error': 'Invalid totalFrames in _metadata.json.'}), 404

        result = {}
        for pair in pairs:
            r1, n1, c1 = pair.get('resName1'), str(pair.get('resNum1')), pair.get('chain1')
            r2, n2, c2 = pair.get('resName2'), str(pair.get('resNum2')), pair.get('chain2')
            if not all([r1, n1, c1, r2, n2, c2]):
                continue
            pair_key = f"{c1}-{r1}{n1}_{c2}-{r2}{n2}"
            full = _get_atom_pairs_response_from_csv(system_path, r1, n1, c1, r2, n2, c2, total_frames)
            result[pair_key] = {
                'residuePair': full['residuePair'],
                'totalFrames': full['totalFrames'],
                'atomPairs': full['atomPairs'],
                'atomPairsByFrame': full['atomPairsByFrame'],
                'interactionTypes': full['interactionTypes']
            }
        return jsonify(result)

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
                # Detect chain pattern dynamically (e.g., A_B, A_C, etc.)
                chain_pattern = _get_chain_pattern(frame_folder)
                # Try both naming patterns: with Reduce (.pd_h.pdb) and without Reduce (.pdb)
                type_csv = frame_folder / f"{frame_folder.name}.pd_h.pdb_{chain_pattern}_{csv_filename}.csv"
                if not type_csv.exists():
                    type_csv = frame_folder / f"{frame_folder.name}.pdb_{chain_pattern}_{csv_filename}.csv"
                
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
                            
                            res_id1 = _format_residue_id(type_row['Res. Name 1'], type_row['Res. Number 1'], type_row['Chain 1'])
                            res_id2 = _format_residue_id(type_row['Res. Name 2'], type_row['Res. Number 2'], type_row['Chain 2'])
                            pair_key = _format_pair_key(res_id1, res_id2)
                            
                            # Get distance - handle different CSV formats
                            distance = None
                            
                            # Standard format: try multiple possible distance column names
                            distance_str = None
                            for dist_col in ['Distance (Å)', 'Distance', 'Distance(Å)', 'Dist (Å)', 'Dist', 'distance', 'Centroid Distance', 'Centroid Distance (Å)', 'Ring Distance', 'Ring Distance (Å)']:
                                if dist_col in type_row and type_row[dist_col]:
                                    distance_str = type_row[dist_col].strip()
                                    break
                            
                            if distance_str:
                                distance_str = distance_str.replace('*', '').strip()
                                try:
                                    distance = float(distance_str)
                                except ValueError:
                                    pass
                            
                            # Water-mediated format: has Distance from Res 1 and Distance from Res 2
                            # Sum both distances (total path through water)
                            elif 'Distance from Res 1' in type_row and 'Distance from Res 2' in type_row:
                                try:
                                    dist1_str = type_row.get('Distance from Res 1', '').strip()
                                    dist2_str = type_row.get('Distance from Res 2', '').strip()
                                    if dist1_str and dist2_str:
                                        dist1 = float(dist1_str.replace('*', '').strip())
                                        dist2 = float(dist2_str.replace('*', '').strip())
                                        distance = dist1 + dist2  # Total path through water
                                except ValueError:
                                    pass
                            
                            if distance is not None:
                                try:
                                    
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
        
        # Structure: {(pair_key, interaction_type): {'distances': [], 'frames': set()}}
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
                # Detect chain pattern dynamically (e.g., A_B, A_C, etc.)
                chain_pattern = _get_chain_pattern(frame_folder)
                # Try both naming patterns: with Reduce (.pd_h.pdb) and without Reduce (.pdb)
                type_csv = frame_folder / f"{frame_folder.name}.pd_h.pdb_{chain_pattern}_{csv_filename}.csv"
                if not type_csv.exists():
                    type_csv = frame_folder / f"{frame_folder.name}.pdb_{chain_pattern}_{csv_filename}.csv"
                
                if not type_csv.exists():
                    continue
                
                # Parse the CSV file
                try:
                    with open(type_csv, 'r', encoding='utf-8') as tf:
                        type_reader = csv.DictReader(tf)
                        for row in type_reader:
                            # Check required fields (excluding distance for now)
                            if not all(key in row for key in ['Res. Name 1', 'Res. Number 1', 'Chain 1', 
                                                              'Res. Name 2', 'Res. Number 2', 'Chain 2']):
                                continue
                            
                            # Try multiple possible distance column names
                            distance_str = None
                            for dist_col in ['Distance (Å)', 'Distance', 'Distance(Å)', 'Dist (Å)', 'Dist', 'distance', 'Centroid Distance', 'Centroid Distance (Å)', 'Ring Distance', 'Ring Distance (Å)']:
                                if dist_col in row and row[dist_col]:
                                    distance_str = row[dist_col].strip()
                                    break
                            
                            if not distance_str:
                                continue
                            
                            # Remove asterisks and parse
                            distance_str = distance_str.replace('*', '').strip()
                            try:
                                distance = float(distance_str)
                            except ValueError:
                                continue
                            
                            # Create pair key in unified residue format
                            res_id1 = _format_residue_id(row['Res. Name 1'], row['Res. Number 1'], row['Chain 1'])
                            res_id2 = _format_residue_id(row['Res. Name 2'], row['Res. Number 2'], row['Chain 2'])
                            pair_key = _format_pair_key(res_id1, res_id2)
                            compound_key = (pair_key, normalized_type)
                            
                            # Store pair info
                            if pair_key not in pair_info:
                                pair_info[pair_key] = {
                                    'chain1': row['Chain 1'],
                                    'resName1': row['Res. Name 1'],
                                    'resNum1': int(row['Res. Number 1']),
                                    'chain2': row['Chain 2'],
                                    'resName2': row['Res. Name 2'],
                                    'resNum2': int(row['Res. Number 2']),
                                    'id1': res_id1,
                                    'id2': res_id2
                                }
                            
                            # Store distance and track frame
                            if compound_key not in pair_type_distances:
                                pair_type_distances[compound_key] = {
                                    'distances': [],
                                    'frames': set()
                                }
                            pair_type_distances[compound_key]['distances'].append(distance)
                            pair_type_distances[compound_key]['frames'].add(frame_num)
                
                except Exception as e:
                    continue
        
        # Format results
        pairs = []
        for (pair_key, interaction_type), data in pair_type_distances.items():
            if pair_key in pair_info:
                info = pair_info[pair_key]
                distances = data['distances']
                unique_frames = data['frames']
                
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
                    'frameCount': len(unique_frames),  # Count unique frames, not total measurements
                    'consistency': len(unique_frames) / total_frames if total_frames > 0 else 0,  # Fixed: unique frames
                    'totalMeasurements': len(distances),  # Total distance measurements (can be > frames)
                    'avgDistance': sum(distances) / len(distances) if distances else 0,
                    'minDistance': min(distances) if distances else 0,
                    'maxDistance': max(distances) if distances else 0,
                    'id1': info.get('id1'),
                    'id2': info.get('id2')
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
