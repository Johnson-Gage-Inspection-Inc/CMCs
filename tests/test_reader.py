import pytest
from src.main import custom_extract_tables, custom_parse_table
import pdfplumber
import json
from deepdiff import DeepDiff


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


@pytest.mark.parametrize(
    "json_file",
    [
        "page1.json",
    ],
)
def test_parse_table(json_file):
    """Test the custom_parse_table function with JSON input and expected CSV output."""
    import json
    # Load input JSON
    with open(f"tests/test_data/pages/{json_file}") as file:
        input_data = json.load(file)
    # Get the output from the new function
    for table in input_data:
        output_csv = custom_parse_table(table)
        # Load expected CSV content
        with open("tests/test_data/tables/parsed/page1_table0.csv") as csv_file:
            expected_csv = csv_file.read()
        # Compare the output with the expected output
        assert output_csv == expected_csv, "Parsed CSV output does not match the expected CSV content."
