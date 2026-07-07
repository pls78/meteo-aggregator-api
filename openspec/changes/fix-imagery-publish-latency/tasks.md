## 1. Fix

- [x] 1.1 Add `EUMETVIEW_LATENCY_MINUTES` (default 20) to config
- [x] 1.2 In `get_satellite_imagery`, clamp the snap target to
  `min(requested, now - latency)` before snapping and the archive check

## 2. Verify

- [x] 2.1 Unit tests: recent and future requests clamp to `<= now - latency`;
  historical requests unchanged (`pytest`, 61 passed)
- [x] 2.2 Live GetMap: all 10 configured layers return `200 image/png` at their
  provider-computed times (previously 502/ServiceException at the un-clamped time)
