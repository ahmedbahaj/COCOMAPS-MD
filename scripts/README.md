# Operational scripts

## `cleanup_expired_systems.py`

Removes subfolders under **`systems/`** whose **`_metadata.json`** has **`jobExpiresAt`** in the past (compared with current time in UTC). This matches the expiry fields managed by **`engine/job_id.py`**.

Directories are **skipped** when:

- **`isExample`** is **`true`** (bundled demo data),
- **`_metadata.json`** is missing or invalid,
- **`jobExpiresAt`** is missing or not parseable,

so ambiguous or legacy runs are not wiped automatically.

### Usage

Default **`systems`** directory:

- Repo checkout (from repo root): **`systems/`**
- Docker backend container: **`/app/systems`** (mounted volume **`systems-data`**)

Optional environment variable **`COCOMAPS_SYSTEMS_DIR`** overrides the path when **`--systems-dir`** is omitted.

Dry-run (recommended first — lists paths that **would** be removed):

```bash
python scripts/cleanup_expired_systems.py
```

Apply deletions:

```bash
python scripts/cleanup_expired_systems.py --apply
```

Custom directory:

```bash
python scripts/cleanup_expired_systems.py --systems-dir /path/to/systems --apply
```

From **repository root**, Python can resolve **`engine`** automatically. Else set **`PYTHONPATH`** to the repo root.

### Scheduling (Docker Compose)

Production data lives in the backend volume (**`/app/systems`** in the **`backend`** service). Typical pattern: **cron on the host** runs Compose once daily, for example at **00:00 UTC**:

```cron
0 0 * * * cd /path/to/COCOMAPS-MD && docker compose exec -T backend python scripts/cleanup_expired_systems.py --apply >> /var/log/cocomaps-cleanup.log 2>&1
```

Use **`docker compose run --rm --no-deps backend`** instead of **`exec`** if you prefer a one-shot container instead of attaching to the long-running **`backend`** process.

Adjust **`cd`** to the directory that contains **`docker-compose.yml`**. Ensure the **`backend`** image includes **`scripts/`** (Dockerfile **`COPY`**); rebuild after changing this script.

### Exit codes

- **0**: Success (nothing to delete, or **`--apply`** completed without unrecoverable errors).
- **1**: **`systems`** path missing or at least one delete failed during **`--apply`**.
