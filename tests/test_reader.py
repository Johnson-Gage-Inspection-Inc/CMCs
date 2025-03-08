import pytest
from src.main import custom_extract_tables
import pdfplumber
import json
from deepdiff import DeepDiff  # Add this import


@pytest.mark.parametrize(
    "pdf_file",
    [
        "page1.pdf",
        "page21.pdf",
    ],
)
def test_extract_tables_by_position(pdf_file):
    """Test extract_tables_by_position function."""
    with pdfplumber.open(f"tests/test_data/pages/{pdf_file}") as pdf:
        for page in pdf.pages:
            tables = custom_extract_tables(page)

    json_file = f"tests/test_data/pages/{pdf_file}".replace(".pdf", ".json")
    json_data = json.load(open(json_file))

    # Use DeepDiff for better error messages
    if len(tables) != len(json_data):
        pytest.fail(f"Table count mismatch: expected {len(json_data)}, got {len(tables)}")

    for i, (table, expected_table) in enumerate(zip(tables, json_data)):
        diff = DeepDiff(expected_table, table, report_repetition=True)
        assert not diff, f"Table {i} mismatch:\n{diff.pretty()}"
