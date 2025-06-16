import json
import logging
from datetime import datetime
from typing import Any, Dict

from src.utils import (
    get_cards,
    get_rates_with_fallback,
    get_sp500_stocks,
    get_time_for_greeting,
    get_top_transactions,
    load_user_settings,
)

logger = logging.getLogger(__name__)


def main_info(date_time: str) -> str:
    """Главная функция страницы <Главная>"""
    try:
        datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")

        settings = load_user_settings()

        json_data: Dict[str, Any] = {
            "greeting": get_time_for_greeting(),
            "cards": get_cards("data/operations.xlsx", date_time),
            "top_transactions": get_top_transactions("data/operations.xlsx", date_time),
            "currency_rates": [],
            "stock_prices": [],
        }

        try:
            rates_data = get_rates_with_fallback()
            rates = rates_data.get("rates", {})

            json_data["currency_rates"] = [
                {"currency": curr, "rate": rates.get(curr, "N/A")}
                for curr in settings.get("user_currencies", ["USD", "EUR"])
            ]
        except Exception as e:
            logger.warning(f"Ошибка при получении курсов валют: {str(e)}")
            json_data["currency_rates"] = [
                {"currency": curr, "rate": "Недоступно"}
                for curr in settings.get("user_currencies", ["USD", "EUR"])
            ]

        try:
            stocks = get_sp500_stocks()
            json_data["stock_prices"] = (
                stocks.to_dict(orient="records") if stocks is not None else []
            )
        except Exception as e:
            logger.warning(f"Ошибка при получении данных об акциях: {str(e)}")
            json_data["stock_prices"] = []

        return json.dumps(json_data, indent=4, ensure_ascii=False)

    except ValueError as e:
        logger.error(f"Неверный формат даты: {date_time}. Ошибка: {str(e)}")
        return json.dumps({"error": "Invalid date format"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка при формировании отчета: {str(e)}")
        return json.dumps({"error": "Internal server error"}, ensure_ascii=False)
