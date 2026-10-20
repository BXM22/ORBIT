# Step 4 — Write your first unit test: `validate()`

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
from orbit.validate import validate
from orbit.exceptions import ValidationError

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

You'll also want a `pytest.ini` at the repo root. `pythonpath = .` lets the
tests import the `orbit` package when you run plain `pytest`, and the marker
lets later steps register `integration` tests without warnings:

```ini
[pytest]
pythonpath = .
markers =
    integration: requires a live Postgres (docker-compose db service)
```

**Check your work:** `pip install pytest` then `pytest tests/test_validate.py -v` — all cases should pass, and this should run instantly with no network or Docker involved.

---

[← Step 3](03-env-var-dsn.md) · [Index](README.md) · [Step 5 →](05-mock-extract.md)
