import pytest
import os
import pandas as pd
from src.reader import extract_pdf_tables_to_df, parse_page_table


@pytest.mark.parametrize(
    "pdf_file",
    [
        "tests/test_data/2820-01.pdf",
        "tests/test_data/JGI A2LA Cert 2820.01 Exp 03-2025.pdf",
    ],
)
def test_extract_pdf_tables_to_df(pdf_file):
    """Test that extract_pdf_tables_to_df returns a valid DataFrame with the required columns."""
    assert os.path.exists(pdf_file), f"Test PDF not found: {pdf_file}"

    df = extract_pdf_tables_to_df(pdf_file)
    assert isinstance(df, pd.DataFrame), "Result is not a DataFrame."

    # Check for the essential columns
    required_cols = [
        "Equipment",
        "Parameter",
        "Range",
        "Frequency",
        "CMC (±)",
        "Comments",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column '{col}' in DataFrame."

    # We expect at least some rows in these PDFs
    assert len(df) > 0, "No rows extracted from PDF."


@pytest.mark.parametrize(
    "table_file",
    [
        "page1_table0.csv",
        "page18_table1.csv",
        "page19_table0.csv",
        "page21_table1.csv",
        "page7_table1.csv",
        "page9_table0.csv",
    ],
)
def test_parse_page_table(table_file):
    """Test that parse_page_table correctly transforms tables according to expected outputs."""

    # Load the input table
    input_path = f"tests/test_data/tables/pre/{table_file}"
    input_df = pd.read_csv(input_path)

    # Process the table
    result_df = parse_page_table(input_df.copy())

    # Load the expected output
    expected_path = f"tests/test_data/tables/parsed/{table_file}"
    expected_df = pd.read_csv(expected_path)

    # Assert dataframes match (ignoring dtype differences)
    pd.testing.assert_frame_equal(
        result_df.reset_index(drop=True),
        expected_df.reset_index(drop=True),
        check_dtype=False
    )