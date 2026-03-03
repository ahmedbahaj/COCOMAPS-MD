import json
from pathlib import Path
from typing import Set

from job_id import ensure_job_fields, generate_job_id, isoformat_utc


def update_metadata_files(systems_dir: Path, days_valid: int = 60) -> None:
    """
    For each system in `systems_dir`, add a jobId and expiry info to _metadata.json
    if they are not already present.
    """
    if not systems_dir.is_dir():
        raise SystemExit(f"Systems directory not found: {systems_dir}")

    # Track job ids to avoid collisions within this run.
    seen: Set[str] = set()

    for system_dir in systems_dir.iterdir():
        if not system_dir.is_dir():
            continue

        metadata_path = system_dir / "_metadata.json"
        if not metadata_path.is_file():
            continue

        try:
            with metadata_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"Skipping {metadata_path} (invalid JSON): {exc}")
            continue

        if not isinstance(data, dict):
            print(f"Skipping {metadata_path} (expected JSON object).")
            continue

        # If already has a jobId, keep it (don't rewrite timestamps).
        if isinstance(data.get("jobId"), str) and data["jobId"].strip():
            print(f"{metadata_path}: jobId already present ({data['jobId']}), skipping.")
            continue

        # Ensure fields exist; make jobId unique within this run.
        ensure_job_fields(data, days_valid=days_valid, regenerate_if_expired=False)
        while data.get("jobId") in seen:
            data["jobId"] = generate_job_id()
        seen.add(data.get("jobId"))

        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"{metadata_path}: added jobId={data.get('jobId')}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    systems_dir = repo_root / "systems"
    update_metadata_files(systems_dir)


if __name__ == "__main__":
    main()

