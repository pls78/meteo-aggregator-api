## 1. Fix

- [x] 1.1 Apply publish latency per layer in `get_satellite_imagery` using
  `defn.get("latency_minutes", config.EUMETVIEW_LATENCY_MINUTES)`
- [x] 1.2 Set `latency_minutes: 2880` on the Sentinel-3 daily layer

## 2. Verify

- [x] 2.1 Unit test: the daily layer snaps ~48 h back (two full UTC days); other
  layers keep the global latency (`pytest`, 18 eumetview tests pass)
- [x] 2.2 Live GetMap over Europe at the provider's Sentinel-3 time returns full
  coverage (~500 KB vs ~116 KB partial before)
