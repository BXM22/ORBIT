# ORBIT Hardening Roadmap — a step-by-step tutorial

This is a guided exercise, not a diff to copy-paste. Work through the steps
in order — each one builds on the last (you genuinely can't write a good
test for `validate()` until Step 1 is done, because bare `assert` is
basically untestable). Each step says what to change, why, shows a worked
example, and gives you a quick check before moving on.

Scope for this roadmap: **testing + CI** and **observability/data quality**.
Airflow orchestration, dbt models, and a dashboard are intentionally *not*
covered here — they're later roadmap items in the README.

---

## Steps

1. [Replace bare `assert` with a real exception](01-validation-exception.md)
2. [Add structured logging](02-structured-logging.md)
3. [Move the DB connection string into an environment variable](03-env-var-dsn.md)
4. [Write your first unit test: `validate()`](04-unit-test-validate.md)
5. [Mock `requests.get` to test `extract()`](05-mock-extract.md)
6. [Mock `psycopg2` to test `load()`](06-mock-load.md)
7. [Write one real integration test](07-integration-test.md)
8. [Wire up GitHub Actions CI](08-github-actions-ci.md)
9. [Diagnose and fix the cron "Operation not permitted" bug](09-cron-operation-not-permitted.md)

---

## When you're done

- Update the README roadmap checkboxes for the items this roadmap covers.
- Update `README.md` to mention `.env` setup and link to this file and
  `docs/SDLC.md`.
- `extract.py` (the old scratch script) can be deleted now — it's dead code
  that duplicates `extract()` and isn't invoked by anything.
