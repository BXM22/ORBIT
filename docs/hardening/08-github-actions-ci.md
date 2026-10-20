# Step 8 — Wire up GitHub Actions CI

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

[← Step 7](07-integration-test.md) · [Index](README.md) · [Step 9 →](09-cron-operation-not-permitted.md)
