"""
Routes for data retrieval
"""
from flask import Blueprint, jsonify, current_app, send_file
from pathlib import Path
import csv
import json
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

        # Web pipeline may write frame_1_viewer.pdb (full frame 1, minus non-interacting waters/metals)
        if frame_num == 1:
            viewer_pdb = frame_folder / 'frame_1_viewer.pdb'
            if viewer_pdb.is_file():
                pdb_file = viewer_pdb
            else:
                pdb_file = frame_folder / f'frame_{frame_num}.pdb'
                if not pdb_file.exists():
                    pdb_file = frame_folder / f'frame_{frame_num}.pd_h.pdb'
        else:
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


def _canonical_pair_key(res_name1, res_num1, chain1, res_name2, res_num2, chain2):
    """Stable key for a residue pair (order-independent)."""
    id1 = _format_residue_id(res_name1, str(res_num1), chain1)
    id2 = _format_residue_id(res_name2, str(res_num2), chain2)
    return tuple(sorted([id1, id2]))


def _read_atom_pairs_grouped(system_path, requested_canonical_keys):
    """
    Read _atom_pairs.csv once and return dict: canonical_pair_key -> list of row dicts.
    Only includes rows for pairs in requested_canonical_keys (or all if set is empty).
    """
    grouped = {}
    path = system_path / '_atom_pairs.csv'
    if not path.exists():
        return grouped
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            r1, n1, c1 = row.get('resName1'), row.get('resNum1'), row.get('chain1')
            r2, n2, c2 = row.get('resName2'), row.get('resNum2'), row.get('chain2')
            if not all([r1, n1, c1, r2, n2, c2]):
                continue
            key = _canonical_pair_key(r1, n1, c1, r2, n2, c2)
            if requested_canonical_keys and key not in requested_canonical_keys:
                continue
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(row)
    return grouped


def _build_atom_pairs_response_from_rows(rows, res_name1, res_num1, chain1,
                                         res_name2, res_num2, chain2, total_frames):
    """Build the same response structure from a list of CSV row dicts (one residue pair)."""
    atom_pairs_by_frame = {}
    atom_pair_stats = {}
    interaction_types = set()

    for row in rows:
        frame_num = int(row['frame'])
        interaction_type = row.get('interactionType', '')
        atom1 = row.get('atom1', '').strip()
        atom2 = row.get('atom2', '').strip()
        if not atom1 or not atom2:
            continue

        atom_pair_key = f"{atom1}-{atom2}"
        interaction_types.add(interaction_type)

        try:
            dist = float(row['distance']) if row.get('distance') else None
        except (ValueError, TypeError):
            dist = None
        try:
            ang = float(row['angle']) if row.get('angle') else None
        except (ValueError, TypeError):
            ang = None

        if frame_num not in atom_pairs_by_frame:
            atom_pairs_by_frame[frame_num] = []
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


def _get_atom_pairs_response_from_csv(system_path, res_name1, res_num1, chain1,
                                       res_name2, res_num2, chain2, total_frames):
    """Build atom-pairs response from _atom_pairs.csv filtered by residue pair (single pair, single read)."""
    key = _canonical_pair_key(res_name1, res_num1, chain1, res_name2, res_num2, chain2)
    grouped = _read_atom_pairs_grouped(system_path, {key})
    rows = grouped.get(key, [])
    return _build_atom_pairs_response_from_rows(
        rows, res_name1, res_num1, chain1, res_name2, res_num2, chain2, total_frames
    )


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


