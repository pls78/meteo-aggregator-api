# Meteo-Aggregator

Accurate local 7-day forecasts by aggregating multiple weather models. No single
source is best across all lead times — high-resolution regional models win the
near term (days 1–3), ECMWF wins at range, and far-out days are inherently
probabilistic. This service blends them into one consensus forecast and reports
how much to trust each day.

It is a **library core** (`meteo_aggregator/`) plus a **thin FastAPI layer**
(`api/`), so the same backend can serve a future web app and an iOS app.

## How it works

- **General provider** — global models (ECMWF, GFS, ICON) fetched together from
  the [Open-Meteo Forecast API](https://open-meteo.com/en/docs) in one keyless
  call, up to a 16-day horizon.
- **Specialized-local provider** — a high-resolution regional model
  (default: ItaliaMeteo-ARPAE **ICON-2i**, ~2 km, Italy-wide, ~3-day horizon)
  via Open-Meteo.
- **Aggregation** — a lead-time-weighted consensus (local high-res favored
  days 1–3, ECMWF at range) with a per-day **confidence** (level + numeric
  range) derived from inter-model disagreement and Open-Meteo
  [ensemble](https://open-meteo.com/en/docs/ensemble-api) spread. The full
  per-model breakdown is always returned alongside the headline.

Each day reports 16 daily variables (temperature, apparent temperature,
precipitation, wind, cloud cover, humidity, UV, daylight, sunrise/sunset,
weather code). Numeric variables are weight-blended; `sunrise`, `sunset`, and
`weather_code` are non-blendable and take the highest-weighted model's value.
See [`api/README.md`](api/README.md) for the full HTTP request/response
reference and the variable list with units.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run the API

```bash
uvicorn api.main:app --reload
# then:
curl "http://localhost:8000/forecast?lat=45.5&lon=9.5&days=7"
```

Each day in the response carries `values` (consensus per variable), a
`confidence` (`level` + `low`/`high`/`spread`), and a `breakdown` (each
contributing model with its values). ICON-2i appears in the near-term days and
drops out beyond its horizon.

## Live satellite imagery

`GET /imagery` returns WMS parameters for eight EUMETSAT EUMETView layers
(MTG infrared, MTG lightning, MSG cloud mask, MSG fog detection, MSG instability
indices, Sentinel-3 true-colour RGB) ready to pass directly to a map library:

```bash
curl "http://localhost:8000/imagery?time=2026-06-20T12:00:00Z"
```

Each entry in `layers` carries `wms_url`, `layer`, `time` (snapped to the
layer's cadence), `crs`, and `format`. In Leaflet:

```js
L.tileLayer.wms(layer.wms_url, {
  layers: layer.layer,
  time: layer.time,
  format: layer.format,
  crs: L.CRS.EPSG3857,
  transparent: true,
}).addTo(map);
```

No image bytes flow through this service — the map client fetches tiles directly
from EUMETSAT (keyless, non-commercial). See [`api/README.md`](api/README.md)
for the full layer list and field reference.

As a library:

```python
from meteo_aggregator import get_satellite_imagery
imagery = get_satellite_imagery()  # defaults to now
for layer in imagery.layers:
    print(layer.layer, layer.time)
```

## Find coordinates by name

Don't know the coordinates? Search by place name and feed a result into
`/forecast`:

```bash
curl "http://localhost:8000/search?name=Milan"
# -> [{ "name": "Milan", "latitude": 45.46, "longitude": 9.19, "country": "Italy", ... }, ...]
curl "http://localhost:8000/forecast?lat=45.46&lon=9.19&days=7"
```

`/search` is backed by the keyless Open-Meteo Geocoding API and returns a ranked
list of matching places (no match → `[]`). Results are language-sensitive — pass
`&language=it` to favour Italian names (`Milano`). See
[`api/README.md`](api/README.md) for the full `Place` field list.

## Use as a library

```python
import asyncio
from meteo_aggregator import get_forecast, search_locations
from meteo_aggregator.models import Location

forecast = asyncio.run(get_forecast(Location(latitude=45.5, longitude=9.5), days=7))

# Or resolve a name first, then forecast on the top match:
places = asyncio.run(search_locations("Milan"))
forecast = asyncio.run(get_forecast(places[0].to_location(), days=7))
```

## Relocating (swap the local model)

The local slot is config-selected, so moving regions is a configuration change,
not a code change. ICON-2i already covers all of Italy (so Lombardy → Toscana
needs nothing), but to point the local provider at a different high-res model
edit `LOCAL_MODEL` in `meteo_aggregator/config.py`:

```python
LOCAL_MODEL = "italia_meteo_arpae_icon_2i"  # -> any Open-Meteo model id
```

or pass `model=` when constructing `OpenMeteoLocalProvider`. Weighting and
confidence thresholds are also in `config.py`.

## Tests

```bash
pytest                 # offline; mocks Open-Meteo with respx
METEO_LIVE=1 pytest    # also runs the live integration test (hits the network)
```
