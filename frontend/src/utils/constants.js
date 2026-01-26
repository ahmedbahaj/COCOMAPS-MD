/**
 * Interaction filters backed by trajectory outputs
 */
export const INTERACTION_TYPES = [
  { id: 'pi-pi', label: 'π-π interactions', keywords: ['pi-pi', 'π-π'], trendLabel: 'π-π interactions' },
  { id: 'amino-pi', label: 'Polar-π (Amino-π)', keywords: ['amino-pi', 'amino_pi', 'polar-π', 'polar-pi'], trendLabel: 'Amino-π interactions' },
  { id: 'anion-pi', label: 'Anion-π interactions', keywords: ['anion-pi', 'anion_pi', 'anion-π'], trendLabel: 'Anion-π interactions' },
  { id: 'apolar-vdw', label: 'Apolar vdW contacts', keywords: ['apolar vdw', 'apolar_vdw'], trendLabel: 'Apolar vdW contacts' },
  { id: 'ch-on', label: 'CH-O/N bonds', keywords: ['ch-o', 'c-h_on', 'c-h on'], trendLabel: 'CH-O/N bonds' },
  { id: 'ch-pi', label: 'CH-π interactions', keywords: ['ch-pi', 'ch-π', 'c-h_pi'], trendLabel: 'CH-π interactions' },
  { id: 'cation-pi', label: 'Cation-π interactions', keywords: ['cation-pi', 'cation_pi', 'cation-π'], trendLabel: 'Cation-π interactions' },
  { id: 'clash', label: 'Clashes', keywords: ['clash'], trendLabel: 'Clashes' },
  { id: 'h-bond', label: 'H-bonds', keywords: ['h-bond', 'h-bond*', 'hydrogen bond'], trendLabel: 'H-bonds' },
  { id: 'halogen', label: 'Halogen bonds', keywords: ['halogen'], trendLabel: 'Halogen bonds' },
  { id: 'lone-pair-pi', label: 'lp-π interactions', keywords: ['lone_pair_pi', 'lone pair', 'lp-pi', 'lp-π'], trendLabel: 'Lone pair-π interactions' },
  { id: 'metal', label: 'Metal-mediated contacts', keywords: ['metal mediated', 'metal_mediated', 'metal-mediated'], trendLabel: 'Metal mediated' },
  { id: 'ons-oh-pi', label: 'O/N/SH-π interactions', keywords: ['n-s-o-h', 'n-s-o-h_pi', 'o/n/sh'], trendLabel: 'O/N/SH-π interactions' },
  { id: 'polar-vdw', label: 'Polar vdW contacts', keywords: ['polar vdw', 'polar_vdw'], trendLabel: 'Polar vdW contacts' },
  { id: 'proximal', label: 'Proximal contacts', keywords: ['proximal'], trendLabel: 'Proximal contacts' },
  { id: 'salt-bridge', label: 'Salt-bridges', keywords: ['salt-bridge', 'salt bridge'], trendLabel: 'Salt-bridges' },
  { id: 'ss-bond', label: 'S-S bonds', keywords: ['ss bond', 's-s bond', 'ss_bond'], trendLabel: 'S-S bonds' },
  { id: 'water', label: 'Water-mediated contacts', keywords: ['water mediated', 'water_mediated', 'water-mediated'], trendLabel: 'Water mediated' }
]

