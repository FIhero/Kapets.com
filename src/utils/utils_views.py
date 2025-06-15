import os
from datetime import datetime
from typing import Any, Dict, Union

import pandas as pd
import requests


def get_time_for_greeting():
    """Возвращает приветствие в зависимости от времени"""
    user_datetime = datetime.now()
    hour = user_datetime.hour

    if 5 <= hour <= 12:
        return "Доброе утро"
    elif 12 <= hour <= 18:
        return "Добрый день"
    elif 18 <= hour <= 23:
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


def get_cards(
    file_xlsx: str = "data/operations.xlsx",
) -> Union[Dict[str, Any], pd.DataFrame]:
    """Загрузка и обработка данных операций"""
    try:
        df = pd.read_excel(file_xlsx)

        df = df.rename(
            columns={
                "дата операции": "date",
                "номер карты": "card_number",
                "сумма операции": "amount",
                "кэшбэк": "cashback",
                "статус": "state",
            }
        )

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        df["card_number"] = df["card_number"].astype(str).str[-4:]

        operations = []
        for _, row in df.iterrows():
            operations.append(
                {
                    "date": row["date"].strftime("%d.%m.%Y %H:%M:%S"),
                    "card_number": row["card_number"],
                    "amount": float(row["amount"]),
                    "cashback": row.get("cashback", 0),
                }
            )

        top_transactions = df.nlargest(5, "amount")[
            ["date", "card_number", "amount", "cashback"]
        ]

        top_5 = []
        for _, row in top_transactions.iterrows():
            top_5.append(
                {
                    "date": row["date"].strftime("%d.%m.%Y %H:%M:%S"),
                    "card_number": row["card_number"],
                    "amount": float(row["amount"]),
                    "cashback": row.get("cashback", 0),
                }
            )

        return {
            "state": df.iloc[0]["state"],
            "operations": operations,
            "top_5_transactions": top_5,
        }

    except Exception as e:
        print(f"Ошибка при загрузки данных: {e}")
        return pd.DataFrame()


# ___________________________Курс рубля____________________________________


API_KEY = os.environ.get("API_KEY")
API_URL = "https://api.apilayer.com/exchangerates_data/latest?base=USD&symbols=RUB,EUR"
HEADERS = {"apikey": API_KEY}


def get_currency_rates():
    """Получает курсы USD/RUB и EUR/RUB с обработкой ошибок"""
    try:
        if not API_URL or not API_KEY:
            raise ValueError("API_URL или API_KEY не заданы")

        params = {"base": "USD", "symbols": "RUB,EUR"}

        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data.get("success", False):
            raise ValueError(
                f"API error: {data.get('error', {}).get('info', 'Unknown error')}"
            )

        usd_rub = data["rates"]["RUB"]
        eur_usd = 1 / data["rates"]["EUR"]
        eur_rub = usd_rub * eur_usd

        return {
            "success": True,
            "rates": {"USD": round(usd_rub, 2), "EUR": round(eur_rub, 2)},
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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


# ________________________Акции_____________________________


def get_sp500_stocks():
    sp500_symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]

    stock_data = []
    for symbol in sp500_symbols:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "Global Quote" in data:
            price = data["Global Quote"]["05. price"]
            stock_data.append({"Symbol": symbol, "Price": price})

    return pd.DataFrame(stock_data)
