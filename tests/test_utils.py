import os
import unittest
from datetime import datetime
from unittest.mock import mock_open, patch

import numpy as np
import pandas as pd
import pytest
import requests

import src.utils
from src.utils import (
    get_cards,
    get_currency_rates,
    get_date_time,
    get_time_for_greeting,
    get_top_transactions,
    load_and_prepare_data,
    load_user_settings,
)

API_URL = os.environ.get("API_URL")
API_KEY = os.environ.get("API_KEY")


@pytest.fixture(autouse=True)
def clear_caches():
    """Автоматически очищает кеш перед каждым тестом"""
    from src.utils import get_currency_rates, get_rates_with_fallback

    get_currency_rates.cache_clear()
    get_rates_with_fallback.cache_clear()


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


@pytest.fixture
def mock_requests_get():
    with patch("src.utils.requests.get") as mock_get:
        yield mock_get
    if hasattr(get_currency_rates, "cache_clear"):
        get_currency_rates.cache_clear()


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

    assert set(result[0].keys()) == {"last_digits", "total_spent", "cashback"}

    assert result[0]["last_digits"] == "3456"
    assert isinstance(result[0]["cashback"], float)
    assert isinstance(result[0]["total_spent"], (float, np.floating, int, np.integer))


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
    result = get_top_transactions(invalid_data_fixture)
    assert result == [{"message": "Нет расходных операций за период"}]


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
def test_successful_response(monkeypatch, mock_requests_get):
    import src.utils

    monkeypatch.setattr(src.utils, "API_KEY", "test_key")
    monkeypatch.setattr(src.utils, "API_URL", "https://test.api")

    src.utils.get_currency_rates.cache_clear()

    mock_response = {"success": True, "rates": {"RUB": 90.5, "EUR": 0.9}, "base": "USD"}
    mock_requests_get.return_value.json.return_value = mock_response
    mock_requests_get.return_value.raise_for_status.return_value = None

    result = src.utils.get_currency_rates()
    print("Actual result:", result)

    assert result["success"] is True
    assert result["rates"]["USD"] == 90.5
    assert result["rates"]["EUR"] == pytest.approx(90.5 / 0.9, 0.01)


def test_get_currency_rates_api_error(monkeypatch, mock_requests_get, clear_caches):
    monkeypatch.setattr(src.utils, "API_KEY", "test_key")
    monkeypatch.setattr(src.utils, "API_URL", "https://test.api")

    mock_response = {"success": False, "error": {"info": "Invalid API key"}}
    mock_requests_get.return_value.json.return_value = mock_response

    mock_requests_get.return_value.raise_for_status.side_effect = [
        None,
        requests.exceptions.HTTPError("401 Unauthorized"),
    ]

    result = src.utils.get_currency_rates()
    assert result["success"] is False
    assert "Invalid API key" in result["error"]


def test_get_currency_rates_network_error(monkeypatch, mock_requests_get):
    monkeypatch.setattr(src.utils, "API_KEY", "test_key")
    monkeypatch.setattr(src.utils, "API_URL", "https://test.api")

    mock_requests_get.side_effect = requests.exceptions.ConnectionError("Timeout")

    result = src.utils.get_currency_rates()

    print("Actual result:", result)
    assert result["success"] is False
    assert "Timeout" in result["error"]
    assert "Проверьте подключение" in result["retry_suggestion"]


def test_fallback_secondary_ok(monkeypatch, mock_requests_get):
    monkeypatch.setattr(src.utils, "API_KEY", "test_key")
    monkeypatch.setattr(src.utils, "API_URL", "https://test.api")

    mock_requests_get.return_value.json.return_value = {
        "success": False,
        "error": "API down",
    }

    with patch("src.utils.requests.get") as mock_fallback:
        mock_fallback.return_value.json.return_value = {
            "Valute": {"USD": {"Value": 91.2}, "EUR": {"Value": 99.1}}
        }

        result = src.utils.get_rates_with_fallback()

        print("Fallback result:", result)
        assert result["rates"]["USD"] == 91.2
        assert result["rates"]["EUR"] == 99.1
        assert "ЦБ РФ (резервный)" in result["source"]


