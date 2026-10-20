# ORBIT Code Structure — splitting `pipeline.py` into modules

A guided exercise, not a diff to copy-paste. Originally `pipeline.py` held config,
extraction, validation, loading, and the entry point. This guide splits those
into one file per responsibility so each piece can be imported, tested, and
changed on its own.

## Status: done (Oct 19, 2026)

The split below has been applied. It was done **before** hardening Steps 1–3
instead of after them, as a pure refactor, so the code was moved as it was:

| File | What's in it now | Changes still to come |
|---|---|---|
| `orbit/config.py` | `API`, hardcoded `DSN` | Step 3 adds `load_dotenv()` and `ORBIT_DSN` |
| `orbit/exceptions.py` | `ValidationError` (moved from the root) | — |
| `orbit/extract.py` | `extract()` | Step 2 adds error logging |
| `orbit/validate.py` | `validate()`, still using `assert` | Step 1 switches to `ValidationError` |
| `orbit/load.py` | `load()` | Step 2 adds `rowcount` logging |
| `orbit/pipeline.py` | `main()`: extract, validate, load, then `print` | Step 2 adds logging and `try/except ValidationError` |

Other changes made with the split:

- `run.sh` runs `.venv/bin/python -m orbit.pipeline` instead of `pipeline.py`.
- The root-level `pipeline.py` and `exceptions.py` were removed (`git mv`, so
  their history follows them into `orbit/`).
- `docs/hardening/` Steps 1–9 now name the new files, imports, and `@patch`
  targets, and Step 4's `pytest.ini` includes `pythonpath = .`.
- `docs/SDLC.md`, `docs/DASHBOARD_ROADMAP.md`, and `README.md` describe the
  new layout.

Behavior is unchanged: a live reading still extracts, validates, and loads the
same way, and `main()` passes the same values to the `INSERT`.

The rest of this guide is kept as the reasoning behind the layout and as a
reference for the code examples, which show the end state after Steps 1–3.

**Originally planned timing:** after [Step 3](hardening/03-env-var-dsn.md) of the
hardening roadmap (logging and the env-var DSN are in) and **before**
[Step 4](hardening/04-unit-test-validate.md). Splitting before Step 4 means your
tests are written against the final import paths and you don't rewrite their
`@patch` targets later.

---

## Target layout

```
ORBIT/
├── orbit/
│   ├── __init__.py      # empty; marks the folder as a package
│   ├── config.py        # API url, DSN, load_dotenv()
│   ├── exceptions.py    # ValidationError (moved from the repo root)
│   ├── extract.py       # extract()
│   ├── validate.py      # validate()
│   ├── load.py          # load()
│   └── pipeline.py      # main(): extract -> validate -> load, plus logging
├── tests/
├── sql/
└── run.sh
```

Why a package folder instead of loose files in the root: the root stays for
config and scripts (`run.sh`, `docker-compose.yml`, `requirements.txt`), and
`orbit.extract` can't collide with a stray `extract.py` scratch script.

Why one function per file: each module has one reason to change. A change to
the API url touches `config.py`; a new sanity check touches `validate.py`.
Don't over-split. Three-line modules are fine, but don't add subpackages
until a module outgrows a screen or two.

---

## What goes where

**`config.py`** holds the constants and nothing that does I/O except reading
the environment.

```python
import os
from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist

API = "https://api.wheretheiss.at/v1/satellites/25544"
DSN = os.environ.get("ORBIT_DSN", "postgresql://postgres:postgres@localhost:5432/iss")
```

**`extract.py`**, **`validate.py`**, **`load.py`** each hold their one
function, with only the imports that function needs:

```python
# orbit/extract.py
import requests
from orbit.config import API

def extract():
    ...
```

```python
# orbit/validate.py
from orbit.exceptions import ValidationError

def validate(p: dict) -> None:
    ...
```

```python
# orbit/load.py
import psycopg2
from orbit.config import DSN

def load(p):
    ...
```

`validate.py` importing nothing but `exceptions` is the payoff: it's pure, so
its tests need no mocks and no installed HTTP/DB libraries.

**`pipeline.py`** becomes a thin orchestrator. It owns logging setup and the
`try/except ValidationError` from Step 2, and nothing else:

```python
# orbit/pipeline.py
import logging

from orbit.exceptions import ValidationError
from orbit.extract import extract
from orbit.validate import validate
from orbit.load import load

log = logging.getLogger("orbit")

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        payload = extract()
        validate(payload)
        load(payload)
        log.info("loaded %s", payload["timestamp"])
    except ValidationError as e:
        log.error("rejected reading: %s", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
```

Moving `basicConfig` into `main()` means importing the package (in a test, for
example) doesn't reconfigure logging as a side effect.

---

## Things that change because of the split

1. **Imports.** Use absolute imports (`from orbit.config import DSN`). Run the
   pipeline as a module from the repo root: `python -m orbit.pipeline`.
2. **`run.sh`.** In `run_pipeline()`, change `.venv/bin/python pipeline.py` to
   `.venv/bin/python -m orbit.pipeline`. `run.sh` already `cd`s to the repo
   root, which is what `-m` needs.
3. **Mock targets in the tests.** `@patch` must name the module where the name
   is *looked up*, not where it was defined:
   - Step 5: `@patch("orbit.extract.requests.get")`, and
     `from orbit.extract import extract` / `from orbit.config import API`.
   - Step 6: `@patch("orbit.load.psycopg2.connect")`, and
     `from orbit.load import load`.
   - Steps 4 and 7: `from orbit.validate import validate`,
     `from orbit.exceptions import ValidationError`, `from orbit.load import load`.
4. **CI (Step 8).** If the workflow runs `pipeline.py` directly anywhere, switch
   it to `python -m orbit.pipeline`. `pytest` from the repo root needs no
   change as long as `orbit/` is in the root. If imports fail, add
   `pythonpath = .` to `pytest.ini`.
5. **Docs.** Search `docs/` for `from pipeline import` and `pipeline.requests` /
   `pipeline.psycopg2` and update them to the new paths.
6. **Delete the old root-level `pipeline.py` and `exceptions.py`** once the
   package versions work. Leaving both is a classic source of "which one is
   actually running?" bugs.

---

## Do it in small, checkable moves

Run a check after each move; don't batch them.

1. Create `orbit/` with an empty `__init__.py`. `git mv exceptions.py orbit/exceptions.py`.
   **Check:** `python -c "from orbit.exceptions import ValidationError"`.
2. Create `config.py`. **Check:** `python -c "from orbit.config import DSN, API; print(DSN)"`.
3. Move `extract()`, then `validate()`, then `load()` into their files, importing
   from `config`/`exceptions` as needed. **Check** each with a one-line
   `python -c "from orbit.<module> import <fn>"`.
4. Move the orchestration into `orbit/pipeline.py` (with `git mv pipeline.py orbit/pipeline.py`
   first, so git keeps the history, then cut the functions out of it).
   **Check:** `python -m orbit.pipeline` loads a row, same as before.
5. Update `run.sh`. **Check:** `./run.sh run`, then `./run.sh check` prints `OK:`.

**Check your work at the end:** `grep -rn "import pipeline\|from pipeline" .`
should return nothing outside `docs/` history, and `python -m orbit.pipeline`
should behave exactly like the old `python pipeline.py`. This is a pure
refactor, so no behavior should change.
