import pytest
import os
import pandas as pd
from src.reader import extract_pdf_tables_to_df


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
