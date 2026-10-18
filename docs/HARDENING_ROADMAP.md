# ORBIT Hardening Roadmap — a step-by-step tutorial

This is a guided exercise, not a diff to copy-paste. Work through the steps
in order — each one builds on the last (you genuinely can't write a good
test for `validate()` until Step 1 is done, because bare `assert` is
basically untestable). Each step says what to change, why, shows a worked
example, and gives you a quick check before moving on.

Scope for this roadmap: **testing + CI** and **observability/data quality**.
Airflow orchestration, dbt models, and a dashboard are intentionally *not*
covered here — they're later roadmap items in the README.

---

## Step 1 — Replace bare `assert` with a real exception

**Why:** `assert` statements vanish entirely when Python runs with `-O`, and
an `AssertionError` only ever carries the *first* failing condition. Neither
property is what you want from input validation in a pipeline.

**What to change:** create a new file, `exceptions.py`, holding just the
custom exception. Keeping it out of `pipeline.py` means anything that needs
to catch or raise `ValidationError` later (a test, a future second pipeline
module, a dbt/Airflow task) imports a small standalone module instead of
pulling in `pipeline.py`'s HTTP/DB dependencies along with it — and it keeps
`pipeline.py` focused on *behavior* rather than also defining types.

```python
# exceptions.py
class ValidationError(ValueError):
    """Raised when an ISS position reading fails a sanity check."""
```

Then in `pipeline.py`, import it and rewrite `validate()` to collect
*every* failing field, not just the first:

```python
# pipeline.py
from exceptions import ValidationError

def validate(p: dict) -> None:
    errors = []
    if not (-90 <= p["latitude"] <= 90):
        errors.append(f"latitude out of range: {p['latitude']}")
    if not (-180 <= p["longitude"] <= 180):
        errors.append(f"longitude out of range: {p['longitude']}")
    if not (300 <= p["altitude"] <= 500):
        errors.append(f"altitude out of range: {p['altitude']}")
    if errors:
        raise ValidationError("; ".join(errors))
```

This is a one-file exception, not a package — no `exceptions/` directory or
`__init__.py` needed yet. If a second exception type shows up later (e.g. a
`StaleDataError` for the freshness check), that's the natural point to
reconsider, not before.

**Check your work:** run `python -c "from pipeline import validate; validate({'latitude': 999, 'longitude': 999, 'altitude': 400})"` and confirm you get a `ValidationError` whose message mentions *both* latitude and longitude, not just the first bad field. Also run `python -c "from exceptions import ValidationError; print(ValidationError)"` on its own to confirm `exceptions.py` is importable independent of `pipeline.py`.

---

## Step 2 — Add structured logging

**Why:** right now, success is a bare `print()` and failure is either an
uncaught exception or (soon) a swallowed `ValidationError`. You want a log
you can actually read after the fact to answer "did last night's run work?"

**What to change:** add `logging` setup near the top of `pipeline.py`, and
replace the final `print` with a log call. Log to stdout/stderr only — don't
add a `FileHandler`. `run.sh` already redirects cron output into
`pipeline.log` via `>> pipeline.log 2>&1`; if `pipeline.py` also wrote to
that file directly, you'd get everything twice. Keeping `pipeline.py`
agnostic about where it logs also matters once you add CI (Step 8) — you
don't want a test run leaving a `pipeline.log` file inside the CI runner.

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("orbit")
```

Then in each function:
- `extract()`: on failure (timeout, bad HTTP status), log at `ERROR` with
  `log.exception(...)` so the traceback is captured, before re-raising or
  letting it propagate.
- `load()`: after the `INSERT`, check `cur.rowcount` — `0` means the row
  already existed (dedupe no-op), `1` means a new row landed. Log which one
  happened at `INFO`. This is a real data-quality signal worth having.
- `__main__`: wrap the `extract → validate → load` sequence in a
  `try/except ValidationError`, log the error, and exit non-zero — no raw
  traceback for an *expected* condition like a bad reading.

```python
if __name__ == "__main__":
    try:
        payload = extract()
        validate(payload)
        load(payload)
        log.info("loaded %s", payload["timestamp"])
    except ValidationError as e:
        log.error("rejected reading: %s", e)
        raise SystemExit(1)
```

**Check your work:** run `python pipeline.py` manually and confirm you see
timestamped `INFO` log lines instead of a bare `loaded ...` print. Then
temporarily hardcode a bad payload into `validate()`'s caller to confirm a
`ValidationError` logs cleanly and exits with status 1 (check with
`echo $?`) instead of dumping a traceback.

---

## Step 3 — Move the DB connection string into an environment variable

**Why:** a hardcoded DSN (`postgresql://postgres:postgres@localhost:5432/iss`)
means you can't point the pipeline at a different database (e.g. the one
GitHub Actions spins up in Step 8) without editing source code.

**What to change:**

```python
import os
DSN = os.environ.get("ORBIT_DSN", "postgresql://postgres:postgres@localhost:5432/iss")
```

Add `python-dotenv` to `requirements.txt` so you can keep a local `.env`
file instead of exporting the variable by hand every session:

