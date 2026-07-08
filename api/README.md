# Meteo-Aggregator HTTP API

The HTTP layer is a thin wrapper over the `meteo_aggregator` library core. It
parses/validates the request, delegates to `get_forecast`, and returns the
aggregated forecast as JSON. No forecasting logic lives here.

## Running

```bash
pip install -e ".[dev]"
uvicorn api.main:app --reload          # http://localhost:8000
```

Interactive docs are available once running:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## Deployment

The service is stateless, keyless, and holds no persistent state, so it runs as a
single scale-to-zero container. A minimal [`Dockerfile`](../Dockerfile) builds it;
uvicorn binds `0.0.0.0:$PORT` (the platform injects `$PORT`, default `8080`).

Deployed target — Google Cloud Run (`europe-west1`):
<https://your-backend.example.com>

```bash
# from the repo root — builds the Dockerfile, deploys, prints the HTTPS URL
gcloud run deploy meteo-aggregator --source . --region europe-west1 --allow-unauthenticated

# point CORS at the deployed UI origin (see below)
gcloud run services update meteo-aggregator --region europe-west1 \
  --set-env-vars ALLOWED_ORIGINS=https://meteo-aggregator.pages.dev
```

Cloud Run scales to zero, so the service costs nothing while idle; the first
request after inactivity pays a ~1–2 s cold start.

## Browser clients (CORS)

The API is read-only, so it emits CORS headers for `GET` only. The allowed
origins are configurable via the `ALLOWED_ORIGINS` environment variable
(comma-separated); when it is unset the app falls back to the local web UI's
dev-server origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

In production, set `ALLOWED_ORIGINS` to the deployed UI origin(s):

```bash
ALLOWED_ORIGINS=https://meteo-aggregator.pages.dev uvicorn api.main:app
```

A page served from an allowed origin can `fetch` the endpoints directly; other
origins are not granted access.

## Endpoints

### `GET /hourly`

Returns a per-hour aggregated forecast for up to 168 hours (7 days): consensus
values, per-hour confidence, and a per-model breakdown for each hour.

#### Query parameters

| Param   | Type  | Required | Default | Constraints   | Description                        |
|---------|-------|----------|---------|---------------|------------------------------------|
| `lat`   | float | yes      | —       | `-90 … 90`    | Latitude in decimal degrees        |
| `lon`   | float | yes      | —       | `-180 … 180`  | Longitude in decimal degrees       |
| `hours` | int   | no       | `48`    | `1 … 168`     | Number of forecast hours to return |

#### Example request

```bash
curl "http://localhost:8000/hourly?lat=45.5&lon=9.5&hours=48"
```

#### Response

`200 OK`, `application/json`. Top-level shape:

| Field          | Type                    | Description                              |
|----------------|-------------------------|------------------------------------------|
| `location`     | object                  | Echo of the requested location           |
| `generated_at` | string (ISO-8601, UTC)  | When the forecast was assembled          |
| `hours`        | array\<HourConsensus\>  | One entry per forecast hour              |

**`HourConsensus`**

| Field        | Type                           | Description                                              |
|--------------|--------------------------------|----------------------------------------------------------|
| `date`       | string (ISO-8601, local)       | Forecast timestamp in the location's local timezone (matches the daily `date`) |
| `lead_hour`  | int                            | 0-indexed offset from the first hour; `lead_hour` 0 is current conditions |
| `values`     | object\<string, number\|null\> | Consensus value per variable (weighted blend)            |
| `confidence` | object                         | Same structure as daily (`level`, `low`, `high`, `spread`) |
| `breakdown`  | array\<HourContribution\>      | Each model's raw values for the hour                     |

**Hourly variables**

| Key                          | Unit  | Meaning                               |
|------------------------------|-------|---------------------------------------|
| `temperature_2m`             | °C    | 2 m air temperature                   |
| `apparent_temperature`       | °C    | Feels-like temperature                |
| `precipitation`              | mm    | Precipitation in this hour            |
| `precipitation_probability`  | %     | Probability of precipitation          |
| `wind_speed_10m`             | km/h  | 10 m wind speed                       |
| `wind_direction_10m`         | °     | 10 m wind direction (non-blendable)   |
| `weather_code`               | WMO   | Categorical condition (non-blendable) |
| `cloud_cover`                | %     | Total cloud cover                     |
| `relative_humidity_2m`       | %     | 2 m relative humidity                 |
| `uv_index`                   | index | UV index                              |

`wind_direction_10m` and `weather_code` are non-blendable: their consensus is
the value from the highest-weighted model rather than an arithmetic mean
(averaging wind directions or WMO codes is geometrically and categorically
meaningless).

