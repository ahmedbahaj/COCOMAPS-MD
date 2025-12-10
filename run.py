import subprocess
import os
import re
from pathlib import Path
from distutils.util import strtobool

HOST_ROOT_DIR = "C:/Users/Ahmed/Desktop/PDB-examples/5ak0dimer_JBT1CAB_100f"
DOCKER_IMAGE_REDUCE = os.environ.get("COCOMAPS_IMAGE_REDUCE", "andrpet/cocomaps-backend:0.0.19")
DOCKER_IMAGE_NO_REDUCE = os.environ.get(
    "COCOMAPS_IMAGE_NO_REDUCE", "sattamaltwaim/cocomaps-backend:no-reduce"
)
USE_REDUCE = bool(strtobool(os.environ.get("COCOMAPS_USE_REDUCE", "true")))
DOCKER_IMAGE = DOCKER_IMAGE_REDUCE if USE_REDUCE else DOCKER_IMAGE_NO_REDUCE
CONTAINER_EXECUTION = "python /app/coco2/begin.py"
INPUT_FILE_NAME = "example_input.json"

def get_frame_numbers(root_dir):
    frame_numbers = []
    root_path = Path(root_dir)
    
    if not root_path.exists():
        print(f"Warning: Directory {root_dir} does not exist.")
        return frame_numbers
    
    #looking for folders matching frame_* pattern
    for item in root_path.iterdir():
        if item.is_dir():
            match = re.match(r'frame_(\d+)', item.name)
            if match:
                frame_numbers.append(int(match.group(1)))
    
    return sorted(frame_numbers)

def run_frame_processing():
    frame_numbers = get_frame_numbers(HOST_ROOT_DIR)
    
    print(f"Found {len(frame_numbers)} frame(s) to process: {frame_numbers}\n")
    
    for i in frame_numbers:
        frame_folder = f"frame_{i}"
        
        container_input_path = f"/app/data/{INPUT_FILE_NAME}"
        docker_command = (
            f"docker run "
            f"-v {HOST_ROOT_DIR}/{frame_folder}:/app/data " #mount
            f"-it {DOCKER_IMAGE} "
            f"{CONTAINER_EXECUTION} "
            f"{container_input_path}"
        )
        print(f"processing: {docker_command}")

        try:
            subprocess.run(
                docker_command, shell=True, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True 
            )
            print(f"done: {frame_folder}.\n")

        except subprocess.CalledProcessError as e:
            print(f"docker command failed for {frame_folder}.")
            print(f"Output:\n{e.output}")

if __name__ == "__main__":
    try:
        run_frame_processing()
    except Exception as e:
        print(f"{e}")