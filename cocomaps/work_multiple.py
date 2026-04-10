import os
import json
from Bio.PDB import PDBParser, MMCIFParser
import copy
import requests
from bs4 import BeautifulSoup
import shutil

input_dict = {
    "pdb_file": "",
    "chains_set_1": [],
    "chains_set_2": [],
    "ranges_1": [],
    "ranges_2": [],
    "HBOND_DIST": 3.9,
    "HBOND_ANGLE": 90,
    "SBRIDGE_DIST": 4.0,
    "WBRIDGE_DIST": 3.9,
    "CH_ON_DIST": 3.5,
    "CH_ON_ANGLE": 110,
    "CUT_OFF": 5.0,
    "APOLAR_TOLERANCE": 0.4,
    "POLAR_TOLERANCE": 0.4,
    "PI_PI_DIST": 5.5,
    "PI_PI_THETA": 80,
    "PI_PI_GAMMA": 90,
    "ANION_PI_DIST": 5.0,
    "LONEPAIR_PI_DIST": 5.0,
    "CATION_PI_DIST": 5.0,
    "METAL_DIST": 3.2,
    "HALOGEN_THETA1": 120,
    "HALOGEN_THETA2": 110,
    "C_H_PI_DIST": 4.5,
    "C_H_PI_THETA1": 120,
    "C_H_PI_THETA2": 30,
    "NSOH_PI_DIST": 4.5,
    "NSOH_PI_THETA1": 120,
    "NSOH_PI_THETA2": 30,
}


def get_chains(pdb):
    url = f"https://www.rcsb.org/structure/{pdb[:4].upper()}"
    html_content = requests.get(url)
    soup = BeautifulSoup(html_content.content, "html.parser")
    area1 = soup.find("div", {"class": "table-responsive"})
    area1_1 = area1.find("tr", {"id": "macromolecule-entityId-1-rowDescription"})
    area1_2 = area1_1.find_all("a")
    chain1 = area1_2[0].get_text()
    if "auth" in chain1:
        chain1 = chain1.split()[2].replace("]", "")
    area2 = soup.find("tr", {"id": "macromolecule-entityId-2-rowDescription"})
    area2_2 = area2.find_all("a")
    chain2 = area2_2[0].get_text()
    if "auth" in chain2:
        chain2 = chain2.split()[2].replace("]", "")
    return chain1, chain2


def run(dir_path):
    error_file = open("error.out", "w")
    inp_dic = copy.deepcopy(input_dict)
    for pdb in os.listdir(dir_path):
        if len(pdb) == 8:
            try:
                input_file_name = os.path.join(dir_path, f"{pdb}_input.json")
                pdb_path = os.path.join(dir_path, pdb)
                new_pdb_path = os.path.join(
                    "/Users/utkarshkalra/kaust/coco_new/res_pdbs", pdb
                )
                shutil.copyfile(pdb_path, new_pdb_path)
                pdb_path = new_pdb_path
                chain1, chain2 = get_chains(pdb)
                inp_dic["pdb_file"] = pdb_path
                inp_dic["chains_set_1"] = [chain1]
                inp_dic["chains_set_2"] = [chain2]
                json_object = json.dumps(inp_dic, indent=4)
                # Writing to sample.json
                with open(input_file_name, "w") as outfile:
                    outfile.write(json_object)
                # os.system(
                #     f"python /Users/utkarshkalra/kaust/coco_new/begin.py {input_file_name}"
                # )
                # os.remove(input_file_name)
            except Exception as e:
                print(f"{pdb} nahi chali")
                error_file.write(f"{pdb} nahi chali")
                error_file.write(e)
                error_file.write("\n")
                print(e)
                print()
        error_file.close()


def run_all_by_json(dir):
    er_file = open("error1.out", "w")
    for json_file in os.listdir(dir):
        if json_file.endswith(".json"):
            try:
                input_file = os.path.join(dir, json_file)
                os.system(
                    f"python /Users/utkarshkalra/kaust/coco_new/begin.py {input_file}"
                )
            except Exception as e:
                er_file.write(f"{json_file}\n")
                er_file.write(f"{e}\n")
    er_file.close()


def remove_unwanted(dir):
    for fl in os.listdir(dir):
        if len(fl) > 8:
            path = os.path.join(dir, fl)
            os.remove(path)

            print(f"deleted {path}")


def get_all_chains(pdb_file):
    pdb_name = os.path.basename(pdb_file)
    if pdb_file.endswith(".pdb"):
        pdb = PDBParser().get_structure(pdb_name, pdb_file)
    elif pdb_file.endswith(".cif"):
        pdb = MMCIFParser().get_structure(pdb_name, pdb_file)
    else:
        return
    chain_ids = []
    for chain in pdb.get_chains():
        chain_ids.append(chain.get_id())
    return chain_ids


def count_multiple_chain(dir):
    for fl in os.listdir(dir):
        try:
            pdb_path = os.path.join(dir, fl)
            chains = get_all_chains(pdb_path)
            if len(chains) > 2:
                print(f"{fl}")
        except Exception as e:
            print(f"{fl} not working")
            print(e)
            print()


# run_all_by_json("/Users/utkarshkalra/kaust/coco_new/pdbs")
all_chain = get_all_chains("/ibex/scratch/kalrau/coco_2/8vaj/8VAJ.pdb")
print(len(all_chain))
print(all_chain)
inp_dic = copy.deepcopy(input_dict)
for chain in all_chain:
    inp_dic["chains_set_1"].append(chain)
    inp_dic["chains_set_2"].append(chain)
    inp_dic["ranges_1"].append([0,10000])
    inp_dic["ranges_2"].append([0,10000])

json_object = json.dumps(inp_dic, indent=4)
# Writing to sample.json
with open("/ibex/scratch/kalrau/coco_2/8vaj/8VAJ_input.json", "w") as outfile:
    outfile.write(json_object)

