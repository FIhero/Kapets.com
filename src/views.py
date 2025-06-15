import json
from datetime import datetime
from typing import Union, Dict, Any

from src.utils.utils_views import (
    get_cards,
    get_date_time,
    get_rates_with_fallback,
    get_sp500_stocks,
    get_time_for_greeting,
)


def main_info(date_time) -> str:
    time_period = get_date_time(date_time)

    json_data = {
        "greating": get_time_for_greeting(),
        "period": time_period,
        "cards": get_cards(),
        "exchange_rate": get_rates_with_fallback(),
        "stocks": get_sp500_stocks(),
    }

    json_data["stocks"] = json_data["stocks"].to_dict(orient="records")
    return json.dumps(json_data, indent=4, ensure_ascii=False)


def print_financial_report(data: Union[Dict[str, Any], str]) -> None:
    """Красиво выводит финансовый отчет в консоль"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            print("Ошибка: Некорректный JSON")
            return

    print("\n" + "=" * 50)
    print(f"{data['greating']}, вот ваш финансовый отчет:")
    print("=" * 50)

    # Период
    print(f"\nПериод: {data['period'][1]} — {data['period'][0]}")
    print("-" * 50)

    # Карты
    cards = data["cards"]
    print(f"\nКарты (статус: {cards['state']}):")
    print(f"Всего операций: {len(cards['operations'])}")
    total_cashback = sum(op["cashback"] for op in cards["operations"])
    print(f"Общий кэшбэк: {total_cashback:.2f} руб.")

    # Топ-5 операций
    print("\nТоп-5 операций:")
    for op in cards["top_5_transactions"]:
        print(
            f"{op['date']} | Карта ****{op['card_number']} | {op['amount']:>10.2f} руб. | Кэшбэк: {op['cashback']} руб."
        )

    # Курсы валют
    rates = data["exchange_rate"]["rates"]
    print("\nКурсы валют:")
    print(f"USD: {rates['USD']} руб. | EUR: {rates['EUR']} руб.")
    print(f"Актуально на: {data['exchange_rate']['date']}")

    # Акции (если есть)
    if data["stocks"]:
        print("\nАкции S&P500:")
        for stock in data["stocks"]:
            print(f"{stock['Symbol']}: {stock['Price']}$")

    print("\n" + "=" * 50)
    print("Отчет сформирован:", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    print("=" * 50)


