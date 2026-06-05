"""Filesystem path helpers for system directories."""
from pathlib import Path


def get_systems_dir(app) -> Path:
    """Return the configured systems directory."""
    data_folder = app.config.get("DATA_FOLDER") or app.config["UPLOAD_FOLDER"]
    return Path(data_folder) / "systems"


def get_system_path(app, system_id) -> Path | None:
    """
    Resolve a user-provided system ID to a safe systems/<id> child path.

    System IDs are directory names, not paths. Reject hidden names, empty names,
    path separators, and anything that resolves outside the systems directory.
    """
    if not isinstance(system_id, str):
        return None
    name = system_id.strip()
    if not name or name.startswith(".") or "/" in name or "\\" in name:
        return None

    systems_dir = get_systems_dir(app).resolve()
    candidate = (systems_dir / name).resolve()
    if candidate.parent != systems_dir:
        return None
    return candidate
