## Why

The README anticipates a web UI, and a local Vite dev server
(`http://localhost:5173`) is now calling the API from the browser. The browser's
same-origin policy blocks those `fetch` calls because the API serves no
`Access-Control-Allow-Origin` header — the request reaches the server but the
response is unreadable to the page. We need CORS so the local web client can
consume the existing read-only endpoints. This touches only the HTTP layer and
none of the forecasting, geocoding, or imagery pipelines.

## What Changes

- Add FastAPI's `CORSMiddleware` to the app, allowing the local web UI origins
  (`http://localhost:5173` and `http://127.0.0.1:5173`).
- Restrict the grant to `GET` methods only — the API is read-only, so no other
  verbs need to be exposed to the browser.
- No changes to any endpoint's behavior, routing, or payloads.

## Capabilities

### New Capabilities
<!-- None — this is an additive policy on the existing HTTP layer. -->

### Modified Capabilities
- `forecast-api`: The thin HTTP layer gains a browser-CORS requirement so an
  allowed local web-UI origin can read responses from the API's read-only
  endpoints.

## Impact

- **New code:** a `CORSMiddleware` registration in `api/main.py`. No new modules,
  models, or dependencies (`CORSMiddleware` ships with FastAPI/Starlette).
- **External services:** none.
- **No breaking changes** — purely additive; existing non-browser clients are
  unaffected.
