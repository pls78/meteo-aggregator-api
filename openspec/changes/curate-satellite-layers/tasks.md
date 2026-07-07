## 1. Config

- [x] 1.1 Add the five RGB composite layers to `EUMETVIEW_LAYERS` with correct
  cadence and archive-start dates
- [x] 1.2 Remove the redundant `msg_fes:ir039`, `msg_fes:gii_kindex`, and
  `msg_fes:gii_liftedindex` layers

## 2. Verify

- [x] 2.1 `pytest tests/test_eumetview.py` passes (config-driven)
- [x] 2.2 The five new layers serve PNG tiles from the EUMETView WMS (GetMap 200,
  `image/png`)

## 3. Docs

- [x] 3.1 Update the configured-layers table in `api/README.md`
- [x] 3.2 Update the layer count/summary in the root `README.md`
