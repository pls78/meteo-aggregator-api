## Context

EUMETView (`view.eumetsat.int`) is EUMETSAT's public satellite visualization service,
backed by a standard OGC GeoServer. It exposes WMS, WCS, and WFS — no API key,
no authentication, fees: "none", access constraints: "none". The WMS is queried
with `GetMap?layers=<name>&TIME=<ISO>&bbox=...&crs=...&format=...` and returns
imagery in PNG, GeoTIFF, or other formats.

This change adds a satellite-imagery companion to the forecast: given a location
and time, return a URL (or image) for each selected layer that the caller can
display alongside the numerical forecast.

WMS endpoint: `https://view.eumetsat.int/geoserver/wms`

---

## Layer Catalog and Purpose

The following layers were selected after reviewing the full WMS capabilities
document. Each entry explains what the layer measures and what it is practically
useful for.

### `mtg_fd:ir105_hrfi` — MTG Infrared 10.5 µm (primary cloud imagery)
**What it is:** Thermal infrared radiation emitted by the top of the atmosphere.
Cold surfaces (high cloud tops) appear bright; warm surfaces (land, sea, clear
sky) appear dark. Measured by the FCI (Flexible Combined Imager) on the
Meteosat Third Generation satellite.

**What it shows:** Cloud location, extent, and approximate altitude at all times
of day and night. A deep convective storm will have a very cold, very bright
cloud top; thin cirrus will be slightly bright; fog/low cloud over the Po Valley
may be faintly visible.

**Why this one:** Highest spatial resolution (~1 km) and cadence (10-minute) of
any geostationary IR layer available. Available from September 2024.

**Cadence:** 10 min. **Archive from:** 2024-09-23.

---

### `msg_fes:clm` — Cloud Mask (MSG, 0°)
**What it is:** A per-pixel classification derived from multiple SEVIRI channels.
Each pixel is labeled: clear / probably clear / probably cloudy / cloudy.

**What it shows:** A clean binary (or four-class) map of where there is cloud
cover right now. Unlike the IR imagery it is a *decision*, not a raw measurement
— easier to use programmatically (e.g. "is Lombardy currently cloudy?").

**Why this one:** No MTG cloud-mask layer is yet available in EUMETView; the MSG
cloud mask fills that role. Complements `mtg_fd:ir105_hrfi` visually with a
clean classified product.

**Cadence:** 15 min. **Archive from:** 2020-09-01.

---

### `msg_fes:ir039` — SEVIRI IR 3.9 µm (fog & low cloud)
**What it is:** A shorter-wavelength infrared channel sensitive to both emitted
heat and reflected sunlight. At this wavelength, very small water droplets (as
in fog and low stratus clouds) have a distinctly different signal than larger
ice-crystal cirrus clouds or clear sky.

**What it shows:**
- **At night:** Fog, low stratus, and shallow cloud layers that are nearly
  invisible in IR 10.5/10.8 become clearly distinguishable.
- **During the day:** Sunglint off smooth cloud tops adds to the signal; combined
  with the night product, it produces a near-continuous fog/low-cloud detection.

**Why this one:** The Po Valley is one of Europe's most fog-prone regions.
`mtg_fd:ir105_hrfi` does not yet have an IR 3.9 equivalent in EUMETView, so
MSG fills this niche. Pairs naturally with `msg_fes:clm`.

**Cadence:** 15 min. **Archive from:** 2020-09-01.

---

### `msg_rss:ir039_nrt` — Rapid Scan IR 3.9 µm (Europe, near-real-time)
**What it is:** The same IR 3.9 µm channel as `msg_fes:ir039`, but from the
Rapid Scan Service slot — a dedicated mode covering Europe at **5-minute**
cadence instead of 15 minutes.

**What it shows:** Same fog/low-cloud detection as `msg_fes:ir039`, but faster.
At 5-minute intervals, fast-evolving fog banks or convective initiation over the
Alps are resolved much better.