```python
from dotenv import load_dotenv
load_dotenv()  # no-op if .env doesn't exist
```

Create `.env.example` at the repo root (this one *is* committed — it's just
a template, not a secret):

```
ORBIT_DSN=postgresql://postgres:postgres@localhost:5432/iss
```

`.env` itself is already in `.gitignore`, so you're safe to create a real
`.env` locally without accidentally committing it.

**Check your work:** delete your local `.env` (or rename it), run
`python pipeline.py`, and confirm it still works using the fallback default.
Then set `ORBIT_DSN` to something obviously wrong
(`ORBIT_DSN=postgresql://nope/nope python pipeline.py`) and confirm it now
fails to connect — proving the env var is actually being read.

---

## Step 4 — Write your first unit test: `validate()`

**Why:** `validate()` is pure (no I/O), which makes it the easiest possible
place to start testing. This step is really about getting `pytest` set up
and proving the harness works before tackling anything that needs mocking.

**What to create:** `tests/conftest.py` with a fixture for a known-good
reading, and `tests/test_validate.py`.

```python
# tests/conftest.py
import pytest

@pytest.fixture
def sample_payload():
    return {"latitude": 10.0, "longitude": 20.0, "altitude": 400.0,
            "velocity": 7660.0, "timestamp": 1700000000}
```

```python
# tests/test_validate.py
import pytest
from pipeline import validate
from exceptions import ValidationError

def test_validate_accepts_nominal_reading(sample_payload):
    validate(sample_payload)  # should not raise

@pytest.mark.parametrize("field,bad_value", [
    ("latitude", 91), ("latitude", -91),
    ("longitude", 181), ("longitude", -181),
    ("altitude", 299), ("altitude", 501),
])
def test_validate_rejects_out_of_range(sample_payload, field, bad_value):
    sample_payload[field] = bad_value
    with pytest.raises(ValidationError):
        validate(sample_payload)

def test_validate_collects_multiple_errors(sample_payload):
    sample_payload["latitude"] = 999
    sample_payload["longitude"] = 999
    with pytest.raises(ValidationError) as exc:
        validate(sample_payload)
    assert "latitude" in str(exc.value)
    assert "longitude" in str(exc.value)
```

You'll also want a `pytest.ini` at the repo root so later steps can register
the `integration` marker without warnings:

```ini
[pytest]
markers =
    integration: requires a live Postgres (docker-compose db service)
```

**Check your work:** `pip install pytest` then `pytest tests/test_validate.py -v` — all cases should pass, and this should run instantly with no network or Docker involved.

---

## Step 5 — Mock `requests.get` to test `extract()`

**Why:** `extract()` makes a real HTTP call. A unit test should never
actually hit the network — it should be fast, deterministic, and not fail
just because the ISS API is briefly down.

**What to create:** `tests/test_extract.py`, patching `requests.get` inside
the `pipeline` module's namespace (important: patch `pipeline.requests.get`,
not `requests.get` globally, since `pipeline.py` imported `requests` into
its own namespace).

```python
# tests/test_extract.py
from unittest.mock import patch
import pytest
import requests
from pipeline import extract, API

@patch("pipeline.requests.get")
def test_extract_returns_parsed_json(mock_get):
    mock_get.return_value.json.return_value = {
        "latitude": 1, "longitude": 2, "altitude": 400,
        "velocity": 7000, "timestamp": 123,
    }
    mock_get.return_value.raise_for_status.return_value = None

    result = extract()

    assert result["latitude"] == 1
    mock_get.assert_called_once_with(API, timeout=10)

@patch("pipeline.requests.get")
def test_extract_raises_on_http_error(mock_get):
    mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("500")
    with pytest.raises(requests.HTTPError):
        extract()
```

**Check your work:** `pytest tests/test_extract.py -v`. Confirm it passes with your Wi-Fi off — if it still passes offline, you know the mock is actually being used instead of a real network call.

---

## Step 6 — Mock `psycopg2` to test `load()`

**Why:** same idea as Step 5, but for the database. This is the trickiest
mock in the project because `load()` chains two `with` statements
(`with psycopg2.connect(DSN) as conn, conn.cursor() as cur:`), so you need to
wire up the mock's `__enter__` return values correctly or the test will
silently check the wrong object.

**What to create:** `tests/test_load.py`.

```python
# tests/test_load.py
from unittest.mock import patch
from pipeline import load

@patch("pipeline.psycopg2.connect")
def test_load_executes_insert_with_expected_params(mock_connect, sample_payload):
    mock_conn = mock_connect.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value

    load(sample_payload)

    args, _ = mock_cursor.execute.call_args
    sql, params = args
    assert "ON CONFLICT" in sql
    assert params == (
        sample_payload["timestamp"], sample_payload["latitude"],
        sample_payload["longitude"], sample_payload["altitude"],
        sample_payload["velocity"],
    )
```

If this test fails in a confusing way (e.g. `call_args` is `None`), the
most common cause is mocking the wrong level of the `with` chain — double
check `connect(...).__enter__()` vs. just `connect(...)`.

