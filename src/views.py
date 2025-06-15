import json

from src.utils.utils_views import (get_cards, get_date_time,
                                   get_rates_with_fallback, get_sp500_stocks,
                                   get_time_for_greeting)


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
