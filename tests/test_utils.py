import json
import os
import unittest
from datetime import datetime
from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from src.utils import (
    get_cards,
    get_date_time,
    get_sp500_stocks,
    get_time_for_greeting,
    get_top_transactions,
    load_and_prepare_data,
    load_user_settings,
)

API_URL = os.environ.get("API_URL")
API_KEY = os.environ.get("API_KEY")


def get_currency_rates():
    if not API_URL or not API_KEY:
        return {"success": False, "error": "API_URL или API_KEY не заданы"}


@pytest.fixture
def valid_data_fixture(tmp_path):
    """Фикстура с корректными данными"""
    file_path = tmp_path / "valid_data.xlsx"
    df = pd.DataFrame(
        {
            "Дата операции": ["01.01.2023 12:00:00", "15.01.2023 14:30:00"],
            "Номер карты": ["1234567890123456", "9876543210987654"],
            "Сумма операции": [100.0, 200.0],
            "Категория": ["Еда", "Транспорт"],
            "Описание": ["Обед", "Такси"],
        }
    )
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def invalid_data_fixture(tmp_path):
    file_path = tmp_path / "invalid_data.xlsx"
    df = pd.DataFrame(
        {
            "Дата операции": ["01.01.2023 12:00:00", "не дата"],
            "Номер карты": ["1234567890123456", ""],
            "Сумма операции": [100.0, "не число"],
            "Категория": ["Еда", None],
            "Описание": ["Обед", ""],
        }
    )
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def empty_data_fixture(tmp_path):
    """Фикстура с пустыми данными"""
    file_path = tmp_path / "empty_data.xlsx"
    pd.DataFrame().to_excel(file_path)
    return file_path


@pytest.fixture
def expenses_fixture(tmp_path):
    """Фикстура с корректными данными"""
    file_path = tmp_path / "valid_data_expenses.xlsx"
    df = pd.DataFrame(
        {
            "Дата операции": [
                "01.01.2023 12:00:00",
                "15.01.2023 14:30:00",
                "21.01.2023 16:40:03",
                "23.01.2023 18:36:45",
            ],
            "Номер карты": [
                "1234567890123456",
                "9876543210987654",
                "1234567890123456",
                "9876543210987654",
            ],
            "Сумма операции": [-100.0, -200.0, 500.0, -250.0],
            "Категория": ["Еда", "Транспорт", "Доход", "Цветы"],
            "Описание": ["Обед", "Такси", "Кэшбэк", "Магазин <KBimka>"],
        }
    )
    df.to_excel(file_path, index=False)
    return file_path


@pytest.mark.parametrize(
    "hour, expected_greeting",
    [
        ("2019-12-24 7:34:23", "Доброе утро"),
        ("2019-02-24 13:35:24", "Добрый день"),
        ("2020-06-05 21:34:56", "Добрый вечер"),
        ("2019-09-29 3:23:52", "Доброй ночи"),
        ("2019-12-31 5:00:00", "Доброе утро"),
        ("2019-02-28 12:00:00", "Добрый день"),
        ("2019-05-31 19:00:00", "Добрый вечер"),
        ("2019-12-24 23:00:00", "Доброй ночи"),
        ("2019-12-24 11:59:59", "Доброе утро"),
        ("2019-12-24 18:59:59", "Добрый день"),
        ("2019-12-24 22:59:59", "Добрый вечер"),
        ("2019-12-24 4:59:59", "Доброй ночи"),
    ],
)
def test_get_greeting(hour, expected_greeting):
    """Тестирует приветствие"""
    test_time = datetime.strptime(hour, "%Y-%m-%d %H:%M:%S")
    with patch("src.utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = test_time
        assert get_time_for_greeting() == expected_greeting


# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_date, expected_dates",
    [
        ("2019-12-24 15:30:00", ["24.12.2019 15:30:00", "01.12.2019 00:00:00"]),
        ("2020-02-29 10:15:00", ["29.02.2020 10:15:00", "01.02.2020 00:00:00"]),
        ("2023-01-01 00:00:01", ["01.01.2023 00:00:01", "01.01.2023 00:00:00"]),
    ],
)
def test_get_date_time(input_date, expected_dates):
    """Тестирует корректность выведения даты и периода"""
    assert get_date_time(input_date) == expected_dates


def test_invalid_date():
    """Тестирует на ошибки при неверной указанной дате"""
    with pytest.raises(ValueError):
        get_date_time("2023-02-30 00:00:00")


# ___________________________Тесты по операциям транзакций__________________________________


def test_load_valid_data(valid_data_fixture):
    df = load_and_prepare_data(valid_data_fixture)
    assert not df.empty
    assert list(df.columns) == [
        "date",
        "card_number",
        "amount",
        "category",
        "description",
    ]
    assert df["card_number"].iloc[0] == "3456"


def test_invalid_data_handling(invalid_data_fixture):
    df = load_and_prepare_data(invalid_data_fixture)
    assert len(df) < 2


def test_empty_file(empty_data_fixture):
    with pytest.raises(ValueError, match="Отсутствуют колонки"):
        load_and_prepare_data(empty_data_fixture)


def test_date_filtering(valid_data_fixture):
    filtered = load_and_prepare_data(
        valid_data_fixture, date_time="2023-01-15 00:00:00"
    )
    assert len(filtered) == 1
    assert filtered["date"].iloc[0] == datetime(2023, 1, 1, 12, 0)


