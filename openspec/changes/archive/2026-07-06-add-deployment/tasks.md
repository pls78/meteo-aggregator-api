## 1. Container

- [x] 1.1 Add `Dockerfile` (python:3.12-slim, `pip install .`, uvicorn binds
  `0.0.0.0:${PORT:-8080}`) and `.dockerignore`

## 2. HTTP layer

- [x] 2.1 Read the CORS allow-list from `ALLOWED_ORIGINS` (comma-separated) in
  `api/main.py`, falling back to the local dev origins when unset
- [x] 2.2 Add `GET /health` returning `{"status": "ok"}` with no upstream calls

## 3. Deploy

- [x] 3.1 Deploy to Google Cloud Run (`europe-west1`, `--allow-unauthenticated`)
- [x] 3.2 Set `ALLOWED_ORIGINS` to the deployed UI origin
  (`https://meteo-aggregator.pages.dev`)

## 4. Docs

- [x] 4.1 Document deployment, `GET /health`, and env-driven CORS in
  `api/README.md` and the root `README.md`
