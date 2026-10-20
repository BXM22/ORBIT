# Step 7 — Write one real integration test

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
from orbit.load import load

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
`ON CONFLICT (observed_at) DO NOTHING` line in `orbit/load.py` temporarily
and re-run the test — it should now *fail* (the second `load()` hits the
primary key and raises a `UniqueViolation`), proving the test is actually
exercising the dedupe behavior rather than trivially passing. Put the line
back afterwards.

---

[← Step 6](06-mock-load.md) · [Index](README.md) · [Step 8 →](08-github-actions-ci.md)
