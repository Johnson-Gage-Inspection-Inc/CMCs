import pytest
from src.ExtractCMCsFromPDF import process_pdf

HARDNESS_SCALES = {
    "HRA",
    "HRBW",
    "HRC",
    "HREW",
    "HRFW",
    "HRHW",
    "HR15N",
    "HR30N",
    "HR30TW",
    "HR45TW",
}


@pytest.mark.parametrize(
    "pdf_file",
    [
        "tests/test_data/JGI A2LA Cert 2820.01 Exp 03-2025.pdf",
        "tests/test_data/2820-01.pdf",
    ],
)
def test_hardness_scales_not_in_range(pdf_file):
    """Test that hardness scales & subheadings (Low, Medium, High) do not appear in the 'Range' column."""
    df = process_pdf(pdf_file, save_intermediate=False)

    # Ensure 'Range' column exists
    assert "Range" in df.columns, "Column 'Range' not found in extracted DataFrame."

    # Convert 'Range' column to a set of unique values for quick lookup
    extracted_ranges = set(df["Range"].dropna().unique())

    # Check that no hardness scales are mistakenly in 'Range'
    for invalid_value in HARDNESS_SCALES:
        assert (
            invalid_value not in extracted_ranges
        ), f"Hardness scale '{invalid_value}' found in 'Range' column."
