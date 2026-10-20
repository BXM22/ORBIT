import pytest


@pytest.fixture
def sample_payload():
    """A known-good reading, shaped like the API response."""
    return {"latitude": 10.0, "longitude": 20.0, "altitude": 400.0,
            "velocity": 7660.0, "timestamp": 1700000000}
