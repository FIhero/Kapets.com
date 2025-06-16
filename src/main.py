from src.services import analyze_cashback
from src.views import main_info

if __name__ == "__main__":
    # Главная
    date_time = "2019-12-24 15:30:00"  # datetime.now()
    print(main_info(date_time))

    # Сервисы
    file_xlsx = "data\\operations.xlsx"

    full_year_result = analyze_cashback(file_xlsx, date_time)
    print(full_year_result)