def test_fallback_all_fail(monkeypatch, mock_requests_get, clear_caches):
    monkeypatch.setattr(src.utils, "API_KEY", "test_key")
    monkeypatch.setattr(src.utils, "API_URL", "https://test.api")

    mock_requests_get.return_value.json.return_value = {
        "success": False,
        "error": "API down",
    }
    mock_requests_get.return_value.raise_for_status.side_effect = (
        requests.exceptions.HTTPError("500 Server Error")
    )

    with patch("src.utils.requests.get") as mock_fallback:
        mock_fallback.side_effect = requests.exceptions.Timeout("Server not responding")

        result = src.utils.get_rates_with_fallback()

        assert result["success"] is False
        assert ("API down" in result["error"]) or (
            "Server not responding" in result["error"]
        )
        assert "retry_suggestion" in result


# ---------------------------------------Тесты по Акциям------------------------------------------------------
@pytest.mark.parametrize(
    "file_content,expected_output,expected_log",
    [
        (
            '{"user_currencies": ["RUB", "CNY"], "user_stocks": ["GAZP"]}',
            {"user_currencies": ["RUB", "CNY"], "user_stocks": ["GAZP"]},
            None,
        ),
        (
            None,
            {
                "user_currencies": ["USD", "EUR"],
                "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
            },
            "Файл user_settings.json не найден",
        ),
        (
            "{invalid json}",
            {
                "user_currencies": ["USD", "EUR"],
                "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
            },
            "Ошибка формата JSON",
        ),
    ],
)
def test_load_user_settings(file_content, expected_output, expected_log, caplog):
    if file_content is not None:
        with patch("builtins.open", mock_open(read_data=file_content)):
            result = load_user_settings()
    else:
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = load_user_settings()

    assert result == expected_output

    if expected_log:
        assert any(expected_log in message for message in caplog.messages)


@pytest.mark.parametrize(
    "api_key,user_stocks,api_responses,expected_output,expected_log",
    [
        (
            "valid_key",
            ["AAPL", "TSLA"],
            [
                {"Global Quote": {"05. price": "150.50"}},
                {"Global Quote": {"05. price": "700.20"}},
            ],
            pd.DataFrame(
                [
                    {"stock": "AAPL", "price": 150.50, "error": None},
                    {"stock": "TSLA", "price": 700.20, "error": None},
                ]
            ),
            None,
        ),
        (
            "valid_key",
            ["AAPL", "INVALID"],
            [
                {"Global Quote": {"05. price": "150.50"}},
                {"Error Message": "Invalid symbol"},
            ],
            pd.DataFrame(
                [
                    {"stock": "AAPL", "price": 150.50, "error": None},
                    {
                        "stock": "INVALID",
                        "price": None,
                        "error": "Неверный формат ответа",
                    },
                ]
            ),
            "Неверный формат ответа для INVALID",
        ),
        (
            None,
            ["AAPL", "TSLA"],
            [],
            pd.DataFrame(
                [
                    {"stock": "AAPL", "price": None, "error": "API ключ не настроен"},
                    {"stock": "TSLA", "price": None, "error": "API ключ не настроен"},
                ]
            ),
            "API ключ Alpha Vantage не настроен",
        ),
        (
            "valid_key",
            [],
            [],
            pd.DataFrame(columns=["stock", "price", "error"]),
            "Нет акций для отображения в настройках",
        ),
        (
            "valid_key",
            ["AAPL"],
            [Exception("Timeout error")],
            pd.DataFrame([{"stock": "AAPL", "price": None, "error": "Timeout error"}]),
            "Timeout error",
        ),
    ],
)
def test_get_sp500_stocks(
    api_key,
    user_stocks,
    api_responses,
    expected_output,
    expected_log,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        "src.utils.load_user_settings",
        lambda: {
            "user_stocks": user_stocks,
            "user_currencies": ["USD", "EUR"],  # Добавляем обязательное поле
        },
    )

    monkeypatch.setattr(
        "os.getenv",
        lambda x, default=None: api_key if x == "ALPHAVANTAGE_API_KEY" else None,
    )

    mock_responses = []
    for resp in api_responses:
        if isinstance(resp, Exception):
            mock_responses.append(resp)
        else:
            mock_response = unittest.mock.Mock()
            mock_response.json.return_value = resp
            mock_response.raise_for_status.return_value = None
            mock_responses.append(mock_response)
