# ORBIT — Software Development Lifecycle

A lightweight process for a solo learning project. The point is to keep good
habits, not to add ceremony. Skip anything here that doesn't earn its keep as
the project grows — but write down *why* you skipped it (see "Design" below
for an example of that in practice).

## 1. Overview

ORBIT is maintained by one person, for learning. This doc exists so that
future-you (or anyone else who opens the repo) knows the expected workflow
for making a change, without having to re-derive it from scratch each time.

## 2. Planning

- The **README roadmap checklist** is the backlog. New work starts there:
  add a checkbox before writing code if the change is bigger than a one-line
  fix.
- For anything non-trivial (new feature, schema change, new dependency),
  write a short plan first — a few sentences on what's changing and why is
  enough. `docs/HARDENING.md` is an example of this for the current
  testing/observability work.

## 3. Design

- Default to the flat repo layout and stdlib tools. Only reach for a new
  framework, directory structure, or dependency when the current approach is
  actually in the way — not because a "real" project would have it.
- Example of this principle applied: the pipeline started as a single
  root-level `pipeline.py`. It moved into the `orbit/` package (one module
  per step: `extract`, `validate`, `load`, plus `config`, `exceptions`, and
  a thin `pipeline` orchestrator) only once tests were about to be written
  against it, so test imports and `@patch` targets wouldn't need rewriting
  later. It's still a plain folder with an `__init__.py` — no `src/` layout
  or `pyproject.toml` until something actually needs them. See
  `docs/CODE_STRUCTURE.md`.
- Document deferred-but-considered ideas in the README roadmap so the
  reasoning isn't lost.

## 4. Implementation

- Config (DB connection strings, API URLs, thresholds) comes from environment
  variables with sane local defaults — never hardcode credentials.
- Errors that represent *expected* bad conditions (e.g. an out-of-range
  reading) should raise a specific, named exception and get logged — not a
  bare `assert` and not a silent `print`.
- Use the stdlib `logging` module for anything worth knowing about after the
  fact (a successful load, a validation failure, a network error). If you
  can't answer "did this run work?" by reading the log, add a log line.

## 5. Testing

- Unit tests mock anything that leaves the process (HTTP calls, database
  connections). They should run in well under a second, with no Docker and
  no network.
- At least one integration test per data path exercises the real thing (real
  Postgres via `docker compose`) to catch the gap between "the mock says
  this works" and "it actually works."
- Fast feedback loop: `pytest -m "not integration"` while iterating,
  `pytest -m integration` before considering a change done.

## 6. CI / Review

- Every push/PR runs lint + unit tests + integration tests in GitHub Actions.
  A red CI run means the change isn't done yet, even if it "works on my
  machine."
- Since this is a solo project, there's no PR-approval gate — but don't merge
  to `master` on a broken CI run.

## 7. Deployment

- `docker compose up -d` brings up Postgres. On a fresh database it runs
  everything in `sql/` automatically.
- Apply `sql/schema.sql` (and `sql/summary.sql` for the summary view) manually
  after any schema change to an existing database.
- `./run.sh install` schedules the pipeline (every 10 min) and the freshness
  check (every 30 min) via cron — or via `launchd` if the project migrates
  off cron (see Step 9 in `docs/HARDENING.md`).

## 8. Monitoring / Maintenance

- `pipeline.log` and `check.log` are the first place to look when something's
  wrong.
- `./run.sh check` is the staleness watchdog — if the newest reading is more
  than 30 minutes old, it logs a `STALE:` line and fires a desktop
  notification.
- The README roadmap is the living list of what's intentionally not done yet
  (Airflow orchestration, dbt models, a dashboard). Update it as items land
  or priorities change.
