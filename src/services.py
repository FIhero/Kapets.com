import json
import logging
from datetime import datetime
from functools import reduce

from src.utils import load_and_prepare_data, logger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_cashback(file_xlsx: str, date_time: str) -> str:
    """Анализирует кэшбэк по категориям за указанный месяц и год"""
    logger.info(f"Запуск анализа кэшбэка. Файл: {file_xlsx}, Дата: {date_time}")

    try:
        logger.debug("Загрузка данных...")
        df = load_and_prepare_data(file_xlsx)
        if df is None:
            logger.error("Не удалось загрузить данные")
            return json.dumps({"error": "Ошибка загрузки данных"})

        logger.debug("Парсинг даты...")
        target_date = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        logger.info(f"Анализируем период: {target_date.month}.{target_date.year}")

        logger.debug("Фильтрация данных по дате...")
        filtered_data = filter(
            lambda x: x["date"].year == target_date.year
            and x["date"].month == target_date.month,
            df.to_dict("records"),
        )
        filtered_list = list(filtered_data)

        if not filtered_list:
            logger.warning(f"Нет данных за {target_date.month}.{target_date.year}")
            return json.dumps(
                {"error": f"Нет данных за {target_date.month}.{target_date.year}"}
            )

        logger.debug(f"Найдено {len(filtered_list)} транзакций за период")

        logger.debug("Агрегация данных по категориям...")

        def reducer(acc, transaction):
            category = transaction["category"]
            cashback = transaction.get("cashback", 0)
            acc[category] = acc.get(category, 0) + cashback
            return acc

        result = reduce(reducer, filtered_list, {})

        logger.debug("Фильтрация и сортировка результата...")
        result = {
            k: v
            for k, v in sorted(result.items(), key=lambda item: item[1], reverse=True)
            if v > 0
        }

        logger.info(f"Найдено {len(result)} категорий с положительным кэшбэком")
        logger.debug(f"Результат: {result}")

        return json.dumps(result, ensure_ascii=False, indent=2)

    except ValueError as e:
        logger.error(f"Ошибка формата даты: {str(e)}", exc_info=True)
        return json.dumps({"error": "Неверный формат даты"})
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        return json.dumps({"error": "Внутренняя ошибка сервера"})