**Why this one:** Higher temporal resolution is valuable for near-real-time
display alongside a forecast. The geographic focus on Europe makes it appropriate
for an Italy-centric service.

**Cadence:** 5 min. **Archive from:** 2020-02-12.

---

### `msg_fes:gii_kindex` — K-Index instability (MSG, 0°)
**What it is:** A scalar instability index computed from the temperature and
humidity profile of the atmosphere at several altitude levels. Named after the
meteorologist who defined it. Delivered on the same 15-minute MSG grid.

**What it shows:** A map of thunderstorm risk:
- K-Index < 20: little or no risk
- 20–30: moderate risk
- > 30: high risk of severe thunderstorms, hail, and heavy rain

**Why this one:** A concise single-number readout of convective risk over the
domain — a useful complement to the `precipitation_probability_*` and
`weather_code` values in the forecast payload.

**Cadence:** 15 min. **Archive from:** 2021-06-06.

---

### `msg_fes:gii_liftedindex` — Lifted Index instability (MSG, 0°)
**What it is:** Another atmospheric instability index, complementary to K-Index.
It compares the temperature of a hypothetically lifted air parcel to the
surrounding atmosphere at altitude. A *negative* value means the parcel is
warmer than its environment and will keep rising — an unstable atmosphere.

**What it shows:** Instability severity:
- Positive: stable, no convection
- 0 to −2: marginally unstable
- < −6: extremely unstable, severe weather likely

**Why this one:** K-Index and Lifted Index are physically complementary — K-Index
is better for assessing moisture availability, Lifted Index for parcel
buoyancy. Together they give a more robust picture of convective potential than
either alone.

**Cadence:** 15 min. **Archive from:** 2021-06-06.

---

### `mtg_fd:li_afa` — Lightning Imager Accumulated Flash Area (MTG)
**What it is:** A unique MTG capability: an optical detector that counts lightning
flashes from geostationary orbit. AFA = Accumulated Flash Area — areas where one
or more lightning flashes were detected, accumulated over a 5-minute window.

**What it shows:** Where active thunderstorms are producing lightning right now.
No other geostationary satellite over Europe had this capability before MTG.
A cluster of flash areas over the Alps or Apennines immediately indicates a
severe convective cell — something the IR imagery hints at through cold cloud tops
but the lightning layer confirms directly.

**Why this one:** Directly complements the instability indices (K-Index,
Lifted-Index) — the indices say *risk*, the lightning layer says *it's happening*.
Together they give a nowcast picture of convective activity that contextualises
the forecast's `weather_code` and `precipitation_probability_*` values.

**Cadence:** 5 min. **Archive from:** 2025-05-30.

---

### `copernicus:daily_sentinel3ab_olci_l1_rgb_fulres` — True-colour RGB (Sentinel-3)
**What it is:** A natural-colour (true-colour) composite image from the OLCI
instrument on Sentinel-3 A/B, assembled from the day's orbital passes into a
daily mosaic. Resolution: ~300 m. Sentinel-3 is polar-orbiting, so it revisits
any given location 1–2× per day.

**What it shows:** What the scene looks like in visible light — cloud texture,
snow cover, vegetation, smoke, dust plumes, urban areas. The highest-resolution
"photograph-like" view of the region available in EUMETView.

**Why this one:** Useful for a daily context image and for spotting
high-resolution features invisible to MSG/MTG (individual cloud cells, snow-line
altitude over the Alps, wildfire smoke). Not real-time, but rich in detail.

**Cadence:** ~1h41m (orbital, one pass per day for a given location). **Archive
from:** 2020-02-17.

---

## Layers Explicitly Excluded

