import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
from cachetools import TTLCache, cached
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

currency_cache: TTLCache[str, Any] = TTLCache(maxsize=10, ttl=3600)
stocks_cache: TTLCache[str, Any] = TTLCache(maxsize=10, ttl=3600)
rates_fallback_cache: TTLCache[str, Any] = TTLCache(maxsize=5, ttl=1800)


def get_time_for_greeting():
    """Возвращает приветствие в зависимости от времени"""
    user_datetime = datetime.now()
    hour = user_datetime.hour

    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 19:
        return "Добрый день"
    elif 19 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_date_time(date_time, date_format="%Y-%m-%d %H:%M:%S"):
    """Изменяет формат даты"""
    today = datetime.strptime(date_time, date_format)
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0)

    return [
        today.strftime("%d.%m.%Y %H:%M:%S"),
        start_of_month.strftime("%d.%m.%Y %H:%M:%S"),
    ]


# ___________________________Операции транзакций__________________________________
def load_and_prepare_data(
    file_xlsx: Union[str, pd.DataFrame] = "data\\operations.xlsx",
    date_time: Optional[str] = None,
) -> pd.DataFrame:
    """Общая функция для загрузки и подготовки данных"""
    try:
        if isinstance(file_xlsx, pd.DataFrame):
            df = file_xlsx.copy()
        else:
            if not isinstance(file_xlsx, (str, bytes, os.PathLike)):
                raise TypeError(
                    "Путь к файлу должен быть строкой, bytes или os.PathLike"
                )

            if not os.path.exists(file_xlsx):
                raise FileNotFoundError(f"Файл не найден: {file_xlsx}")

            df = pd.read_excel(file_xlsx, engine="openpyxl")

        required_cols = ["Дата операции", "Номер карты", "Сумма операции"]
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            raise ValueError(f"Отсутствуют колонки: {missing}")

        df = df.rename(
            columns={
                "Дата операции": "date",
                "Номер карты": "card_number",
                "Сумма операции": "amount",
                "Категория": "category",
                "Описание": "description",
                "Кэшбэк": "cashback",
            }
        )

        df["date"] = pd.to_datetime(
            df["date"], format="%d.%m.%Y %H:%M:%S", dayfirst=True, errors="coerce"
        )

        if date_time:
            try:
                today_str, start_of_month_str = get_date_time(date_time)
                start_date = datetime.strptime(start_of_month_str, "%d.%m.%Y %H:%M:%S")
                end_date = datetime.strptime(today_str, "%d.%m.%Y %H:%M:%S")

                mask = (df["date"] >= start_date) & (df["date"] <= end_date)
                df = df.loc[mask].copy()
            except Exception as e:
                logger.warning(f"Ошибка фильтрации даты: {str(e)}")

        df = df.dropna(subset=["date", "card_number", "amount"])

        if df.empty:
            logger.warning(
                f"Нет данных за период {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            )
            return pd.DataFrame()

        df["card_number"] = df["card_number"].astype(str).str.strip().str[-4:]
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        return df.dropna(subset=["amount"])
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {str(e)}", exc_info=True)
        raise ValueError(f"Файл операций не найден: {file_xlsx}") from e
    except pd.errors.EmptyDataError as e:
        logger.error(f"Файл пуст: {str(e)}", exc_info=True)
        raise ValueError("Файл операций пуст") from e
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {str(e)}", exc_info=True)
        raise ValueError(f"Ошибка обработки данных: {str(e)}") from e


def get_cards(
    file_xlsx: str = "data\\operations.xlsx", date_time: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Формирует список карт с информацией о расходах и кэшбэке за указанный период"""
    try:
        df = load_and_prepare_data(file_xlsx, date_time)

        if df.empty:
            return []

        cards = []
        for card in df["card_number"].unique():
            card_df = df[df["card_number"] == card]
            expenses = card_df[card_df["amount"] < 0]["amount"].sum()
            cards.append(
                {
                    "last_digits": card[-4:],
                    "total_spent": round(-expenses, 2),
                    "cashback": round((-expenses) / 100, 2),
                }
            )

        return cards

    except Exception as e:
        logger.error(f"Ошибка формирования карт: {str(e)}")
        raise


def get_top_transactions(
    file_xlsx: str = "data\\operations.xlsx", date_time: Optional[str] = None
) -> List[Dict[str, Any]] | None:
    """Анализ больших транзакций за период"""
    try:
        df = load_and_prepare_data(file_xlsx, date_time)

        if df.empty:
            return None

        expenses = df[df["amount"] < 0]
        if expenses.empty:
            return [{"message": "Нет расходных операций за период"}]

        if expenses.empty:
            return None

        top_expenses = expenses.sort_values("amount", ascending=True).head(5)[
            ["date", "amount", "category", "description"]
        ]

        top_5 = []
        for _, row in top_expenses.iterrows():
            top_5.append(
                {
                    "date": row["date"].strftime("%d.%m.%Y"),
                    "amount": float(row["amount"]),
                    "category": str(row["category"]),
                    "description": str(row["description"]),
                }
            )
        return top_5

    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {str(e)}")
        return None


# ___________________________Курс рубля____________________________________

API_KEY = os.environ.get("API_KEY")
API_URL = "https://api.apilayer.com/exchangerates_data/latest?base=USD&symbols=RUB,EUR"


currency_cache = TTLCache(maxsize=10, ttl=3600)


@cached(currency_cache)
def get_currency_rates():
    """Получает курсы USD/RUB и EUR/RUB с обработкой ошибок"""
    try:
        api_key_val = API_KEY

        if not API_URL or not api_key_val:
            return {"success": False, "error": "API_URL или API_KEY не заданы"}

        params = {"base": "USD", "symbols": "RUB,EUR"}
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data.get("success", True):
            raise ValueError(
                f"API error: {data.get('error', {}).get('info', 'Unknown error')}"
            )
        if data.get("error"):
            return {"success": False, "error": f"API error: {data['error']}"}

        usd_rub = data["rates"]["RUB"]
        eur_usd = 1 / data["rates"]["EUR"]
        eur_rub = usd_rub * eur_usd

        return {
            "success": True,
            "rates": {"USD": round(usd_rub, 2), "EUR": round(eur_rub, 2)},
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Основной API",
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Ошибка сети: {str(e)}",
            "retry_suggestion": "Проверьте подключение к интернету",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "retry_suggestion": "Попробуйте позже или используйте резервный источник",
        }


@cached(currency_cache)
def get_rates_with_fallback():
    """Основная функция с резервными источниками"""
    result = get_currency_rates()

    if not result["success"]:
        try:
            cbr_data = requests.get(
                "https://www.cbr-xml-daily.ru/daily_json.js", timeout=5
            ).json()
            usd = cbr_data["Valute"]["USD"]["Value"]
            eur = cbr_data["Valute"]["EUR"]["Value"]

            return {
                "rates": {"USD": round(usd, 2), "EUR": round(eur, 2)},
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "ЦБ РФ (резервный)",
            }
        except Exception as e:
            print(f"Ошибка при получении курсов ЦБ РФ: {e}")
            return result
    if "source" not in result:
        result["source"] = "Основной API"
    return result


# ________________________Акции_____________________________
def load_user_settings():
    """Загрузка пользовательских настроек"""
    try:
        with open("../user_settings.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(
            "Файл user_settings.json не найден. Используются настройки по умолчанию"
        )
    except json.JSONDecodeError as e:
        logger.warning(f"Ошибка формата JSON в user_settings.json: {e}")
    except Exception as e:
        logger.warning(f"Неизвестная ошибка при загрузке user_settings.json: {e}")

    return {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
    }


load_dotenv("../.env")

currency_cache = TTLCache(maxsize=10, ttl=3600)
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")


def get_sp500_stocks():
    """Получение данных об акциях с обработкой ошибок"""
    if not ALPHAVANTAGE_API_KEY:
        logger.error("API ключ Alpha Vantage не настроен!")
        return pd.DataFrame(columns=["stock", "price", "error"])

    try:
        settings = load_user_settings()
        stocks = settings.get("user_stocks", [])

        if not stocks:
            logger.warning("Нет акций для отображения в настройках")
            return pd.DataFrame(columns=["stock", "price", "error"])

        results = []
        for symbol in stocks:
            try:
                url = (f"https://www.alphavantage.co/query?function="
                       f"GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHAVANTAGE_API_KEY}")
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()

                if "Global Quote" not in data:
                    logger.warning(f"Неверный формат ответа для {symbol}")
                    results.append(
                        {
                            "stock": symbol,
                            "price": None,
                            "error": "Неверный формат ответа",
                        }
                    )
                    continue

                price = float(data["Global Quote"]["05. price"])
                results.append({"stock": symbol, "price": price, "error": None})

            except Exception as e:
                logger.error(f"Ошибка для {symbol}: {str(e)}")
                results.append({"stock": symbol, "price": None, "error": str(e)})

        return pd.DataFrame(results)

    except Exception as e:
        logger.error(f"Общая ошибка: {str(e)}")
        return pd.DataFrame(columns=["stock", "price", "error"])
