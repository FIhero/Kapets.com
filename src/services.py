import os
from typing import Dict, Optional, Tuple

import pandas as pd


def load_data(file_path: str = "data/operations.xlsx") -> Optional[pd.DataFrame]:
    """Загружает данные из Excel файла"""
    try:
        if not os.path.exists(file_path):
            print(f"Файл не найден: {file_path}")
            return None
        return pd.read_excel(file_path)
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return None


def analyze_cashback(
    df: pd.DataFrame, year: Optional[int] = None, month: Optional[int] = None
) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
    """Анализирует кэшбэк в переданном DataFrame"""
    try:
        required_cols = ["дата операции", "категория", "кэшбэк"]
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            print(f"Отсутствуют столбцы: {missing}")
            return None, None

        df["дата операции"] = pd.to_datetime(df["дата операции"], errors="coerce")
        df = df.dropna(subset=["дата операции"])

        period = "Все данные"
        if year is not None and month is not None:
            mask = (df["дата операции"].dt.year == year) & (
                df["дата операции"].dt.month == month
            )
            df = df[mask]

            if df.empty:
                print(f"Нет данных за {month}.{year}")
                return None, None

            start_date = df["дата операции"].min().strftime("%d.%m.%Y")
            end_date = df["дата операции"].max().strftime("%d.%m.%Y")
            period = f"{start_date} - {end_date}"

        cashback = df.groupby("категория")["кэшбэк"].sum()
        cashback = cashback.sort_values(ascending=False)

        return cashback.to_dict(), period

    except Exception as e:
        print(f"Ошибка анализа: {e}")
        return None, None


def print_results(results: Optional[Dict[str, float]], period: Optional[str]):
    """Выводит результаты анализа"""
    if not results:
        print("Нет данных для отображения")
        return

    print(f"\nАнализ за период: {period}")
    print("-" * 40)
    for category, amount in results.items():
        print(f"{category:<20}: {amount:>10.2f} руб.")
    print("-" * 40)
    print(f"Всего категорий: {len(results)}")
    print(f"Общий кэшбэк: {sum(results.values()):.2f} руб.")
