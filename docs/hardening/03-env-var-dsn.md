# Step 3 — Move the DB connection string into an environment variable

**Why:** a hardcoded DSN (`postgresql://postgres:postgres@localhost:5432/iss`)
means you can't point the pipeline at a different database (e.g. the one
GitHub Actions spins up in Step 8) without editing source code.

**What to change:** in `orbit/config.py`, replace the hardcoded `DSN`:

```python
# orbit/config.py
import os
DSN = os.environ.get("ORBIT_DSN", "postgresql://postgres:postgres@localhost:5432/iss")
```

Add `python-dotenv` to `requirements.txt` so you can keep a local `.env`
file instead of exporting the variable by hand every session. Put the
`load_dotenv()` call in `orbit/config.py` too, above the `DSN` line, so the
`.env` file is read before `DSN` looks up the variable:

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
`python -m orbit.pipeline`, and confirm it still works using the fallback default.
Then set `ORBIT_DSN` to something obviously wrong
(`ORBIT_DSN=postgresql://nope/nope python -m orbit.pipeline`) and confirm it now
fails to connect — proving the env var is actually being read.

---

[← Step 2](02-structured-logging.md) · [Index](README.md) · [Step 4 →](04-unit-test-validate.md)
