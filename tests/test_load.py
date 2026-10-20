import logging
from unittest.mock import patch

from orbit.load import load


def _mock_cursor(mock_connect):
    # load() uses `with connect(...) as conn, conn.cursor() as cur`, so the
    # cursor sits behind two __enter__ calls.
    mock_conn = mock_connect.return_value.__enter__.return_value
    return mock_conn.cursor.return_value.__enter__.return_value


@patch("orbit.load.psycopg2.connect")
def test_load_executes_insert_with_expected_params(mock_connect, sample_payload):
    mock_cursor = _mock_cursor(mock_connect)

    load(sample_payload)

    sql, params = mock_cursor.execute.call_args.args
    assert "ON CONFLICT" in sql
    assert params == (
        sample_payload["timestamp"], sample_payload["latitude"],
        sample_payload["longitude"], sample_payload["altitude"],
        sample_payload["velocity"],
    )


@patch("orbit.load.psycopg2.connect")
def test_load_logs_inserted_row(mock_connect, sample_payload, caplog):
    _mock_cursor(mock_connect).rowcount = 1
    with caplog.at_level(logging.INFO):
        load(sample_payload)
    assert "inserted new row" in caplog.text


@patch("orbit.load.psycopg2.connect")
def test_load_logs_duplicate_row(mock_connect, sample_payload, caplog):
    _mock_cursor(mock_connect).rowcount = 0
    with caplog.at_level(logging.INFO):
        load(sample_payload)
    assert "duplicate reading" in caplog.text
