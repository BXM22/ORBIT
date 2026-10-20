from unittest.mock import patch

import pytest

from orbit.exceptions import ValidationError
from orbit.pipeline import main


@patch("orbit.pipeline.load")
@patch("orbit.pipeline.validate")
@patch("orbit.pipeline.extract")
def test_main_runs_extract_validate_load(mock_extract, mock_validate, mock_load, sample_payload):
    mock_extract.return_value = sample_payload

    main()

    mock_validate.assert_called_once_with(sample_payload)
    mock_load.assert_called_once_with(sample_payload)


@patch("orbit.pipeline.load")
@patch("orbit.pipeline.validate", side_effect=ValidationError("bad"))
@patch("orbit.pipeline.extract")
def test_main_exits_1_and_skips_load_on_validation_error(
    mock_extract, mock_validate, mock_load, sample_payload
):
    mock_extract.return_value = sample_payload

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    mock_load.assert_not_called()
