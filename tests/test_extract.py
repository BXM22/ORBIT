import logging
from unittest.mock import patch

import pytest
import requests

from orbit.config import API
from orbit.extract import extract


@patch("orbit.extract.requests.get")
def test_extract_returns_parsed_json(mock_get):
    mock_get.return_value.json.return_value = {
        "latitude": 1, "longitude": 2, "altitude": 400,
        "velocity": 7000, "timestamp": 123,
    }
    mock_get.return_value.raise_for_status.return_value = None

    result = extract()

    assert result["latitude"] == 1
    mock_get.assert_called_once_with(API, timeout=10)


@patch("orbit.extract.requests.get")
def test_extract_raises_on_http_error(mock_get):
    mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("500")
    with pytest.raises(requests.HTTPError):
        extract()


@patch("orbit.extract.requests.get")
def test_extract_logs_error_on_failure(mock_get, caplog):
    mock_get.side_effect = requests.Timeout("slow")
    with caplog.at_level(logging.ERROR), pytest.raises(requests.Timeout):
        extract()
    assert "API request failed" in caplog.text