@bp.route('/systems/<system_id>/atom-pairs/batch', methods=['POST'])
def get_atom_pairs_batch(system_id):
    """
    Get atom pair data for multiple residue pairs at once.
    POST body: { "pairs": [ { "resName1", "resNum1", "chain1", "resName2", "resNum2", "chain2" }, ... ] }
    Returns: { "pairKey1": { atomPairs, atomPairsByFrame, ... }, "pairKey2": {...}, ... }
    Requires _atom_pairs.csv and _metadata.json. Reads CSV once for all requested pairs.
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

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        total_frames = metadata.get('totalFrames', 0)
        if total_frames <= 0:
            return jsonify({'error': 'Invalid totalFrames in _metadata.json.'}), 404

        requested_keys = set()
        valid_pairs = []
        for pair in pairs:
            r1, n1, c1 = pair.get('resName1'), str(pair.get('resNum1')), pair.get('chain1')
            r2, n2, c2 = pair.get('resName2'), str(pair.get('resNum2')), pair.get('chain2')
            if not all([r1, n1, c1, r2, n2, c2]):
                continue
            requested_keys.add(_canonical_pair_key(r1, n1, c1, r2, n2, c2))
            valid_pairs.append((r1, n1, c1, r2, n2, c2))

        grouped = _read_atom_pairs_grouped(system_path, requested_keys)

        result = {}
        for (r1, n1, c1, r2, n2, c2) in valid_pairs:
            pair_key = f"{c1}-{r1}{n1}_{c2}-{r2}{n2}"
            canonical = _canonical_pair_key(r1, n1, c1, r2, n2, c2)
            rows = grouped.get(canonical, [])
            full = _build_atom_pairs_response_from_rows(rows, r1, n1, c1, r2, n2, c2, total_frames)
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
    Get distance data for all interactions across all frames.
    Requires _atom_pairs.csv. Returns {pair_key: {frame: {type: distance}}}.
    """
    try:
        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404

        atom_pairs_csv = system_path / '_atom_pairs.csv'
        if not atom_pairs_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _atom_pairs.csv.'}), 404

        # Structure: {pair_key: {frame: {type: [distances]}}}
        distance_map = {}
        with open(atom_pairs_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                res_id1 = _format_residue_id(row['resName1'], row['resNum1'], row['chain1'])
                res_id2 = _format_residue_id(row['resName2'], row['resNum2'], row['chain2'])
                pair_key = _format_pair_key(res_id1, res_id2)
                frame_num = int(row['frame'])
                interaction_type = row.get('interactionType', '').strip()
                if not interaction_type:
                    continue
                try:
                    dist = float(row['distance']) if row.get('distance') else None
                except (ValueError, TypeError):
                    dist = None
                if dist is None:
                    continue
                if pair_key not in distance_map:
                    distance_map[pair_key] = {}
                if frame_num not in distance_map[pair_key]:
                    distance_map[pair_key][frame_num] = {}
                if interaction_type not in distance_map[pair_key][frame_num]:
                    distance_map[pair_key][frame_num][interaction_type] = []
                distance_map[pair_key][frame_num][interaction_type].append(dist)

        simplified_map = {}
        for pair_key, frames in distance_map.items():
            simplified_map[pair_key] = {}
            for frame_num, types in frames.items():
                simplified_map[pair_key][frame_num] = {}
                for itype, distances in types.items():
                    simplified_map[pair_key][frame_num][itype] = min(distances) if distances else None

        return jsonify({'system': system_id, 'distances': simplified_map})

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@bp.route('/systems/<system_id>/distance-distributions', methods=['GET'])
def get_distance_distributions(system_id):
    """
    Get distance distributions for residue pairs filtered by interaction types.
    Requires _atom_pairs.csv and _metadata.json.
    Query params: interaction_types (comma-separated list).
    Returns: {pairs: [...], totalFrames}.
    """
    from flask import request

    try:
        interaction_types_param = request.args.get('interaction_types', '')
        selected_types = [t.strip() for t in interaction_types_param.split(',') if t.strip()]

        data_folder = current_app.config['DATA_FOLDER']
        system_path = Path(data_folder) / 'systems' / system_id

        if not system_path.exists():
            return jsonify({'error': 'System not found'}), 404

        atom_pairs_csv = system_path / '_atom_pairs.csv'
        metadata_path = system_path / '_metadata.json'
        if not atom_pairs_csv.exists():
            return jsonify({'error': 'Aggregated data not found. Run the pipeline to generate _atom_pairs.csv.'}), 404

        total_frames = 0
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as mf:
                    meta = json.load(mf)
                    total_frames = int(meta.get('totalFrames', 0))
            except (json.JSONDecodeError, TypeError):
                pass

        pair_type_distances = {}
        pair_info = {}

        with open(atom_pairs_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                itype = row.get('interactionType', '').strip()
                if not itype:
                    continue
                if selected_types and itype not in selected_types:
                    continue
                try:
                    dist = float(row['distance']) if row.get('distance') else None
                except (ValueError, TypeError):
                    continue
                if dist is None:
                    continue

                res_id1 = _format_residue_id(row['resName1'], row['resNum1'], row['chain1'])
                res_id2 = _format_residue_id(row['resName2'], row['resNum2'], row['chain2'])
                pair_key = _format_pair_key(res_id1, res_id2)
                compound_key = (pair_key, itype)

                if pair_key not in pair_info:
                    pair_info[pair_key] = {
                        'chain1': row['chain1'],
                        'resName1': row['resName1'],
                        'resNum1': int(row['resNum1']),
                        'chain2': row['chain2'],
                        'resName2': row['resName2'],
                        'resNum2': int(row['resNum2']),
                        'id1': res_id1,
                        'id2': res_id2
                    }
                if compound_key not in pair_type_distances:
                    pair_type_distances[compound_key] = {'distances': [], 'frames': set()}
                pair_type_distances[compound_key]['distances'].append(dist)
                pair_type_distances[compound_key]['frames'].add(int(row['frame']))

        pairs = []
        for (pair_key, interaction_type), data in pair_type_distances.items():
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
                'frameCount': len(unique_frames),
                'consistency': len(unique_frames) / total_frames if total_frames > 0 else 0,
                'totalMeasurements': len(distances),
                'avgDistance': sum(distances) / len(distances) if distances else 0,
                'minDistance': min(distances) if distances else 0,
                'maxDistance': max(distances) if distances else 0,
                'id1': info.get('id1'),
                'id2': info.get('id2')
            })

        pairs.sort(key=lambda x: x['consistency'], reverse=True)

        return jsonify({'system': system_id, 'totalFrames': total_frames, 'pairs': pairs})

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500
