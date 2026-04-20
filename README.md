# COCOMAPS-MD — Dev Repo

Private development repository for COCOMAPS-MD. All source code, Dockerfiles, and tests live here.

The **public-facing** README, `docker-compose.yml` (image-only), and `coco-md` wrapper script live in [sattamaltwaim/COCOMAPS-MD](https://github.com/sattamaltwaim/COCOMAPS-MD). Do not duplicate them here.

## Prerequisites

- Docker Engine + Docker Compose
- Node.js 20+ (frontend dev only)
- Python 3.11+ (local engine/backend dev only)

## Building

### All services (backend + frontend)

```bash
docker compose build
```

Images are built from source using the Dockerfiles in this repo. The compose file uses `build:` contexts, unlike the public repo's image-only compose.

### Backend only

```bash
docker compose build backend
```

Uses `Dockerfile.backend` — Python 3.11-slim with system deps (gcc, gfortran, csh), pip requirements from `requirements-backend.txt`, and the native binaries in `deps/` (reduce, hbplus, naccess).

### Frontend only

```bash
docker compose build frontend
```

Uses `Dockerfile.frontend` — two-stage build: Node 20 builds the Vue app, then nginx serves the static files at `/BioTools/COCOMAPS-MD/`. The nginx config is `nginx.conf` in the repo root.

### CLI image

```bash
docker compose build cli
```

Uses `Dockerfile.cli` — same Python base as backend, plus Node.js, Chromium, and highcharts-export-server for chart PNG export. Installs the `coco-md` entry point via `setup.py`. The CLI service is behind a Compose profile so it doesn't start with `docker compose up`.

## Running

### Web app (backend + frontend)

```bash
docker compose up -d
```

- Frontend: http://localhost:80/BioTools/COCOMAPS-MD/
- Backend API: http://localhost:5001

Analyzed data persists in the `systems-data` Docker volume.

### CLI (one-off run)

```bash
docker compose run --rm cli my_protein.pdb -c A B -o results/
```

The CLI service mounts `./systems` to `/data/systems` inside the container. Pass any arguments after `cli` — they go straight to the `coco-md` entry point.

## Publishing to Docker Hub

Build and push all three images:

```bash
docker build --platform linux/amd64 -f Dockerfile.backend -t sattamaltwaim/cocomaps-md-backend .
docker build --platform linux/amd64 -f Dockerfile.cli     -t sattamaltwaim/cocomaps-md-cli     .
docker build                        -f Dockerfile.frontend -t sattamaltwaim/cocomaps-md-frontend .

docker push sattamaltwaim/cocomaps-md-backend
docker push sattamaltwaim/cocomaps-md-frontend
docker push sattamaltwaim/cocomaps-md-cli
```

Backend and CLI must target `linux/amd64` (native binaries in `deps/`). Frontend is architecture-independent.

After pushing, end users pull the new images via the public repo's instructions (`docker compose pull && docker compose up -d`), and CLI users run `coco-md --update`.

## Job Privacy

Job IDs are stored in each user's browser via `localStorage` (key: `cocomapsmd:submittedJobIds`). The Jobs page only shows jobs whose IDs are present in that list, so each user sees only their own submissions. Analysis URLs remain publicly shareable — anyone with a direct `/analysis/:jobId` link can view the results.

## Repo layout

```
├── backend/          Flask REST API (routes/, app.py)
├── cli/              CLI entry point (main.py, charts.py)
├── cocomaps/         Local CoCoMaps library (interaction detection)
├── engine/           Core analysis pipeline (no web deps)
├── frontend/         Vue 3 + Vite SPA
├── deps/             Native linux/amd64 binaries (reduce, hbplus, naccess)
├── stubs/            Type stubs
├── tests/            Pytest tests
├── example_systems/  Sample analyzed outputs for the Examples page
├── scripts/          Utility scripts
├── Dockerfile.backend
├── Dockerfile.frontend
├── Dockerfile.cli
├── docker-compose.yml   ← build-from-source (dev), not the public image-only one
├── nginx.conf
├── setup.py             ← CLI package + coco-md entry point
├── requirements.txt
├── requirements-backend.txt
└── requirements-cli.txt
```

## Public repo

[`sattamaltwaim/COCOMAPS-MD`](https://github.com/sattamaltwaim/COCOMAPS-MD) contains:

- `README.md` — end-user deployment & CLI install guide
- `docker-compose.yml` — image-only compose (no build contexts)
- `coco-md` — cross-platform wrapper script that users download

When you change the CLI interface, update the public repo's `README.md` and `coco-md` wrapper to match.
