import pandas as pd

from src.reports import spending_by_category
from src.services import analyze_cashback
from src.utils import load_and_prepare_data
from src.views import main_info

# from datetime import datetime

if __name__ == "__main__":
    # Главная
    date_time = "2019-12-24 15:30:00"  # datetime.now()
    print(main_info(date_time))

    # Сервисы
    file_xlsx = "data\\operations.xlsx"
    file_xlsx_1 = pd.read_excel("data\\operations.xlsx")

    full_year_result = analyze_cashback(file_xlsx, date_time)
    print(full_year_result)

    # Отчет
    df = load_and_prepare_data(file_xlsx_1)
    category = "Транспорт"  # input("Введите категорию:")
    result = spending_by_category(df, category, date_time)
    print(result)
