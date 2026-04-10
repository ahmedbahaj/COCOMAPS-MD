# from Bio.PDB import NACCESS, PDBParser
# from constants import NACCESS_PATH

# rsa_data_compound, asa_data_compound = NACCESS.run_naccess(
#             model="4g37_4",
#             pdb_file= "/workspaces/cocomaps-docker/failedPDB/4g37_4.pd_h.pdb_A_B_complex.pdb",
#             naccess=NACCESS_PATH,
#         )

# print(rsa_data_compound, asa_data_compound)
polar_pi = {
    "ASN": ["ND2"],
    "AASN": ["ND2"],
    "BASN": ["ND2"],
    "GLN": ["NE2"],
    "AGLN": ["NE2"],
    "BGLN": ["NE2"],
    "A": ["N6"],
    "G": ["N2"],
    "C": ["N4"],
    "DA": ["N6"],
    "DG": ["N2"],
    "DC": ["N4"],
}