# CLAUDE.md

## Overview
Maskarr: a single-file Python HTTP proxy that rewrites User-Agent and headers so *arr stack apps (Prowlarr, Jackett) can reach private trackers. Includes a web UI for managing trackers and a JSON REST API.

## Commands
- Install: `pip install -r requirements.txt`
- Run (dev): `python3 maskarr.py`
- Quick check (no test suite exists yet): `python3 -m py_compile maskarr.py`
- Docker build: `docker build -t maskarr .`
- Docker run: `docker-compose up -d`

## Architecture
Everything lives in `maskarr.py`: an `http.server`-based proxy that forwards requests to the configured tracker domain with a rewritten User-Agent/headers, plus a small web UI and `/api/trackers` REST endpoints. Configuration persists to `maskarr_config.json` (path overridable via `CONFIG_PATH`). See `docs/usage.md` and `docs/deployment.md`.

## Conventions
- Only `CONFIG_PATH` is read from the environment (`maskarr.py`); everything else lives in `maskarr_config.json`.
- Keep `.env.example` limited to variable names actually read from the environment.

## Workflow quirks
- No linter/formatter (ruff/black/flake8) or test suite (pytest) is configured yet. The only available check is a syntax compile (`py_compile`); see LESSONS.md.
- No `development` branch exists yet; CI and the version workflow reference it per the standard shape, but they won't trigger until it's created.

## Deployment
Docker image published to GHCR only, on push to `main`/tags (`.github/workflows/docker-publish.yml`). Version workflow lives in `.gitea/workflows/`; CI runs in both `.gitea/workflows/` and `.github/workflows/`. See `docs/deployment.md` for systemd and Docker instructions.

## Gotchas
- `maskarr_config.json` is tracked as an empty template; don't commit it populated with real tracker credentials/cookies.
- This proxy is meant for local/private-network use only (see Security notes in `docs/usage.md`).
