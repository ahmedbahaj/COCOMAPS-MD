"""
Shared constants for CLI — mirrors frontend/src/utils/constants.js and chartHelpers.js
"""

# ──────────────────────────────────────────────────────────────────────────────
# Interaction types — same order and keywords as frontend constants.js
# ──────────────────────────────────────────────────────────────────────────────
INTERACTION_TYPES = [
    {'id': 'pi-pi',      'label': 'π-π interactions',       'keywords': ['pi-pi', 'π-π'],                                     'trendLabel': 'π-π interactions'},
    {'id': 'amino-pi',   'label': 'Polar-π (Amino-π)',      'keywords': ['amino-pi', 'amino_pi', 'polar-π', 'polar-pi'],      'trendLabel': 'Amino-π interactions'},
    {'id': 'anion-pi',   'label': 'Anion-π interactions',    'keywords': ['anion-pi', 'anion_pi', 'anion-π'],                  'trendLabel': 'Anion-π interactions'},
    {'id': 'apolar-vdw', 'label': 'Apolar vdW contacts',    'keywords': ['apolar vdw', 'apolar_vdw'],                         'trendLabel': 'Apolar vdW contacts'},
    {'id': 'ch-on',      'label': 'CH-O/N bonds',           'keywords': ['ch-o', 'c-h_on', 'c-h on'],                         'trendLabel': 'CH-O/N bonds'},
    {'id': 'ch-pi',      'label': 'CH-π interactions',       'keywords': ['ch-pi', 'ch-π', 'c-h_pi'],                          'trendLabel': 'CH-π interactions'},
    {'id': 'cation-pi',  'label': 'Cation-π interactions',   'keywords': ['cation-pi', 'cation_pi', 'cation-π'],               'trendLabel': 'Cation-π interactions'},
    {'id': 'clash',      'label': 'Clashes',                 'keywords': ['clash'],                                             'trendLabel': 'Clashes'},
    {'id': 'h-bond',     'label': 'H-bonds',                 'keywords': ['h-bond', 'h-bond*', 'hydrogen bond'],                'trendLabel': 'H-bonds'},
    {'id': 'halogen',    'label': 'Halogen bonds',           'keywords': ['halogen'],                                           'trendLabel': 'Halogen bonds'},
    {'id': 'lone-pair-pi','label': 'lp-π interactions',      'keywords': ['lone_pair_pi', 'lone pair', 'lp-pi', 'lp-π'],       'trendLabel': 'Lone pair-π interactions'},
    {'id': 'metal',      'label': 'Metal-mediated contacts', 'keywords': ['metal mediated', 'metal_mediated', 'metal-mediated'],'trendLabel': 'Metal mediated'},
    {'id': 'ons-oh-pi',  'label': 'O/N/SH-π interactions',   'keywords': ['n-s-o-h', 'n-s-o-h_pi', 'o/n/sh'],                  'trendLabel': 'O/N/SH-π interactions'},
    {'id': 'polar-vdw',  'label': 'Polar vdW contacts',      'keywords': ['polar vdw', 'polar_vdw'],                            'trendLabel': 'Polar vdW contacts'},
    {'id': 'proximal',   'label': 'Proximal contacts',       'keywords': ['proximal'],                                          'trendLabel': 'Proximal contacts'},
    {'id': 'salt-bridge','label': 'Salt-bridges',             'keywords': ['salt-bridge', 'salt bridge'],                        'trendLabel': 'Salt-bridges'},
    {'id': 'ss-bond',    'label': 'S-S bonds',               'keywords': ['ss bond', 's-s bond', 'ss_bond'],                    'trendLabel': 'S-S bonds'},
    {'id': 'water',      'label': 'Water-mediated contacts',  'keywords': ['water mediated', 'water_mediated', 'water-mediated'],'trendLabel': 'Water mediated'},
]

