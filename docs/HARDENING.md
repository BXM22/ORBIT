# ORBIT Hardening Roadmap

Nine steps that take the pipeline from "works on my laptop" to tested,
logged, and running in CI. Do them in order; each builds on the last.

Scope: **testing + CI** and **observability/data quality**. Airflow, dbt, and
the dashboard are separate roadmap items.

| # | Step | Main files |
|---|---|---|
| 1 | Replace `assert` with a real exception | `orbit/validate.py` |
| 2 | Add structured logging | `orbit/pipeline.py`, `extract.py`, `load.py` |
| 3 | Read the DSN from an environment variable | `orbit/config.py`, `.env.example` |
| 4 | Unit test `validate()` | `tests/conftest.py`, `tests/test_validate.py`, `pytest.ini` |
| 5 | Mock the HTTP call to test `extract()` | `tests/test_extract.py` |
| 6 | Mock the database to test `load()` | `tests/test_load.py` |
| 7 | One real integration test | `tests/test_integration_load.py` |
| 8 | GitHub Actions CI | `.github/workflows/ci.yml`, `requirements-dev.txt`, `ruff.toml` |
| 9 | Fix the cron "Operation not permitted" bug | macOS settings or `launchd` |

---

## 1. Replace `assert` with a real exception

**Why:** `assert` is skipped under `python -O` and only reports the first
failure.

**Do:** in `orbit/validate.py`, import `ValidationError` from
`orbit/exceptions.py`. Check latitude, longitude, and altitude with `if`
statements, collect every failure in a list, and raise one
`ValidationError` joining them all.

**Check:** validating `{'latitude': 999, 'longitude': 999, 'altitude': 400}`
raises a `ValidationError` that mentions both latitude and longitude.

## 2. Add structured logging

**Why:** a bare `print` can't tell you later whether last night's runs worked.

**Do:**
- In `orbit/pipeline.py`, call `logging.basicConfig(...)` inside `main()`, not
  at module level, so importing the package in tests doesn't reconfigure
  logging. Log to stdout only; `run.sh` already sends output to `pipeline.log`.
- Each module gets `log = logging.getLogger("orbit")`.
- `extract()`: `log.exception(...)` on HTTP failures.
- `load()`: log whether `cur.rowcount` was 1 (new row) or 0 (duplicate).
- `main()`: wrap extract, validate, load in `try/except ValidationError`, log
  the error, and `raise SystemExit(1)`. Replace the `print` with `log.info`.

**Check:** `python -m orbit.pipeline` prints timestamped `INFO` lines; a bad
reading logs an error and exits with status 1 instead of a traceback.

## 3. Read the DSN from an environment variable

**Why:** CI (Step 8) needs to point the pipeline at a different database
without editing code.

**Do:**
- In `orbit/config.py`: `load_dotenv()` first, then
  `DSN = os.environ.get("ORBIT_DSN", "<current default>")`.
- Add `python-dotenv` to `requirements.txt`.
- Commit `.env.example` with `ORBIT_DSN=...`; the real `.env` is gitignored.

**Check:** with no `.env` the pipeline still works (default). With
`ORBIT_DSN=postgresql://nope/nope` it fails to connect, proving the variable
is read.

## 4. Unit test `validate()`

**Why:** `validate()` has no I/O, so it's the easiest place to set up pytest.

**Do:**
- `tests/conftest.py`: a `sample_payload` fixture with a valid reading.
- `tests/test_validate.py`: one test that a valid reading passes, a
  parametrized test that each out-of-range field raises `ValidationError`,
  and one test that two bad fields both appear in the message.
- `pytest.ini` at the repo root with `pythonpath = .` (so tests can import
  `orbit`) and an `integration` marker for Step 7.

**Check:** `pytest tests/test_validate.py -v` passes instantly, with no
network or Docker.

## 5. Mock the HTTP call to test `extract()`

**Why:** unit tests shouldn't depend on the ISS API being up.

**Do:** in `tests/test_extract.py`, use `@patch("orbit.extract.requests.get")`.
Patch where the name is looked up (`orbit.extract`), not `requests.get`
globally. Test that the parsed JSON is returned and that it was called with
`(API, timeout=10)`, and that an `HTTPError` from `raise_for_status` is raised.

**Check:** `pytest tests/test_extract.py -v` passes with Wi-Fi off.

## 6. Mock the database to test `load()`

**Why:** same idea as Step 5, for Postgres.

**Do:** in `tests/test_load.py`, use `@patch("orbit.load.psycopg2.connect")`.
Because `load()` uses two `with` blocks, the cursor is
`mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value`.
Assert the SQL contains `ON CONFLICT` and the parameters match the payload.

**Check:** `pytest tests/test_load.py -v` passes with Docker stopped. If
`call_args` is `None`, you mocked the wrong level of the `with` chain.

## 7. One real integration test

**Why:** mocks can't prove the `ON CONFLICT` dedupe works in real Postgres.

**Do:** in `tests/test_integration_load.py`, mark the module
`pytest.mark.integration`. A fixture connects using `ORBIT_DSN`, runs
`sql/schema.sql`, and truncates the table. The test calls `load()` twice
with the same payload and asserts there is exactly one row.

**Run:** `docker compose up -d`, wait for `pg_isready`, then
`pytest -m integration -v`.

**Check:** it passes; then comment out the `ON CONFLICT` line in
`orbit/load.py` and confirm it fails with a `UniqueViolation`. Put the line
back.

## 8. GitHub Actions CI

**Why:** makes "all tests pass" true for every commit, not just your laptop.

**Do:**
- `requirements-dev.txt` with `pytest` and `ruff`; a `ruff.toml` (empty is
  fine).
- `.github/workflows/ci.yml` on push and pull request: an Ubuntu job with a
  `postgres:16` service (health-checked), `ORBIT_DSN` set, then: install
  requirements, `ruff check .`, apply `sql/schema.sql` with `psql`,
  `pytest -m "not integration"`, `pytest -m integration`.

**Check:** a PR goes green; deliberately breaking a test turns it red.

## 9. Fix the cron "Operation not permitted" bug

**Why:** scheduled runs fail with `Operation not permitted` in
`pipeline.log` / `check.log`. This is independent of Steps 1–8.

**Cause:** macOS privacy controls (TCC) block `cron` from reaching the
Docker socket. Confirm with
`sudo log show --predicate 'eventMessage contains "cron"' --last 1h`.

**Fix:** either give `/usr/sbin/cron` Full Disk Access (System Settings →
Privacy & Security), or switch to a `launchd` agent in
`~/Library/LaunchAgents/com.orbit.pipeline.plist`.

**Check:** after `./run.sh install`, the logs show `loaded ...` and `OK:`
lines with no errors.

---

## When you're done

- Tick the matching README roadmap items.
- Mention `.env` setup in the README and link to this file and
  `docs/SDLC.md`.
