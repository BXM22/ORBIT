import pytest

from orbit.exceptions import ValidationError
from orbit.validate import validate


def test_validate_accepts_nominal_reading(sample_payload):
    validate(sample_payload)  # should not raise


@pytest.mark.parametrize("field,bad_value", [
    ("latitude", 89), ("latitude", -91),
    ("longitude", 181), ("longitude", -181),
    ("altitude", 299), ("altitude", 501),
])
def test_validate_rejects_out_of_range(sample_payload, field, bad_value):
    sample_payload[field] = bad_value
    with pytest.raises(ValidationError):
        validate(sample_payload)


@pytest.mark.parametrize("field,edge", [
    ("latitude", 90), ("latitude", -90),
    ("longitude", 180), ("longitude", -180),
    ("altitude", 300), ("altitude", 500),
])
def test_validate_accepts_boundary_values(sample_payload, field, edge):
    sample_payload[field] = edge
    validate(sample_payload)


def test_validate_collects_multiple_errors(sample_payload):
    sample_payload["latitude"] = 999
    sample_payload["longitude"] = 999
    with pytest.raises(ValidationError) as exc:
        validate(sample_payload)
    assert "latitude" in str(exc.value)
    assert "longitude" in str(exc.value)
