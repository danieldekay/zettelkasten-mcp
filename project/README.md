# Resource-Efficient Docker Runbook for zettelkasten-mcp

This project package provides a low-footprint Docker setup for running `zettelkasten-mcp`.

## What is optimized

- Multi-stage build (`project/Dockerfile`) to keep runtime image lean
- Runtime-only dependencies (`--no-dev`) to avoid test/lint packages
- Build cache mounts for faster, lower-CPU rebuilds
- Read-only root filesystem + small `/tmp` tmpfs
- Explicit CPU/memory/PID limits in compose
- Named volume persistence for SQLite + notes

## Build

From `zettelkasten-mcp/project/`:

```bash
docker compose -f docker-compose.yml build
```

## Run

```bash
docker compose -f docker-compose.yml up
```

## Stop

```bash
docker compose -f docker-compose.yml down
```

## Persisted data

Data is stored in named volume `zettelkasten_data` mounted at `/data`:

- Notes: `/data/notes`
- SQLite DB: `/data/db/zettelkasten.db`

## Tuning knobs

In `project/docker-compose.yml`, adjust:

- `mem_limit` (default `384m`)
- `cpus` (default `0.50`)
- `pids_limit` (default `64`)

Recommended first tuning steps:

1. Lower memory to `256m`; if OOM occurs during heavy indexing, return to `384m`.
2. Keep single process model for SQLite safety.
3. Keep read-only filesystem unless adding features that require write access outside `/data`.

## Optional host bind mount (for easy direct file access)

Replace volume section with:

```yaml
volumes:
  - ../data:/data
```

Use bind mounts in local dev; named volume is usually safer and less noisy for long-running usage.
