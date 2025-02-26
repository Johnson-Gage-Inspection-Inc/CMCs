import pytest
import pandas as pd
from src.ExtractCMCsFromPDF import extract_pdf_tables, parse_range


@pytest.mark.parametrize("pdf_file", [
    "tests/test_data/JGI A2LA Cert 2820.01 Exp 03-2025.pdf",  # Replace with actual file paths
    "tests/test_data/2820-01.pdf",
])
def test_extracted_pdf_ranges(pdf_file):
    df = extract_pdf_tables(pdf_file)

    # Apply parse_range() on extracted data
    df[["RangeMin", "RangeMax", "RangeUnit"]] = df["Range"].apply(
        lambda x: pd.Series(parse_range(x))
    )

    # Check for rows where parsing failed
    failed_parses = df[df["RangeMin"].isna() & df["RangeMax"].isna()]
    assert failed_parses.empty, f"Parsing failed on rows: {failed_parses[['Range']]}"
