## 1. Config

- [x] 1.1 Add `EUMETVIEW_WMS_URL`, `EUMETVIEW_CRS`, `EUMETVIEW_FORMAT`, and
  `EUMETVIEW_LAYERS` catalog to `config.py`

## 2. Domain models

- [x] 2.1 Add `WmsLayerParams` pydantic model to `models.py` (`wms_url`, `layer`,
  `title`, `time`, `crs`, `format`)
- [x] 2.2 Add `SatelliteImagery` model (`generated_at`, `layers`)

## 3. Provider

- [x] 3.1 Implement `providers/eumetview.py`: `get_satellite_imagery(at) ->
  SatelliteImagery`; snap `at` to each layer's cadence boundary; return
  `time=None` for layers whose archive starts after `at`

## 4. Client facade

- [x] 4.1 Add `get_satellite_imagery(at, ...)` to `client.py`; export
  `get_satellite_imagery`, `WmsLayerParams`, and `SatelliteImagery` from
  `__init__.py`

## 5. HTTP layer

- [x] 5.1 Add `GET /imagery?time=<ISO>` to `api/main.py` with optional `time`
  parameter (default: now); reject non-parseable datetimes (HTTP 422)

## 6. Tests

- [x] 6.1 Provider unit tests: all layers returned; time snapping per cadence;
  pre-archive time yields `time=None` for that layer; no-time defaults to now
- [x] 6.2 API tests with no mock needed (provider is pure): success shape; time
  param forwarded; invalid time → 422
- [x] 6.3 Network-gated live integration test: request `/imagery` and verify the
  WMS URLs are reachable (HEAD request)

## 7. Docs

- [x] 7.1 Document `/imagery` in `api/README.md` (params, `WmsLayerParams` fields,
  example, how to use with a map library)
- [x] 7.2 Add a short "Live satellite imagery" section to the root `README.md`
