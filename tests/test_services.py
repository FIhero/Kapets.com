import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.services import analyze_cashback


@pytest.fixture
def mock_logger():
    with patch("src.services.logger") as mock:
        yield mock


@pytest.fixture
def mock_load_and_prepare_data():
    with patch("src.services.load_and_prepare_data") as mock:
        yield mock


def test_analyze_cashback_success(mock_load_and_prepare_data, mock_logger):
    test_data = [
        {"date": datetime(2023, 1, 1), "category": "Food", "cashback": 10},
        {"date": datetime(2023, 1, 2), "category": "Food", "cashback": 20},
        {"date": datetime(2023, 1, 3), "category": "Transport", "cashback": 5},
        {"date": datetime(2022, 12, 1), "category": "Food", "cashback": 15},
    ]

    mock_df = MagicMock()
    mock_df.to_dict.return_value = test_data
    mock_load_and_prepare_data.return_value = mock_df

    result = analyze_cashback("test.xlsx", "2023-01-01 00:00:00")
    data = json.loads(result)

    assert "Food" in data
    assert "Transport" in data
    assert data["Food"] == 30
    assert data["Transport"] == 5
    assert len(data) == 2
    mock_logger.info.assert_called()


def test_analyze_cashback_no_data(mock_load_and_prepare_data, mock_logger):
    mock_df = MagicMock()
    mock_df.to_dict.return_value = []
    mock_load_and_prepare_data.return_value = mock_df

    result = analyze_cashback("test.xlsx", "2023-01-01 00:00:00")
    data = json.loads(result)

    assert "error" in data
    mock_logger.warning.assert_called()


def test_analyze_cashback_load_error(mock_load_and_prepare_data, mock_logger):
    mock_load_and_prepare_data.return_value = None

    result = analyze_cashback("test.xlsx", "2023-01-01 00:00:00")
    data = json.loads(result)

    assert "error" in data
    mock_logger.error.assert_called()


def test_analyze_cashback_invalid_date_format(mock_logger):
    result = analyze_cashback("test.xlsx", "invalid-date")
    data = json.loads(result)

    assert "error" in data
    mock_logger.error.assert_called()


def test_analyze_cashback_general_exception(mock_load_and_prepare_data, mock_logger):
    mock_load_and_prepare_data.side_effect = Exception("Test error")

    result = analyze_cashback("test.xlsx", "2023-01-01 00:00:00")
    data = json.loads(result)

    assert "error" in data
    mock_logger.error.assert_called()


def test_analyze_cashback_filtering(mock_load_and_prepare_data):
    test_data = [
        {"date": datetime(2023, 1, 1), "category": "Jan", "cashback": 10},
        {"date": datetime(2023, 2, 1), "category": "Feb", "cashback": 20},
        {"date": datetime(2023, 1, 2), "category": "Jan", "cashback": 5},
    ]

    mock_df = MagicMock()
    mock_df.to_dict.return_value = test_data
    mock_load_and_prepare_data.return_value = mock_df

    result = analyze_cashback("test.xlsx", "2023-01-01 00:00:00")
    data = json.loads(result)

    assert "Jan" in data
    assert "Feb" not in data
    assert data["Jan"] == 15


def test_analyze_cashback_negative_cashback(mock_load_and_prepare_data):
    test_data = [
        {"date": datetime(2023, 1, 1), "category": "Positive", "cashback": 10},
        {"date": datetime(2023, 1, 2), "category": "Negative", "cashback": -5},
        {"date": datetime(2023, 1, 3), "category": "Zero", "cashback": 0},
    ]

    mock_df = MagicMock()
    mock_df.to_dict.return_value = test_data
    mock_load_and_prepare_data.return_value = mock_df

    result = analyze_cashback("test.xlsx", "2023-01-01 00:00:00")
    data = json.loads(result)

    assert "Positive" in data
    assert "Negative" not in data
    assert "Zero" not in data
