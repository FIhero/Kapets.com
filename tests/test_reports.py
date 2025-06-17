from unittest.mock import patch

import pandas as pd
import pytest

from src.reports import ensure_data_dir, report_to_file, spending_by_category


@pytest.fixture
def mock_logger():
    with patch("src.reports.logger") as mock:
        yield mock


@pytest.fixture
def test_transactions():
    return pd.DataFrame(
        {
            "date": [
                "2023-01-01",
                "2023-01-15",
                "2023-02-01",
                "2023-03-01",
                "2022-12-01",
            ],
            "category": ["food", "food", "transport", "food", "food"],
            "amount": [100, 200, 150, 300, 50],
        }
    )


@pytest.fixture
def mock_file_operations():
    with (
        patch("builtins.open"),
        patch("os.makedirs"),
        patch("json.dump"),
        patch("pandas.DataFrame.to_json"),
    ):
        yield


def test_spending_by_category_success(
    test_transactions, mock_logger, mock_file_operations
):
    result = spending_by_category(test_transactions, "food")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    assert "month" in result.columns
    assert "amount" in result.columns
    mock_logger.info.assert_called()


def test_spending_by_category_no_data(
    test_transactions, mock_logger, mock_file_operations
):
    result = spending_by_category(test_transactions, "clothes")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    mock_logger.info.assert_called()


def test_spending_by_category_invalid_input(mock_logger, mock_file_operations):
    result = spending_by_category("invalid_data", "food")

    assert isinstance(result, pd.DataFrame)
    assert "error" in result.columns
    assert mock_logger.error.call_count == 0


def test_spending_by_category_missing_columns(mock_logger, mock_file_operations):
    invalid_df = pd.DataFrame({"wrong_col": [1, 2, 3]})

    result = spending_by_category(invalid_df, "food")

    assert isinstance(result, pd.DataFrame)
    assert "error" in result.columns
    mock_logger.error.assert_called()


def test_spending_by_category_specific_date(
    test_transactions, mock_logger, mock_file_operations
):
    result = spending_by_category(test_transactions, "food", "2023-01-31 00:00:00")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    mock_logger.info.assert_called()


def test_report_to_file_decorator(test_transactions, tmp_path):
    test_dir = tmp_path / "data"

    with patch("os.path.join") as mock_join:
        mock_join.return_value = str(test_dir / "spending_report.json")

        with patch("builtins.open"), patch("json.dump"):

            assert mock_join.called


def test_ensure_data_dir(tmp_path):
    with patch("os.makedirs") as mock_makedirs:
        ensure_data_dir()
        mock_makedirs.assert_called_with("data", exist_ok=True)


def test_report_to_file_with_custom_filename(test_transactions, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    @report_to_file("custom_report.json")
    def dummy_func():
        return test_transactions


def test_report_to_file_error_handling(test_transactions, mock_logger):
    with patch("builtins.open", side_effect=Exception("File error")):
        try:
            spending_by_category(test_transactions, "food")
        except Exception:
            pass
        mock_logger.error.assert_called_with("Ошибка сохранения отчёта: File error")
