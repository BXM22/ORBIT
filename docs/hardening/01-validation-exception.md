# Step 1 — Replace bare `assert` with a real exception

**Why:** `assert` statements vanish entirely when Python runs with `-O`, and
an `AssertionError` only ever carries the *first* failing condition. Neither
property is what you want from input validation in a pipeline.

**What to change:** the custom exception lives in its own file,
`orbit/exceptions.py` (already created). Keeping it out of the other modules means anything that needs
to catch or raise `ValidationError` later (a test, a future second pipeline
module, a dbt/Airflow task) imports a small standalone module instead of
pulling in HTTP/DB dependencies along with it — and it keeps
the behavior modules free of type definitions.

```python
# orbit/exceptions.py
class ValidationError(ValueError):
    """Raised when an ISS position reading fails a sanity check."""
```

Then in `orbit/validate.py`, import it and rewrite `validate()` to collect
*every* failing field, not just the first:

```python
# orbit/validate.py
from orbit.exceptions import ValidationError

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

This is a one-file exception module, not a subpackage — no `orbit/exceptions/`
directory needed yet. If a second exception type shows up later (e.g. a
`StaleDataError` for the freshness check), that's the natural point to
reconsider, not before.

**Check your work:** run `python -c "from orbit.validate import validate; validate({'latitude': 999, 'longitude': 999, 'altitude': 400})"` and confirm you get a `ValidationError` whose message mentions *both* latitude and longitude, not just the first bad field. Also run `python -c "from orbit.exceptions import ValidationError; print(ValidationError)"` on its own to confirm `orbit/exceptions.py` is importable without pulling in `requests` or `psycopg2`.

---

[← Index](README.md) · [Step 2 →](02-structured-logging.md)