### `GET /forecast`

Returns the aggregated multi-model forecast for a location: a per-day consensus,
a confidence signal, and the full per-model breakdown.

#### Query parameters

| Param  | Type  | Required | Default | Constraints            | Description                          |
|--------|-------|----------|---------|------------------------|--------------------------------------|
| `lat`  | float | yes      | —       | `-90 … 90`             | Latitude in decimal degrees          |
| `lon`  | float | yes      | —       | `-180 … 180`           | Longitude in decimal degrees         |
| `days` | int   | no       | `7`     | `1 … 16`               | Number of forecast days to return    |

Invalid, missing, or out-of-range parameters are rejected with **HTTP 422**
*before* any upstream provider call is made.

#### Example request

```bash
curl "http://localhost:8000/forecast?lat=45.5&lon=9.5&days=7"
```

```python
import httpx

resp = httpx.get(
    "http://localhost:8000/forecast",
    params={"lat": 45.5, "lon": 9.5, "days": 7},
)
resp.raise_for_status()
forecast = resp.json()
```

## Response

`200 OK`, `application/json`. Top-level shape:

| Field          | Type            | Description                                   |
|----------------|-----------------|-----------------------------------------------|
| `location`     | object          | Echo of the requested location                |
| `generated_at` | string (ISO-8601, UTC) | When the forecast was assembled        |
| `days`         | array\<DayConsensus\> | One entry per forecast day              |

**`DayConsensus`**

| Field        | Type                       | Description                                                        |
|--------------|----------------------------|--------------------------------------------------------------------|
| `date`       | string (`YYYY-MM-DD`)      | The forecast day                                                   |
| `lead_day`   | int                        | 0-indexed offset from the first day (drives the weighting)         |
| `values`     | object\<string, number\|null\> | Consensus value per variable (weighted blend)                 |
| `confidence` | object                     | See below                                                          |
| `breakdown`  | array\<ModelContribution\> | Each contributing model's raw values for the day, with provenance  |

**`confidence`**

| Field    | Type                          | Description                                                  |
|----------|-------------------------------|--------------------------------------------------------------|
| `level`  | `"high"` \| `"medium"` \| `"low"` | Categorical confidence for the day                       |
| `low`    | number \| null                | Lower bound (`consensus − spread`) of the confidence range   |
| `high`   | number \| null                | Upper bound (`consensus + spread`) of the confidence range   |
| `spread` | number \| null                | Spread (°C) used: larger of inter-model disagreement and ensemble spread |

**`ModelContribution`**

| Field    | Type                           | Description                              |
|----------|--------------------------------|------------------------------------------|
| `model`  | string                         | Open-Meteo model id (e.g. `ecmwf_ifs025`)|
| `role`   | `"general"` \| `"local"`       | Provider role the model came from        |
| `values` | object\<string, number\|null\> | That model's raw values for the day      |

### Variables

`values` keys are the configured daily variables (see
`meteo_aggregator/config.py`). Defaults:

| Key                              | Unit     | Meaning                              |
|----------------------------------|----------|-------------------------------------|
| `temperature_2m_max`             | °C       | Daily maximum temperature           |
| `temperature_2m_min`             | °C       | Daily minimum temperature           |
| `apparent_temperature_max`       | °C       | "Feels-like" maximum                |
| `apparent_temperature_min`       | °C       | "Feels-like" minimum                |
| `precipitation_sum`              | mm       | Total precipitation                 |
| `precipitation_hours`            | h        | Hours with precipitation            |
| `precipitation_probability_max`  | %        | Max precipitation probability       |
| `precipitation_probability_mean` | %        | Mean precipitation probability      |
| `wind_speed_10m_max`             | km/h     | Max 10 m wind speed                 |
| `cloud_cover_mean`               | %        | Mean total cloud cover              |
| `relative_humidity_2m_max`       | %        | Daily max relative humidity         |
| `uv_index_max`                   | index    | Peak UV index                       |
| `daylight_duration`              | s        | Seconds of daylight                 |
| `sunrise`                        | ISO time | Sunrise timestamp (string)          |
| `sunset`                         | ISO time | Sunset timestamp (string)           |
| `weather_code`                   | WMO code | Categorical condition (for icons)   |

A value is `null` when a contributing model doesn't provide that variable.

**Blending vs. representative values.** Numeric variables are weight-blended
across models. `sunrise`, `sunset`, and `weather_code` are *non-blendable*
(averaging timestamps/categories is meaningless): their consensus is taken from
the highest-weighted model present for that day, preserving their native type
(string for sunrise/sunset, integer code for weather_code).

