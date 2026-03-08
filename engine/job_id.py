import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_utc(value: object) -> Optional[datetime]:
    """
    Parse ISO timestamps stored by this project.
    Accepts:
      - 2026-05-30T12:34:56Z
      - 2026-05-30T12:34:56+00:00
    Returns an aware UTC datetime or None.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def isoformat_utc(dt: datetime) -> str:
    """Return an ISO 8601 string with a trailing 'Z' for UTC."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_job_id(now: Optional[datetime] = None, random_len: int = 8) -> str:
    """
    Generate a job ID of the form:
      YYYYDDD-RRRRRRRR

    - YYYY: 4-digit year (UTC)
    - DDD: day of year (001-366)
    - R: random (A-Z,0-9), length = random_len
    """
    if now is None:
        now = _utc_now()
    day_of_year = now.timetuple().tm_yday
    date_part = f"{now.year}{day_of_year:03d}"
    rand = "".join(secrets.choice(ALPHABET) for _ in range(max(1, int(random_len))))
    return f"{date_part}-{rand}"


def ensure_job_fields(
    metadata: dict,
    *,
    now: Optional[datetime] = None,
    days_valid: int = 60,
    regenerate_if_expired: bool = True,
) -> dict:
    """
    Ensure `metadata` contains:
      - jobId
      - jobCreatedAt
      - jobExpiresAt

    If jobId is missing, it is generated.
    If regenerate_if_expired is True and jobExpiresAt is present but in the past,
    a new jobId is generated and timestamps are reset.
    """
    if now is None:
        now = _utc_now()

    created_at = _parse_iso_utc(metadata.get("jobCreatedAt"))
    expires_at = _parse_iso_utc(metadata.get("jobExpiresAt"))
    has_job_id = isinstance(metadata.get("jobId"), str) and bool(metadata.get("jobId").strip())

    is_expired = False
    if expires_at is not None and expires_at <= now:
        is_expired = True

    if (not has_job_id) or (regenerate_if_expired and is_expired):
        metadata["jobId"] = generate_job_id(now=now)
        metadata["jobCreatedAt"] = isoformat_utc(now)
        metadata["jobExpiresAt"] = isoformat_utc(now + timedelta(days=int(days_valid)))
        return metadata

    # jobId exists and not expired (or we don't regenerate). Ensure timestamps exist.
    if created_at is None:
        metadata["jobCreatedAt"] = isoformat_utc(now)
    if expires_at is None:
        metadata["jobExpiresAt"] = isoformat_utc(now + timedelta(days=int(days_valid)))

    return metadata
