"""Runs load() against a real Postgres. Needs `docker compose up -d`.

Uses a separate `iss_test` database so the real raw_iss_positions data is
never touched.
"""
from pathlib import Path

import psycopg2
import pytest

import orbit.load
from orbit.config import DSN

pytestmark = pytest.mark.integration

TEST_DB = "iss_test"
TEST_DSN = DSN.rsplit("/", 1)[0] + "/" + TEST_DB


@pytest.fixture
def pg_conn(monkeypatch):
    admin = psycopg2.connect(DSN)
    admin.autocommit = True  # CREATE DATABASE can't run in a transaction
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
        if cur.fetchone() is None:
            cur.execute(f"CREATE DATABASE {TEST_DB}")
    admin.close()

    conn = psycopg2.connect(TEST_DSN)
    with conn.cursor() as cur:
        cur.execute(Path("sql/schema.sql").read_text())
        cur.execute("TRUNCATE raw_iss_positions")
    conn.commit()
    monkeypatch.setattr(orbit.load, "DSN", TEST_DSN)
    yield conn
    conn.close()


def test_load_is_idempotent_on_conflict(pg_conn, sample_payload):
    orbit.load.load(sample_payload)
    orbit.load.load(sample_payload)  # same observed_at, called twice

    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM raw_iss_positions WHERE observed_at = to_timestamp(%s)",
            (sample_payload["timestamp"],),
        )
        assert cur.fetchone()[0] == 1
