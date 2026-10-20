# Step 6 — Mock `psycopg2` to test `load()`

**Why:** same idea as Step 5, but for the database. This is the trickiest
mock in the project because `load()` chains two `with` statements
(`with psycopg2.connect(DSN) as conn, conn.cursor() as cur:`), so you need to
wire up the mock's `__enter__` return values correctly or the test will
silently check the wrong object.

**What to create:** `tests/test_load.py`.

```python
# tests/test_load.py
from unittest.mock import patch
from orbit.load import load

@patch("orbit.load.psycopg2.connect")
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

[← Step 5](05-mock-extract.md) · [Index](README.md) · [Step 7 →](07-integration-test.md)