# ---------------------------------------------------------------------------------------------


def test_get_cards(valid_data_fixture):
    result = get_cards(valid_data_fixture)
    assert isinstance(result, list)
    assert len(result) > 0

    assert set(result[0].keys()) == {"last_digits", "cashback"}

    assert result[0]["last_digits"] == "3456"
    assert isinstance(result[0]["cashback"], float)


def test_invalid_data_handling_get_cards(invalid_data_fixture):
    df = get_cards(invalid_data_fixture)
    assert len(df) < 2


def test_empty_file_get_cards(empty_data_fixture):
    with pytest.raises(ValueError, match="Отсутствуют колонки"):
        get_cards(empty_data_fixture)


# ---------------------------------------------------------------------------------------------
def test_get_top_transactions(expenses_fixture):
    result = get_top_transactions(expenses_fixture)
    assert isinstance(result, list)
    assert len(result) > 0

    assert set(result[0].keys()) == {"date", "amount", "category", "description"}


def test_invalid_data_handling_get_top_transactions(invalid_data_fixture):
    df = get_top_transactions(invalid_data_fixture)
    assert df is None


def test_empty_file_get_top_transactions(empty_data_fixture):
    assert get_top_transactions(empty_data_fixture) is None


def test_expenses_sorting(expenses_fixture):
    result = get_top_transactions(expenses_fixture)
    amounts = [t["amount"] for t in result]
    assert amounts == sorted(amounts)


def test_expenses_count(expenses_fixture):
    result = get_top_transactions(expenses_fixture)
    assert len(result) <= 5


# -----------------------------------Тесты по курсу рубля---------------------------------------------------------


@patch("src.utils.requests.get")
def test_get_currency_rates(mock_get):
    mock_get.return_value.json.return_value = {"rates": {"USD": 75.0, "EUR": 85.0}}
    result = get_currency_rates()
    assert result["rates"]["USD"] == 75.0


# ---------------------------------------Тесты по Акциям------------------------------------------------------


class TestUserSettingsFunctions(unittest.TestCase):

    def setUp(self):
        self.valid_settings = {
            "user_currencies": ["USD", "EUR", "GBP"],
            "user_stocks": ["AAPL", "MSFT", "NVDA"],
        }

        self.mock_api_response = {"Global Quote": {"05. price": "185.25"}}

    def test_load_user_settings_success(self):
        """Тест успешной загрузки настроек из файла"""
        mock_file = mock_open(read_data=json.dumps(self.valid_settings))

        with patch("builtins.open", mock_file):
            result = load_user_settings()

        self.assertEqual(result, self.valid_settings)

    def test_load_user_settings_file_not_found(self):
        """Тест обработки отсутствия файла настроек"""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = load_user_settings()

        self.assertEqual(result["user_currencies"], ["USD", "EUR"])
        self.assertEqual(
            result["user_stocks"], ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
        )

    def test_load_user_settings_invalid_json(self):
        """Тест обработки невалидного JSON"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = load_user_settings()

        self.assertEqual(result["user_currencies"], ["USD", "EUR"])

    @patch("src.utils.API_KEY", None)
    def test_get_sp500_stocks_no_api_key(self):
        """Тест работы без API ключа (возврат mock данных)"""
        result = get_sp500_stocks()
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 5)
        self.assertListEqual(
            result["stock"].tolist(), ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        )

    @patch("src.utils.API_KEY", "valid_key")
    @patch("src.utils.requests.get")
    @patch("src.utils.load_user_settings")
    def test_get_sp500_stocks_success(self, mock_load_settings, mock_requests):
        """Тест успешного получения данных об акциях"""
        mock_load_settings.return_value = {"user_stocks": ["AAPL", "MSFT"]}

        mock_response = unittest.mock.Mock()
        mock_response.json.return_value = self.mock_api_response
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        result = get_sp500_stocks()

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["stock"], "AAPL")
        self.assertEqual(result.iloc[0]["price"], 185.25)

    @patch("src.utils.API_KEY", "valid_key")
    @patch("src.utils.requests.get")
    @patch("src.utils.load_user_settings")
    def test_get_sp500_stocks_api_error(self, mock_load_settings, mock_requests):
        """Тест обработки ошибки API"""
        mock_load_settings.return_value = {"user_stocks": ["AAPL"]}

        mock_requests.side_effect = Exception("API error")

        result = get_sp500_stocks()
        self.assertTrue(result.empty)

    @patch("src.utils.API_KEY", "valid_key")
    @patch("src.utils.load_user_settings")
    def test_get_sp500_stocks_no_stocks_in_settings(self, mock_load_settings):
        """Тест случая, когда в настройках нет акций"""
        mock_load_settings.return_value = {"user_stocks": []}

        result = get_sp500_stocks()
        self.assertTrue(result.empty)

    @patch("src.utils.API_KEY", "valid_key")
    @patch("src.utils.requests.get")
    @patch("src.utils.load_user_settings")
    def test_get_sp500_stocks_invalid_response(self, mock_load_settings, mock_requests):
        """Тест обработки невалидного ответа от API"""
        mock_load_settings.return_value = {"user_stocks": ["AAPL"]}

        mock_response = unittest.mock.Mock()
        mock_response.json.return_value = {"invalid": "data"}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        result = get_sp500_stocks()
        self.assertTrue(result.empty)