| Layer | Reason for exclusion |
|---|---|
| `msg_fes:ir108` | **Superseded by `mtg_fd:ir105_hrfi`** for current data. MTG offers ~1 km vs ~3 km resolution and 10-min vs 15-min cadence. The wavelengths (10.8 vs 10.5 µm) are meteorologically equivalent. MSG IR 10.8 remains available as an **archive fallback** for dates before MTG's September 2024 start, but is not a primary layer. |
| `msg_fes:cth` | Cloud Top Height requires understanding of the vertical temperature profile to interpret; the simpler cloud mask + IR imagery convey enough information for the intended use case. |
| `msg_fes:fire` | Active fire monitoring is out of scope for a general weather service. |
| `msg_fes:h60b` / `msg_iodc:h63` | Blended precipitation estimate. Useful for ground-truth verification but adds complexity; precipitation probability is already in the forecast payload. |
| `copernicus:…_olci_l2_chl` | Ocean chlorophyll — irrelevant to an Italy/land weather service. |
| `copernicus:…_slstr_l2p_sst` | Sea surface temperature — out of scope. |
| `eps:m0x_ascat_wind` | Coastal wind scatterometry — marine use, out of scope. |
| `eps:m0x_ir108` / `eps:m0x_rgb_*` | MetOp AVHRR is lower-quality than MSG/MTG for this use case and polar-orbit swath coverage is patchy over a single location. |
| `msg_iodc:*` | Indian Ocean slot — irrelevant to Italy. |

---

## Design Decisions

### 1. WMS parameters, not a baked GetMap URL
The provider returns **WMS endpoint + layer parameters** (endpoint, layer name,
snapped TIME, format, CRS) rather than a fully-assembled `GetMap` URL with a
baked-in bbox. The caller — a map library (Leaflet, MapLibre) on web or iOS —
registers these as a WMS layer and handles tiling, zoom, and bbox itself.

This avoids bbox arithmetic on the server (what buffer radius? what pixel size?),
works at any zoom level, and matches exactly how WMS clients are designed to
consume this kind of service. The server never proxies image bytes.

Example output per layer:
```json
{
  "wms_url": "https://view.eumetsat.int/geoserver/wms",
  "layer": "mtg_fd:ir105_hrfi",
  "time": "2026-06-20T14:00:00Z",
  "crs": "EPSG:3857",
  "format": "image/png"
}
```

### 2. TIME parameter alignment
WMS imagery must be requested at a time that actually exists in the layer's
archive. The provider will snap the requested datetime to the nearest available
slot (e.g. floor to the nearest 15-minute boundary for MSG layers, 10-minute for
MTG). If no TIME is provided, the WMS returns the most recent available image.

### 3. MTG vs MSG for IR imagery
`mtg_fd:ir105_hrfi` is the **primary IR cloud layer**. `msg_fes:ir108` is not
included in the standard layer set because MTG supersedes it for all dates from
September 2024 onward. If historical imagery before that date is ever needed, the
caller can request `msg_fes:ir108` directly.

### 2. Format is always PNG
PNG is mandatory for map overlays — JPEG has no transparency support, so it
renders as an opaque white rectangle on top of the base map instead of a
see-through overlay. GeoTIFF is not browser/app-renderable directly. PNG is
therefore the format for all layers regardless of content type.

### 3. CRS is EPSG:3857 (Web Mercator)
The standard CRS for web and mobile map libraries (Leaflet, MapLibre, Apple
MapKit). All selected layers support it per the WMS capabilities document.

### 4. Archive start dates vary
Each layer has a different archive start date (earliest: MSG RSS from 2020-02-12;
latest: MTG LI from 2025-05-30). The provider should handle requests before a
layer's archive start gracefully (the WMS will return an error; the provider
should surface this cleanly rather than silently returning a blank response).

## Resolved

- **`mtg_fd:li_afa` included.** Lightning flash area is meteorologically unique
  (no MSG equivalent) and pairs well with the instability indices — indices show
  risk, lightning confirms it is happening.
- **BBox strategy: none.** The provider returns WMS parameters, not a baked
  `GetMap` URL. The map library (Leaflet, MapLibre) handles bbox, tiling, and
  zoom. This is the intended WMS consumption pattern.
- **Format: always PNG.** Required for map overlays; JPEG has no transparency
  and would obscure the base map. GeoTIFF is not directly renderable in
  browser/app contexts.