**Check your work:** `pytest tests/test_load.py -v` — green, with zero Docker/Postgres running. Stop your `docker compose` service entirely and confirm the test still passes, proving it's not secretly hitting a real DB.

---

## Step 7 — Write one real integration test

**Why:** mocks prove your code *calls the right functions with the right
arguments* — they can't prove the SQL actually behaves correctly against a
real database. The `ON CONFLICT (observed_at) DO NOTHING` dedupe logic is
exactly the kind of thing that looks right but needs to be proven against
real Postgres.

**What to create:** `tests/test_integration_load.py`, marked so it doesn't
run as part of your fast unit-test loop.

```python
# tests/test_integration_load.py
import os
import pytest
import psycopg2
from pathlib import Path
from pipeline import load

pytestmark = pytest.mark.integration

@pytest.fixture
def pg_conn():
    dsn = os.environ.get("ORBIT_DSN", "postgresql://postgres:postgres@localhost:5432/iss")
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(Path("sql/schema.sql").read_text())
        cur.execute("TRUNCATE raw_iss_positions")
    conn.commit()
    yield conn
    conn.close()

def test_load_is_idempotent_on_conflict(pg_conn, sample_payload):
    load(sample_payload)
    load(sample_payload)  # same observed_at, called twice

    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM raw_iss_positions WHERE observed_at = to_timestamp(%s)",
            (sample_payload["timestamp"],),
        )
        assert cur.fetchone()[0] == 1
```

Run it locally like this:

```bash
docker compose up -d
until docker compose exec -T db pg_isready -U postgres -d iss; do sleep 1; done
ORBIT_DSN=postgresql://postgres:postgres@localhost:5432/iss pytest -m integration -v
```

**Check your work:** confirm the test passes, then comment out the
`ON CONFLICT (observed_at) DO NOTHING` clause in `schema.sql` temporarily,
re-apply the schema, and re-run the test — it should now *fail* (count == 2),
proving the test is actually exercising the dedupe behavior rather than
trivially passing.

---

## Step 8 — Wire up GitHub Actions CI

**Why:** tests that only run on your laptop don't actually guarantee
anything about the next commit. CI makes "all tests pass" a property of the
repository, not just your local machine's current state.

**What to create:** `requirements-dev.txt`:

```
pytest
ruff
```

And `.github/workflows/ci.yml`:

```yaml
name: CI
on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: iss
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      ORBIT_DSN: postgresql://postgres:postgres@localhost:5432/iss
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - name: Apply schema
        run: psql "$ORBIT_DSN" -f sql/schema.sql
      - run: pytest -m "not integration" --tb=short
      - run: pytest -m integration --tb=short
```

You'll also want a minimal `ruff.toml` (an empty one is fine to start —
`ruff check .` will use sane defaults) to catch things like unused imports.

**Check your work:** push a branch, open a PR against `master`, and watch
the Actions tab. All three steps (lint, unit tests, integration tests)
should go green. Then deliberately break something (e.g. reintroduce a bare
`assert`, or remove `mock_get.assert_called_once_with`'s expected arg) and
confirm CI actually turns red — a CI pipeline that can't fail isn't testing
anything.

---

## Step 9 — Diagnose and fix the cron "Operation not permitted" bug

**Why:** `pipeline.log`/`check.log` currently show repeated
`bash: .../run.sh: Operation not permitted` errors when cron fires. This is
a live, real bug independent of everything above — CI doesn't exercise cron
at all (it calls `run.sh check` / `pipeline.py` directly), so it's safe to
tackle this step in parallel or after the testing work, not blocking it.

**Likely cause:** "Operation not permitted" (as opposed to "Permission
denied") is the signature of macOS's TCC (Transparency, Consent, and
Control) privacy system blocking `cron` from reaching resources outside its
sandbox — in this case, almost certainly the Docker socket that
`docker compose` needs.

**How to confirm:** after a scheduled cron firing, run:

```bash
sudo log show --predicate 'eventMessage contains "cron"' --last 1h
```

and look for TCC-related denials around the time of the failure.

**Fix options:**
1. **Full Disk Access for cron** — System Settings → Privacy & Security →
   Full Disk Access → add `/usr/sbin/cron`. Simplest, try this first.
2. **Migrate to `launchd`** — macOS's native scheduler, which doesn't hit
   the same TCC wall for user agents. Create
   `~/Library/LaunchAgents/com.orbit.pipeline.plist` pointing at `run.sh`,
   load it with `launchctl load`. More idiomatic on macOS but more setup.

**Check your work:** run `./run.sh install`, wait for the next scheduled
firing (every 10 min for the pipeline, every 30 min for the freshness
check), and confirm `pipeline.log`/`check.log` show clean `loaded ...` /
`OK:` lines with no `Operation not permitted` errors.

---

## When you're done

- Update the README roadmap checkboxes for the items this roadmap covers.
- Update `README.md` to mention `.env` setup and link to this file and
  `docs/SDLC.md`.
- `extract.py` (the old scratch script) can be deleted now — it's dead code
  that duplicates `extract()` and isn't invoked by anything.
