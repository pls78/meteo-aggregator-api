## Why

The satellite overlay catalog leaned on single-channel/derived products and
carried a few near-duplicates. EUMETView exposes far more striking (and equally
keyless) RGB composite imagery from the new MTG satellite. Adding those and
pruning redundant layers makes the map more useful and much more spectacular, at
zero cost — the browser still fetches rendered WMS tiles directly from EUMETSAT.

## What Changes

- **Add** five RGB composite layers (verified to serve PNG tiles):
  - `mtg_fd:rgb_geocolour` — Geo Colour (true colour by day, IR/clouds by night;
    looks great 24/7)
  - `mtg_fd:rgb_dust` — Saharan dust (very relevant to Italy)
  - `mtg_fd:rgb_cloudphase` — ice vs. water cloud phase
  - `msg_fes:rgb_airmass` — air masses / jet streams
  - `msg_fes:rgb_convection` — storm potential
- **Remove** redundant near-duplicates, keeping the most informative of each:
  - `msg_fes:ir039` (IR 3.9 fog, 15-min full disk) — duplicate of the retained
    5-min rapid-scan `msg_rss:ir039_nrt`
  - `msg_fes:gii_kindex` and `msg_fes:gii_liftedindex` — two equivalent
    convective-instability indices; the storm theme is now carried by the more
    spectacular Convection RGB
- Config-only: the `/imagery` endpoint returns whatever `EUMETVIEW_LAYERS`
  contains, and the UI renders layers dynamically from that response — no code or
  UI change.

## Capabilities

### Modified Capabilities
- `satellite-imagery`: the layer catalog is curated to favour visually rich RGB
  composites and to avoid near-duplicate products.

## Impact

- **Config only:** `EUMETVIEW_LAYERS` in `meteo_aggregator/config.py`. No new
  dependencies, no credentials (EUMETView is keyless).
- **Docs:** update the layer table in `api/README.md` and the layer count/summary
  in the root `README.md`.
- **No breaking changes;** the response shape is unchanged. Tests are
  config-driven and reference only retained layers.