# ──────────────────────────────────────────────────────────────────────────────
# Interaction color palette — same RGB values as chartHelpers.js
# ──────────────────────────────────────────────────────────────────────────────
INTERACTION_COLOR_RULES = [
    {'color': (47, 79, 79),    'keywords': ['π-π', 'pi-pi', 'pi pi']},
    {'color': (152, 251, 152), 'keywords': ['amino-pi', 'amino_pi', 'polar-π', 'polar-pi']},
    {'color': (255, 0, 255),   'keywords': ['anion-π', 'anion-pi', 'anion_pi']},
    {'color': (60, 95, 95),    'keywords': ['apolar vdw', 'apolar_vdw']},
    {'color': (173, 216, 230), 'keywords': ['ch-o', 'c-h_on', 'c-h on', 'ch-on']},
    {'color': (34, 139, 34),   'keywords': ['ch-π', 'ch-pi', 'c-h_pi']},
    {'color': (0, 255, 255),   'keywords': ['cation-π', 'cation-pi', 'cation_pi']},
    {'color': (139, 0, 0),     'keywords': ['clash']},
    {'color': (75, 0, 130),    'keywords': ['h-bond*', 'h-bond', 'hydrogen bond']},
    {'color': (85, 107, 47),   'keywords': ['halogen']},
    {'color': (70, 130, 180),  'keywords': ['lp-π', 'lp-pi', 'lone pair', 'lone_pair_pi']},
    {'color': (139, 69, 19),   'keywords': ['metal mediated', 'metal_mediated', 'metal-mediated']},
    {'color': (90, 75, 170),   'keywords': ['n-s-o-h', 'n-s-o-h_pi', 'o/n/sh']},
    {'color': (255, 0, 127),   'keywords': ['polar vdw', 'polar_vdw']},
    {'color': (54, 69, 79),    'keywords': ['proximal']},
    {'color': (128, 0, 128),   'keywords': ['salt-bridge', 'salt bridge']},
    {'color': (255, 103, 0),   'keywords': ['s-bond', 'ss bond', 's-s bond', 'ss_bond', 's-s']},
    {'color': (72, 61, 139),   'keywords': ['water', 'water mediated', 'water_mediated', 'water-mediated']},
]


def find_interaction_color(type_string: str) -> tuple:
    """Return the RGB tuple for a given interaction type string."""
    normalized = type_string.lower()
    for rule in INTERACTION_COLOR_RULES:
        if any(kw.lower() in normalized for kw in rule['keywords']):
            return rule['color']
    return (75, 0, 130)  # default indigo


def rgb_to_hex(rgb: tuple) -> str:
    """Convert (r, g, b) tuple to '#RRGGBB' string."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def get_interaction_color_hex(type_string: str) -> str:
    """Return the hex color string for a given interaction type."""
    return rgb_to_hex(find_interaction_color(type_string))


# ──────────────────────────────────────────────────────────────────────────────
# Default CoCoMaps parameters (same as create_input_jsons in engine.analyze_pdb)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_COCOMAPS_PARAMS = {
    'HBOND_DIST': 3.9,
    'HBOND_ANGLE': 90,
    'SBRIDGE_DIST': 4.5,
    'WBRIDGE_DIST': 3.9,
    'CH_ON_DIST': 3.6,
    'CH_ON_ANGLE': 110,
    'CUT_OFF': 5,
    'APOLAR_TOLERANCE': 0.5,
    'POLAR_TOLERANCE': 0.5,
    'PI_PI_DIST': 5.5,
    'PI_PI_THETA': 80,
    'PI_PI_GAMMA': 90,
    'ANION_PI_DIST': 5,
    'LONEPAIR_PI_DIST': 5,
    'AMINO_PI_DIST': 5,
    'CATION_PI_DIST': 5,
    'METAL_DIST': 3.2,
    'HALOGEN_THETA1': 165,
    'HALOGEN_THETA2': 120,
    'C_H_PI_DIST': 5.0,
    'C_H_PI_THETA1': 120,
    'C_H_PI_THETA2': 30,
    'NSOH_PI_DIST': 4.5,
    'NSOH_PI_THETA1': 120,
    'NSOH_PI_THETA2': 30,
}

# ──────────────────────────────────────────────────────────────────────────────
# Default chart options — single source of truth for chart generation defaults
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_CHART_OPTIONS = {
    'global': {
        'conservation_threshold': 0.5,
        'time_unit': None,
        'excluded_types': {'proximal'},
    },
    'conservation_matrix': {
        'enabled': True,
        'pair_threshold': 0.5,
        'type_threshold': 0.5,
        'atom_change_mode': 'previous',
    },
    'heatmap': {'enabled': True, 'show_labels': True},
    'trends': {'enabled': True, 'log_scale': False},
    'distribution': {'enabled': True, 'min_conservation': 50},
    'area': {'enabled': True, 'show_stats': True, 'show_percentages': False},
    'conserved_islands': {'enabled': True},
}

# ──────────────────────────────────────────────────────────────────────────────
# Trends CSV keys — same order as backend data.py TRENDS_KEYS
# ──────────────────────────────────────────────────────────────────────────────
TRENDS_KEYS = [
    'H-bonds', 'Salt-bridges', 'π-π interactions', 'Cation-π interactions',
    'Anion-π interactions', 'CH-O/N bonds', 'CH-π interactions', 'Halogen bonds',
    'Apolar vdW contacts', 'Polar vdW contacts', 'Proximal contacts', 'Clashes',
    'Water mediated', 'Metal mediated', 'S-S bonds', 'Amino-π interactions',
    'Lone pair-π interactions', 'O/N/SH-π interactions',
]
