import os

from src.services import analyze_cashback, load_data, print_results
from src.views import main_info

if __name__ == "__main__":
    # Главная
    date_time = "2019-12-24 15:30:00"  # datetime.now()
    print(main_info(date_time))

    # Сервисы
    file_path = os.path.join("data\\operations.xlsx")
    df = load_data(file_path)

    if df is None:
        exit()

    print("\n1. Анализ за весь период:")
    all_results, all_period = analyze_cashback(df)
    print_results(all_results, all_period)

    print("\n2. Анализ за конкретный месяц:")
    month_results, month_period = analyze_cashback(df)
    print_results(month_results, month_period)
