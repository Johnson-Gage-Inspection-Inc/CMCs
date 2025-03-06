import pytest
import pandas as pd
from src.main import process_pdf


@pytest.mark.parametrize(
    "pdf_file",
    [
        "tests/test_data/JGI A2LA Cert 2820.01 Exp 03-2025.pdf",
        "tests/test_data/2820-01.pdf",
    ],
)
def test_extracted_pdf_ranges(pdf_file):
    # This calls the entire pipeline: reading -> expansion -> parse_range
    df_final = process_pdf(pdf_file, save_intermediate=False)

    # Basic checks
    assert isinstance(df_final, pd.DataFrame)
    assert not df_final.empty, f"No rows extracted from {pdf_file}."

    # We expect columns like RangeMin/RangeMax/RangeUnit from expand_rows
    for col in ["RangeMin", "RangeMax", "RangeUnit"]:
        assert col in df_final.columns, f"Missing '{col}' after expansion."

    # Check for any rows that completely failed range parsing
    failed_parses = df_final[
        df_final["RangeMin"].isna() & df_final["RangeMax"].isna() & (df_final["Range"] != "")
    ]
    assert (
        failed_parses.empty
    ), f"Failed parse on rows: {failed_parses[['Range']].values}"
