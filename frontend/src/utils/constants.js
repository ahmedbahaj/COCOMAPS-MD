/**
 * Interaction filters backed by trajectory outputs
 */
export const INTERACTION_TYPES = [
  { id: 'pi-pi', label: 'π-π interactions', keywords: ['pi-pi', 'π-π'] },
  { id: 'amino-pi', label: 'Polar-π (Amino-π)', keywords: ['amino-pi', 'amino_pi', 'polar-π', 'polar-pi'] },
  { id: 'anion-pi', label: 'Anion-π', keywords: ['anion-pi', 'anion_pi', 'anion-π'] },
  { id: 'apolar-vdw', label: 'Apolar vdW contacts', keywords: ['apolar vdw', 'apolar_vdw'] },
  { id: 'ch-on', label: 'CH-O/N bonds', keywords: ['ch-o', 'c-h_on', 'c-h on'] },
  { id: 'ch-pi', label: 'CH-π interactions', keywords: ['ch-pi', 'ch-π', 'c-h_pi'] },
  { id: 'cation-pi', label: 'Cation-π', keywords: ['cation-pi', 'cation_pi', 'cation-π'] },
  { id: 'clash', label: 'Clashes', keywords: ['clash'] },
  { id: 'h-bond', label: 'H-bonds', keywords: ['h-bond', 'h-bond*', 'hydrogen bond'] },
  { id: 'halogen', label: 'Halogen bonds', keywords: ['halogen'] },
  { id: 'lone-pair-pi', label: 'lp-π interactions', keywords: ['lone_pair_pi', 'lone pair', 'lp-pi', 'lp-π'] },
  { id: 'metal', label: 'Metal-mediated contacts', keywords: ['metal mediated', 'metal_mediated'] },
  { id: 'ons-oh-pi', label: 'O/N/SH-π interactions', keywords: ['n-s-o-h', 'n-s-o-h_pi', 'o/n/sh'] },
  { id: 'polar-vdw', label: 'Polar vdW contacts', keywords: ['polar vdw', 'polar_vdw'] },
  { id: 'proximal', label: 'Proximal contacts', keywords: ['proximal'] },
  { id: 'salt-bridge', label: 'Salt-bridges', keywords: ['salt-bridge', 'salt bridge'] },
  { id: 'ss-bond', label: 'S-S bonds', keywords: ['ss bond', 's-s bond', 'ss_bond'] },
  { id: 'water', label: 'Water-mediated contacts', keywords: ['water mediated', 'water_mediated'] }
]

