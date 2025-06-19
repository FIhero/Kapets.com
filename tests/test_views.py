import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.views import main_info


@pytest.fixture
def mock_datetime():
    with patch("src.views.datetime") as mock:
        mock.strptime.return_value = datetime(2023, 1, 1, 12, 0, 0)
        yield mock


@pytest.fixture
def mock_load_user_settings():
    with patch("src.views.load_user_settings") as mock:
        mock.return_value = {"user_currencies": ["USD", "EUR"]}
        yield mock


@pytest.fixture
def mock_get_cards():
    with patch("src.views.get_cards") as mock:
        mock.return_value = [
            {"card_name": "Card1", "balance": 1000},
            {"card_name": "Card2", "balance": 2000},
        ]
        yield mock


@pytest.fixture
def mock_get_top_transactions():
    with patch("src.views.get_top_transactions") as mock:
        mock.return_value = [
            {"transaction": "T1", "amount": 100},
            {"transaction": "T2", "amount": 200},
        ]
        yield mock


@pytest.fixture
def mock_get_rates_with_fallback():
    with patch("src.views.get_rates_with_fallback") as mock:
        mock.return_value = {"rates": {"USD": 75.5, "EUR": 85.3}}
        yield mock


@pytest.fixture
def mock_get_sp500_stocks():
    with patch("src.views.get_sp500_stocks") as mock:
        mock.return_value = MagicMock(
            to_dict=MagicMock(
                return_value=[
                    {"stock": "AAPL", "price": 150},
                    {"stock": "MSFT", "price": 250},
                ]
            )
        )
        yield mock


@pytest.fixture
def mock_logger():
    with patch("src.views.logger") as mock:
        yield mock


def test_main_info_success(
    mock_datetime,
    mock_load_user_settings,
    mock_get_cards,
    mock_get_top_transactions,
    mock_get_rates_with_fallback,
    mock_get_sp500_stocks,
):
    date_time = "2023-01-01 12:00:00"
    result = main_info(date_time)
    data = json.loads(result)

    assert data["greeting"] is not None
    assert len(data["cards"]) == 2
    assert len(data["top_transactions"]) == 2
    assert len(data["currency_rates"]) == 2
    assert data["currency_rates"][0]["currency"] == "USD"
    assert data["currency_rates"][0]["rate"] == 75.5
    assert len(data["stock_prices"]) == 2


def test_main_info_invalid_date_format(mock_logger):
    date_time = "invalid-date"
    result = main_info(date_time)
    data = json.loads(result)

    assert "error" in data
    mock_logger.error.assert_called()


def test_main_info_currency_rates_fallback(
    mock_datetime,
    mock_load_user_settings,
    mock_get_cards,
    mock_get_top_transactions,
    mock_get_sp500_stocks,
    mock_logger,
):
    with patch("src.views.get_rates_with_fallback") as mock:
        mock.side_effect = Exception("API error")
        result = main_info("2023-01-01 12:00:00")
        data = json.loads(result)

        assert data["currency_rates"][0]["rate"] == "Недоступно"
        mock_logger.warning.assert_called()


def test_main_info_stocks_fallback(
    mock_datetime,
    mock_load_user_settings,
    mock_get_cards,
    mock_get_top_transactions,
    mock_get_rates_with_fallback,
    mock_logger,
):
    with patch("src.views.get_sp500_stocks") as mock:
        mock.side_effect = Exception("Stock API error")
        result = main_info("2023-01-01 12:00:00")
        data = json.loads(result)

        assert data["stock_prices"] == []
        mock_logger.warning.assert_called()


def test_main_info_general_exception(
    mock_datetime, mock_load_user_settings, mock_logger
):
    with patch("src.views.get_cards") as mock:
        mock.side_effect = Exception("Unexpected error")
        result = main_info("2023-01-01 12:00:00")
        data = json.loads(result)

        assert "error" in data
        mock_logger.error.assert_called()
