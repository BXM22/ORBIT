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

## Acknowledgements
The `run.sh` script was developed with help from [Claude](https://claude.ai), an AI assistant by Anthropic.

## Roadmap
- [ ] Add a data freshness check
- [ ] Orchestrate with Airflow (scheduling and retries)
- [ ] Move the SQL into dbt models with automated tests
- [ ] Dashboard on top of the summary view