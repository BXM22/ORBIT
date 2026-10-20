# Testing

ORBIT has two kinds of tests. Both use `pytest`.

| Kind | Needs | Files | Speed |
|------|-------|-------|-------|
| Unit | nothing (no network, no Docker) | `test_validate.py`, `test_extract.py`, `test_load.py`, `test_pipeline.py` | ~0.1s |
| Integration | Postgres from `docker compose up -d` | `test_integration_load.py` | ~0.3s |

## Running

```bash
pip install -r requirements-dev.txt     # adds pytest on top of requirements.txt

pytest                                  # unit tests only (default)
pytest -m integration                   # integration tests only (needs the db)
pytest -m "integration or not integration"   # everything
pytest tests/test_validate.py -v        # one file
```

Plain `pytest` skips integration tests because `pytest.ini` sets
`addopts = -m "not integration"`. That keeps the everyday loop fast and
independent of Docker. Passing your own `-m` overrides it.

## Configuration

`pytest.ini`:
- `pythonpath = .` lets tests `import orbit` when run from the repo root.
- Registers the `integration` marker so pytest doesn't warn about it.

`tests/conftest.py` provides the `sample_payload` fixture, a known-good reading
in the API's shape. Tests that need a bad value copy-modify it, e.g.
`sample_payload["latitude"] = 91`.

## What each file covers

**`test_validate.py`** — `validate()` is pure, so it is tested directly.
- A nominal reading passes.
- Each field just outside its range is rejected (lat ±91, lon ±181, alt 299/501).
- Boundary values (lat ±90, lon ±180, alt 300/500) are accepted, which pins
  the `<=` comparisons.
- Several bad fields produce one error naming all of them.

**`test_extract.py`** — `requests.get` is patched at `orbit.extract.requests.get`.
Patch the name where it is *looked up*, not where it is defined.
- The parsed JSON is returned and `get` is called with `(API, timeout=10)`.
- An HTTP error propagates.
- A failure logs `"API request failed"` (checked with pytest's `caplog`).

**`test_load.py`** — `psycopg2.connect` is patched. `load()` uses
`with connect() as conn, conn.cursor() as cur`, so the cursor is reached via
`connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value`
(the `_mock_cursor` helper).
- The `INSERT` contains `ON CONFLICT` and receives the right parameters, in order.
- `rowcount == 1` logs `inserted new row`; `rowcount == 0` logs `duplicate reading`.

**`test_pipeline.py`** — `extract`, `validate`, `load` are patched in `orbit.pipeline`.
- Happy path: validate and load receive the extracted payload.
- A `ValidationError` makes `main()` exit with code 1 and `load` is never called.

**`test_integration_load.py`** — runs real SQL.
- Calling `load()` twice with the same timestamp leaves exactly one row.
- It uses a separate `iss_test` database, created on demand, and points
  `orbit.load.DSN` at it with `monkeypatch`. **Your real `iss` data is never
  touched.** (An earlier draft in the roadmap truncated `raw_iss_positions`
  directly, which would have wiped real readings.)

## Proving the integration test works

A test that can't fail proves nothing. Temporarily delete the
`ON CONFLICT (observed_at) DO NOTHING` line in `orbit/load.py` and run
`pytest -m integration`. It should fail with `UniqueViolation`. Restore the line.
This was done when the suite was written.

## Adding a test

1. Put it in `tests/test_<module>.py`.
2. Use `sample_payload` rather than rebuilding a dict.
3. If it needs a real database, add `pytestmark = pytest.mark.integration`.
4. Never hit the real API or the real `iss` database from a unit test.

## Not yet covered

- `./run.sh` (shell script) has no tests.
- CI: the suite is not run automatically yet (roadmap Step 8).
- `DSN` is still hardcoded in `orbit/config.py` (roadmap Step 3); the
  integration test overrides it by patching `orbit.load.DSN`.