### Example response (trimmed)

The local high-res model (`italia_meteo_arpae_icon_2i`) appears in the
`breakdown` for near-term days and drops out beyond its ~3-day horizon; the
weights renormalize automatically and confidence widens at longer range.

```json
{
  "location": { "latitude": 45.5, "longitude": 9.5, "name": null },
  "generated_at": "2026-06-19T07:45:27.060456Z",
  "days": [
    {
      "date": "2026-06-19",
      "lead_day": 0,
      "values": {
        "temperature_2m_max": 33.09,
        "temperature_2m_min": 21.45,
        "precipitation_sum": 0.38,
        "precipitation_probability_max": 30.9,
        "wind_speed_10m_max": 13.02
      },
      "confidence": {
        "level": "high",
        "low": 32.51,
        "high": 33.66,
        "spread": 0.57
      },
      "breakdown": [
        {
          "model": "ecmwf_ifs025",
          "role": "general",
          "values": { "temperature_2m_max": 33.8, "temperature_2m_min": 23.2,
                      "precipitation_sum": 1.0, "precipitation_probability_max": 12.0,
                      "wind_speed_10m_max": 9.6 }
        },
        {
          "model": "gfs_seamless",
          "role": "general",
          "values": { "temperature_2m_max": 32.2, "temperature_2m_min": 21.1,
                      "precipitation_sum": 1.3, "precipitation_probability_max": 90.0,
                      "wind_speed_10m_max": 12.1 }
        }
      ]
    }
  ]
}
```

### `GET /imagery`

Returns WMS parameters for all configured EUMETSAT EUMETView satellite layers at
a given timestamp. Each entry is ready to register with a map library (Leaflet,
MapLibre); no image bytes flow through this service — the map client fetches
tiles directly from EUMETSAT.

#### Query parameters

| Param  | Type     | Required | Default | Description                                                          |
|--------|----------|----------|---------|----------------------------------------------------------------------|
| `time` | datetime | no       | now     | ISO 8601 UTC timestamp. Each layer's time is snapped to its cadence. |

Non-parseable `time` values are rejected with **HTTP 422**.

#### Example request

```bash
curl "http://localhost:8000/imagery?time=2026-06-20T12:00:00Z"
```

#### Response

`200 OK`, `application/json`. Top-level shape:

| Field          | Type                    | Description                             |
|----------------|-------------------------|-----------------------------------------|
| `generated_at` | string (ISO-8601, UTC)  | When the parameters were computed       |
| `layers`       | array\<WmsLayerParams\> | One entry per configured satellite layer|

**`WmsLayerParams`**

| Field     | Type            | Description                                                                           |
|-----------|-----------------|---------------------------------------------------------------------------------------|
| `wms_url` | string          | WMS endpoint (`https://view.eumetsat.int/geoserver/wms`)                              |
| `layer`   | string          | WMS layer name (e.g. `mtg_fd:ir105_hrfi`)                                             |
| `title`   | string          | Human-readable label                                                                  |
| `time`    | string \| null  | ISO 8601 UTC, snapped to the layer's cadence. `null` if the request predates the archive. |
| `crs`     | string          | `EPSG:3857` (Web Mercator — compatible with Leaflet, MapLibre, Apple MapKit)          |
| `format`  | string          | `image/png` (transparent overlay; required for map compositing)                       |

When `time` is `null` the WMS will serve the most recent available image for
that layer.

#### Configured layers

| `layer`                                           | What it shows                              | Cadence | Archive from |
|---------------------------------------------------|--------------------------------------------|---------|--------------|
| `mtg_fd:rgb_geocolour`                            | Geo Colour RGB — true colour by day, IR/clouds by night | 10 min  | 2024-09-23   |
| `mtg_fd:ir105_hrfi`                               | IR 10.5 µm — cloud imagery                 | 10 min  | 2024-09-23   |
| `mtg_fd:rgb_cloudphase`                           | Cloud Phase RGB — ice vs. water clouds     | 10 min  | 2024-09-23   |
| `mtg_fd:rgb_dust`                                 | Dust RGB — Saharan dust plumes             | 10 min  | 2024-10-22   |
| `msg_fes:rgb_airmass`                             | Airmass RGB — air masses / jet streams     | 15 min  | 2020-09-01   |
| `msg_fes:rgb_convection`                          | Convection RGB — storm potential           | 15 min  | 2020-09-01   |
| `mtg_fd:li_afa`                                   | Lightning Imager flash area                | 5 min   | 2025-05-30   |
| `msg_fes:clm`                                     | Cloud Mask (classified)                    | 15 min  | 2020-09-01   |
| `msg_rss:ir039_nrt`                               | IR 3.9 µm Rapid Scan (fog/low cloud, 5-min, Europe) | 5 min   | 2020-02-12   |
| `copernicus:daily_sentinel3ab_olci_l1_rgb_fulres` | True-colour RGB daily — Sentinel-3 (high-res) | daily   | 2020-02-17   |

