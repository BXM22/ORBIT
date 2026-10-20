# Step 5 — Mock `requests.get` to test `extract()`

**Why:** `extract()` makes a real HTTP call. A unit test should never
actually hit the network — it should be fast, deterministic, and not fail
just because the ISS API is briefly down.

**What to create:** `tests/test_extract.py`, patching `requests.get` inside
the `orbit.extract` module's namespace (important: patch
`orbit.extract.requests.get`, not `requests.get` globally — `@patch` must
name the module where the name is *looked up*, and `orbit/extract.py`
imported `requests` into its own namespace).

```python
# tests/test_extract.py
from unittest.mock import patch
import pytest
import requests
from orbit.extract import extract
from orbit.config import API

@patch("orbit.extract.requests.get")
def test_extract_returns_parsed_json(mock_get):
    mock_get.return_value.json.return_value = {
        "latitude": 1, "longitude": 2, "altitude": 400,
        "velocity": 7000, "timestamp": 123,
    }
    mock_get.return_value.raise_for_status.return_value = None

    result = extract()

    assert result["latitude"] == 1
    mock_get.assert_called_once_with(API, timeout=10)

@patch("orbit.extract.requests.get")
def test_extract_raises_on_http_error(mock_get):
    mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("500")
    with pytest.raises(requests.HTTPError):
        extract()
```

**Check your work:** `pytest tests/test_extract.py -v`. Confirm it passes with your Wi-Fi off — if it still passes offline, you know the mock is actually being used instead of a real network call.

---

[← Step 4](04-unit-test-validate.md) · [Index](README.md) · [Step 6 →](06-mock-load.md)
