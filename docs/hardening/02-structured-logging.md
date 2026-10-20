# Step 2 — Add structured logging

**Why:** right now, success is a bare `print()` and failure is either an
uncaught exception or (soon) a swallowed `ValidationError`. You want a log
you can actually read after the fact to answer "did last night's run work?"

**What to change:** add `logging` setup at the start of `main()` in
`orbit/pipeline.py`, and replace the final `print` with a log call. Log to
stdout/stderr only — don't add a `FileHandler`. `run.sh` already redirects
cron output into `pipeline.log` via `>> pipeline.log 2>&1`; if the pipeline
also wrote to that file directly, you'd get everything twice. Keeping the
code agnostic about where it logs also matters once you add CI (Step 8) —
you don't want a test run leaving a `pipeline.log` file inside the CI runner.

```python
# orbit/pipeline.py
import logging

log = logging.getLogger("orbit")

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ...
```

Putting `basicConfig` inside `main()` (not at module level) means importing
the package from a test doesn't reconfigure logging as a side effect. The
other modules only need `log = logging.getLogger("orbit")` at the top; they
share the configuration `main()` sets up.

Then in each function:
- `extract()` in `orbit/extract.py`: on failure (timeout, bad HTTP status), log at `ERROR` with
  `log.exception(...)` so the traceback is captured, before re-raising or
  letting it propagate.
- `load()` in `orbit/load.py`: after the `INSERT`, check `cur.rowcount` — `0` means the row
  already existed (dedupe no-op), `1` means a new row landed. Log which one
  happened at `INFO`. This is a real data-quality signal worth having.
- `main()` in `orbit/pipeline.py`: wrap the `extract → validate → load`
  sequence in a `try/except ValidationError`, log the error, and exit
  non-zero — no raw traceback for an *expected* condition like a bad reading.

```python
from orbit.exceptions import ValidationError

def main():
    logging.basicConfig(...)
    try:
        payload = extract()
        validate(payload)
        load(payload)
        log.info("loaded %s", payload["timestamp"])
    except ValidationError as e:
        log.error("rejected reading: %s", e)
        raise SystemExit(1)
```

**Check your work:** run `python -m orbit.pipeline` manually and confirm you see
timestamped `INFO` log lines instead of a bare `loaded ...` print. Then
temporarily hardcode a bad payload into `validate()`'s caller to confirm a
`ValidationError` logs cleanly and exits with status 1 (check with
`echo $?`) instead of dumping a traceback.

---

[← Step 1](01-validation-exception.md) · [Index](README.md) · [Step 3 →](03-env-var-dsn.md)
