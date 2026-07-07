## Why

The API needs to run somewhere the web UI (deployed separately) and a few
personal users can reach it, at essentially no cost. The service is stateless,
keyless, read-only, and holds no persistent state, so it is a natural fit for a
scale-to-zero container platform. Two gaps blocked a clean deploy: the CORS
allow-list was hardcoded to the local dev origins, and there was no cheap
liveness probe / container entrypoint.

## What Changes

- Add a minimal `Dockerfile` (+ `.dockerignore`) so the API builds and runs as a
  container; uvicorn binds `0.0.0.0:$PORT` (platform-injected, default `8080`).
- Make the CORS allow-list configurable via the `ALLOWED_ORIGINS` environment
  variable (comma-separated), falling back to the local dev origins when unset,
  so the deployed UI origin is not baked into the image.
- Add `GET /health` (returns `{"status": "ok"}`, no upstream calls) for uptime
  and container health checks.
- Deploy to Google Cloud Run (`europe-west1`, scale-to-zero, public).

## Capabilities

### New Capabilities
- `deployment`: the API is packaged and run as a stateless, scale-to-zero
  container with a platform-injected listen port.

### Modified Capabilities
- `forecast-api`: the browser-CORS requirement becomes a configurable allow-list
  (via `ALLOWED_ORIGINS`), and a health-check endpoint is added.

## Impact

- **New code:** `Dockerfile`, `.dockerignore`, env-driven CORS + `GET /health` in
  `api/main.py`. No new runtime dependencies.
- **External services:** Google Cloud Run (deploy target); no new upstreams.
- **No breaking changes** — CORS defaults unchanged when `ALLOWED_ORIGINS` is
  unset; all existing endpoints and payloads are untouched.
