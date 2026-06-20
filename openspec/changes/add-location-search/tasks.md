## 1. Config

- [x] 1.1 Add geocoding settings to `config.py`: `GEOCODING_URL`,
  `GEOCODING_DEFAULT_COUNT`, `GEOCODING_MAX_COUNT`, `GEOCODING_LANGUAGE`

## 2. Domain model

- [x] 2.1 Add a `Place` pydantic model to `models.py` (`id`, `name`, `latitude`,
  `longitude`, optional `country`, `country_code`, `admin1`, `timezone`,
  `population`, `elevation`)

## 3. Provider

- [x] 3.1 Implement `providers/geocoding.py`: `search_places(client, query, *,
  count, language) -> list[Place]`; parse `results`, skip rows missing lat/lon,
  return `[]` on no match

## 4. Client facade

- [x] 4.1 Add `search_locations(query, *, count, language, http_client=None)` to
  `client.py`; export `search_locations` and `Place` from `__init__.py`

## 5. HTTP layer

- [x] 5.1 Add `GET /search?name&count&language` to `api/main.py` delegating to
  `search_locations`; reject empty `name` (HTTP 422) before any network call;
  bound `count` to `1..GEOCODING_MAX_COUNT`

## 6. Tests

- [x] 6.1 `respx`-mocked provider tests: parse a multi-result payload; missing
  `results` key ⇒ `[]`
- [x] 6.2 API endpoint tests with a mocked client: success returns the list;
  empty `name` ⇒ 422 and the client is not called
- [x] 6.3 Network-gated/skippable live integration test for a real place

## 7. Docs

- [x] 7.1 Document `/search` in `api/README.md` (params, `Place` fields, example)
  and add a short "find coordinates by name" section to the root `README.md`