The catalog favours visually rich RGB composites and avoids near-duplicate
products. `msg_fes:ir039` (15-min full-disk IR 3.9) is dropped in favour of the
5-min rapid-scan `msg_rss:ir039_nrt` (same product, faster over Europe); the
`gii_*` convective-instability indices are dropped in favour of the Convection
RGB. `msg_fes:ir108` (MSG IR 10.8 µm) remains superseded by `mtg_fd:ir105_hrfi`.

#### Using with a map library

```js
// Leaflet
import L from "leaflet";

for (const layer of imagery.layers) {
  if (!layer.time) continue; // pre-archive, skip or show placeholder
  L.tileLayer.wms(layer.wms_url, {
    layers: layer.layer,
    time: layer.time,
    format: layer.format,
    crs: L.CRS.EPSG3857,
    transparent: true,
    opacity: 0.7,
  }).addTo(map);
}
```

```swift
// Apple MapKit (iOS) — use MKTileOverlay with a URL template built from layer params
```

### `GET /search`

Resolves a place-name query into a ranked list of matching places via the
keyless Open-Meteo Geocoding API. Use it to turn a name into coordinates, then
call `/forecast`.

#### Query parameters

| Param      | Type   | Required | Default | Constraints                | Description                       |
|------------|--------|----------|---------|----------------------------|-----------------------------------|
| `name`     | string | yes      | —       | non-empty                  | Place name to search for          |
| `count`    | int    | no       | `10`    | `1 … 100`                  | Max number of results to return   |
| `language` | string | no       | `en`    | 2-letter code              | Result language (e.g. `it`, `de`) |

A missing or empty `name` is rejected with **HTTP 422** *before* any geocoding
call is made. A query with no match returns **`200 OK`** with an empty array.

#### Example request

```bash
curl "http://localhost:8000/search?name=Milan&count=5"
```

Results are language-sensitive: with the default `language=en`, *Milan, Italy*
is the top match for `Milan`; pass `&language=it` to favour the local spelling
(`Milano`).

#### Response

`200 OK`, `application/json`: an array of `Place` objects (ranked by relevance).

**`Place`**

| Field          | Type           | Description                                           |
|----------------|----------------|-------------------------------------------------------|
| `id`           | int \| null    | Open-Meteo geocoding id                               |
| `name`         | string         | Place name                                            |
| `latitude`     | number         | Latitude in decimal degrees                           |
| `longitude`    | number         | Longitude in decimal degrees                          |
| `country`      | string \| null | Country name                                          |
| `country_code` | string \| null | ISO country code                                      |
| `admin1`       | string \| null | First-level region (e.g. Lombardy)                    |
| `timezone`     | string \| null | IANA timezone                                         |
| `population`   | int \| null    | Population, when known                                |
| `elevation`    | number \| null | Elevation in metres                                   |

`latitude`/`longitude` feed straight into `GET /forecast`.

```json
[
  {
    "id": 3173435,
    "name": "Milan",
    "latitude": 45.46427,
    "longitude": 9.18951,
    "country": "Italy",
    "country_code": "IT",
    "admin1": "Lombardy",
    "timezone": "Europe/Rome",
    "population": 1236837,
    "elevation": 122.0
  }
]
```

### `GET /health`

Liveness/readiness probe. Returns `200 OK` with `{"status": "ok"}` and makes no
upstream calls — safe for container health checks and uptime monitors.

```bash
curl "http://localhost:8000/health"
```

## Errors

| Status | When                                                        | Body                              |
|--------|-------------------------------------------------------------|-----------------------------------|
| `422`  | Missing/non-numeric/out-of-range `lat`, `lon`, or `days`; empty `name` or out-of-range `count` | FastAPI validation error detail   |
| `5xx`  | Upstream Open-Meteo failure for a required (general/local) request, or a geocoding failure | Standard error response    |

The ensemble request is best-effort: if it fails, the forecast still returns and
confidence falls back to inter-model disagreement alone.

## Notes

- Open-Meteo requires **no API key** for non-commercial use; commercial use needs
  a key (see Open-Meteo's terms).
- To change models, variables, weighting, or the swappable local provider, edit
  `meteo_aggregator/config.py` — no API changes required. See the root
  [`README.md`](../README.md) for the relocation/swap instructions.
```
