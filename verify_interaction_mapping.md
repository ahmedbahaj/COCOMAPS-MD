# Verification of Interaction Type to CSV File Mapping

Based on COCOMAPS2 documentation (https://zenodo.org/records/17390665) and actual file structure:

## All 18 Interaction Types:

1. **H-bond** → `*_H-bond.csv` ✓
2. **Salt-bridge** → `*_Salt_bridge.csv` ✓
3. **π-π interactions** → `*_pi-pi.csv` ✓
4. **Cation-π interactions** → `*_Cation_pi.csv` ✓
5. **Anion-π interactions** → `*_Anion_pi.csv` ✓
6. **CH-O/N bonds** → `*_C-H_ON.csv` ✓
7. **CH-π interactions** → `*_C-H_pi.csv` ✓
8. **Halogen bonds** → `*_Halogen_bond.csv` ✓
9. **Apolar vdW contacts** → `*_Apolar_vdw.csv` ✓
10. **Polar vdW contacts** → `*_Polar_vdw.csv` ✓
11. **Proximal contacts** → `*_Proximal.csv` ✓
12. **Clashes** → `*_Clash.csv` ✓
13. **Metal-mediated contacts** → `*_Metal_Mediated.csv` ✓
14. **O/N/SH-π interactions** → `*_N-S-O-H_pi.csv` ✓
15. **Lone pair-π interactions** → `*_Lone_pair_pi.csv` ✓
16. **Water-mediated contacts** → `*_Water_Mediated.csv` ✓
17. **S-S bonds** → `*_SS_bond.csv` ✓
18. **Amino-π interactions** → `*_Amino_pi.csv` ✓

## File Pattern:
All files follow the pattern: `{frame_name}.pd_h.pdb_A_B_{interaction_type}.csv`

## Distance Column:
All interaction-specific CSV files contain "Distance (Å)" column.

