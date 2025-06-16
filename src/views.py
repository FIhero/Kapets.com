import json
import logging
from datetime import datetime

from src.utils import (
    get_cards,
    get_rates_with_fallback,
    get_sp500_stocks,
    get_time_for_greeting,
    get_top_transactions,
)

logger = logging.getLogger(__name__)


def main_info(date_time) -> str:
    """Главная функция страницы <Главная>"""
    try:
        datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")

        json_data = {
            "greeting": get_time_for_greeting(),
            "cards": get_cards("data\\operations.xlsx", date_time),
            "top_transactions": get_top_transactions(
                "data\\operations.xlsx", date_time
            ),
            "currency_rates": [
                {"currency": "USD", "rate": get_rates_with_fallback()["rates"]["USD"]},
                {"currency": "EUR", "rate": get_rates_with_fallback()["rates"]["EUR"]},
            ],
            "stock_prices": get_sp500_stocks().to_dict(orient="records"),
        }

        return json.dumps(json_data, indent=4, ensure_ascii=False)

    except ValueError as e:
        logger.error(f"Неверный формат даты: {date_time}. Ошибка: {str(e)}")
        return json.dumps({"error": "Invalid date format"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка при формировании отчета: {str(e)}")
        return json.dumps({"error": "Internal server error"}, ensure_ascii=False)
