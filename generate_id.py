import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_job_id(now: Optional[datetime] = None) -> str:
    """
    Generate a job ID of the form:
    YYYYDDD-RRRRRRRR

    - YYYY: 4-digit year (UTC)
    - DDD: day of year (001-366)
    - RRRRRRRR: 8-character random base36-like (A-Z,0-9)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    day_of_year = now.timetuple().tm_yday
    date_part = f"{now.year}{day_of_year:03d}"
    random_part = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{date_part}-{random_part}"


def isoformat_utc(dt: datetime) -> str:
    """Return an ISO 8601 string with a trailing 'Z' for UTC."""
    return dt.replace(microsecond=0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def update_metadata_files(systems_dir: Path, days_valid: int = 60) -> None:
    """
    For each system in `systems_dir`, add a jobId and expiry info to _metadata.json
    if they are not already present.
    """
    if not systems_dir.is_dir():
        raise SystemExit(f"Systems directory not found: {systems_dir}")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=days_valid)

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

        # Skip if a jobId is already present
        if "jobId" in data:
            print(f"{metadata_path}: jobId already present ({data['jobId']}), skipping.")
            continue

        job_id = generate_job_id(now)
        data["jobId"] = job_id
        data["jobCreatedAt"] = isoformat_utc(now)
        data["jobExpiresAt"] = isoformat_utc(expires_at)

        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"{metadata_path}: added jobId={job_id}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    systems_dir = repo_root / "systems"
    update_metadata_files(systems_dir)


if __name__ == "__main__":
    main()

