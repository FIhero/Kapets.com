import json
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, TypeVar, Any

import pandas as pd
from black.lines import Callable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="reports.log",
)
logger = logging.getLogger(__name__)


def ensure_data_dir():
    """Создаёт папку data, если она не существует"""
    os.makedirs("data", exist_ok=True)



F = TypeVar('F', bound=Callable[..., pd.DataFrame])

def report_to_file(default_filename: Optional[str] = None):
    """Декоратор для сохранения отчёта в папку data"""
    def decorator(func: Callable[..., pd.DataFrame]):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> pd.DataFrame:
            ensure_data_dir()

            filename = kwargs.pop("report_filename", default_filename)
            if filename is None:
                filename = f"{func.__name__}_report.json"

            filepath = os.path.join("data", filename)

            result = func(*args, **kwargs)

            if result is not None:
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        if isinstance(result, (pd.DataFrame, pd.Series)):
                            result.to_json(f, orient="records", force_ascii=False)
                        else:
                            json.dump(result, f, ensure_ascii=False, indent=4)
                    logger.info(f"Отчёт сохранён в {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка сохранения отчёта: {str(e)}")
                    raise

            return result

        return wrapper

    if callable(default_filename):
        func = default_filename
        default_filename = f"{func.__name__}_report.json"
        return decorator(func)

    return decorator


@report_to_file("spending_report.json")
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: Optional[str] = None
) -> pd.DataFrame:
    """
    Возвращает траты по указанной категории за последние 3 месяца.
    Автоматически обрабатывает входящие данные и сохраняет отчет в JSON.
    """
    try:
        if not isinstance(transactions, pd.DataFrame):
            raise ValueError("transactions должен быть pandas DataFrame")

        required_columns = {"date", "category", "amount"}
        missing_columns = required_columns - set(transactions.columns)
        if missing_columns:
            error_msg = f"Отсутствуют обязательные колонки: {missing_columns}"
            logger.error(error_msg)
            return pd.DataFrame({"error": [error_msg]})

        end_date = (
            datetime.now()
            if date is None
            else datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        )
        start_date = end_date - timedelta(days=90)
        logger.info(f"Период отчета: {start_date.date()} - {end_date.date()}")

        transactions["date"] = pd.to_datetime(transactions["date"])
        mask = (
            (transactions["date"] >= start_date)
            & (transactions["date"] <= end_date)
            & (transactions["category"] == category)
        )
        filtered = transactions.loc[mask].copy()

        filtered["month"] = filtered["date"].dt.to_period("M")
        result = filtered.groupby("month")["amount"].sum().reset_index()
        result["month"] = result["month"].astype(str)

        logger.info(f"Найдено {len(result)} месяца с тратами в категории '{category}'")
        return result

    except Exception as e:
        error_msg = f"Критическая ошибка: {str(e)}"
        logger.exception(error_msg)
        return pd.DataFrame({"error": [error_msg]})
