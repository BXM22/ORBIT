# ORBIT

A minimal data pipeline that tracks the International Space Station.

## Purpose
I built this to learn the core patterns behind production data pipelines
(extract, validate, load, transform) in the smallest form that still works.
It's intentionally simple so I can grow it step by step.

## What it does
- **Extracts** the ISS's current position from the Where The ISS At API
- **Validates** each reading (latitude, longitude, altitude range) before storing it
- **Loads** it into Postgres, skipping duplicates, so re-running is safe
- **Summarizes** the data in a SQL view (daily readings, average speed, max altitude)

## Stack
Python · PostgreSQL · SQL · Docker Compose

## How to run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d  # first start also creates the table and view from sql/
./run.sh          # run once
./run.sh install  # run every 10 minutes
```

To run the pipeline by hand (the database must already be up), use
`python3 -m orbit.pipeline` from the repo root. To print the latest stored
positions, use `python3 -m orbit.show` (or `python3 -m orbit.show 25` for 25 rows).

## Configuration
The database connection string is read from the `ORBIT_DSN` environment
variable. If it isn't set, it defaults to the local Docker Compose database
(`postgresql://postgres:postgres@localhost:5432/iss`), so nothing is needed for
the default setup.

To override it, copy the template and edit the copy:
```bash
cp .env.example .env   # .env is gitignored; never commit it
```
`.env` is loaded automatically (via `python-dotenv`), including when run from cron.

## Project layout
```
orbit/
├── config.py      # API url and database connection string (from ORBIT_DSN)
├── exceptions.py  # ValidationError
├── extract.py     # extract(): fetch the current position
├── validate.py    # validate(): range checks
├── load.py        # load(): insert into Postgres
├── pipeline.py    # main(): extract -> validate -> load
└── show.py        # print the latest stored positions
sql/               # table and summary view, run on first database start
tests/             # pytest suite (unit + integration)
docs/              # roadmaps and design notes
run.sh             # run, schedule, and freshness check
```

## Tests
```bash
pip install -r requirements-dev.txt
pytest                  # unit tests, no Docker needed
pytest -m integration   # needs `docker compose up -d`
```
See [docs/TESTING.md](docs/TESTING.md) for what each test covers.

See [docs/CODE_STRUCTURE.md](docs/CODE_STRUCTURE.md) for why it's split this way.

## Acknowledgements
The `run.sh` script was developed with help from [Claude](https://claude.ai), an AI assistant by Anthropic.

## Roadmap
- [ ] Add a data freshness check
- [ ] Orchestrate with Airflow (scheduling and retries)
- [ ] Move the SQL into dbt models with automated tests
- [ ] Dashboard on top of the summary view