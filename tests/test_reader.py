import pytest
from src.main import custom_parse_table, pdf_table_processor
from src.extract import custom_extract_tables
import pdfplumber
import json
from deepdiff import DeepDiff
import pandas as pd


@pytest.mark.parametrize(
    "pdf_file",
    [
        "page1.pdf",
        "page20.pdf",
        "page21.pdf",
    ],
)
def test_extract_tables_by_position(pdf_file):
    """Test extract_tables_by_position function."""
    with pdfplumber.open(f"tests/test_data/pages/{pdf_file}") as pdf:
        for page in pdf.pages:
            tables = custom_extract_tables(page)

    json_file = f"tests/test_data/pages/{pdf_file}".replace(".pdf", ".json")
    with open(json_file, "r", encoding="utf-8-sig") as file:
        json_data = json.load(file)

    # Use DeepDiff for better error messages
    if len(tables) != len(json_data):
        pytest.fail(
            f"Table count mismatch: expected {len(json_data)}, got {len(tables)}"
        )

    for i, (table, expected_table) in enumerate(zip(tables, json_data)):
        diff = DeepDiff(expected_table, table, report_repetition=True)
        assert not diff, f"Table {i} mismatch:\n{diff.pretty()}"


@pytest.mark.parametrize(
    "json_file",
    [
        "page1.json",
        "page7.json",
        # "page9.json",
        "page16.json",
        "page18.json",
        "page19.json",
        "page20.json",
        "page21.json",
    ],
)
def test_parse_table(json_file):
    """Test the custom_parse_table function with JSON input and expected CSV output."""
    import json

    # Load input JSON
    with open(f"tests/test_data/pages/{json_file}", encoding="utf-8-sig") as file:
        input_data = json.load(file)
    # Get the output from the new function
    table = input_data[-1]
    tableNo = len(input_data) - 1
    table_rows = custom_parse_table(table)
    columns = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]
    output_table = pd.DataFrame(table_rows, columns=columns)
    # Load expected CSV content
    expected_table = pd.read_csv(
        f"tests/test_data/tables/parsed/{json_file.replace('.json', f'_table{tableNo}.csv')}"
    )
    expected_table = expected_table.fillna("")
    # Compare the cells of the output table with the expected table
    for i, (row, expected_row) in enumerate(
        zip(output_table.iterrows(), expected_table.iterrows())
    ):
        for j, (cell, expected_cell) in enumerate(zip(row[1], expected_row[1])):
            if cell != expected_cell:
                print(
                    f"Cell mismatch at ({i}, {j}): expected '{expected_cell}', got '{cell}'"
                )
    pd.testing.assert_frame_equal(expected_table, output_table)

@pytest.mark.parametrize(
    "pdf_file",
    [
        "2820-01.pdf",
        "JGI A2LA Cert 2820.01 Exp 03-2025.pdf",
    ],
)
def test_whole_files(pdf_file):
    """Test the custom_parse_table function with JSON input and expected CSV output."""
    # Load input JSON
    table = pdf_table_processor(f"tests/test_data/{pdf_file}")

    # Check for unexpected cmc_mult_unit values
    for removed in ['D', 'L', 'W']:
        assert not any(table['cmc_mult_unit'] == removed), f"Unexpected cmc_mult_unit '{removed}' found in the data."

    # Make sure the table is not empty
    assert not table.empty, "Table is empty"

    # Check the columns
    expected_columns = ['Equipment', 'Parameter', 'Range', 'Frequency', 'CMC (±)', 'Comments', 'range_min', 'range_min_unit', 'range_max', 'range_max_unit', 'frequency_range_min', 'frequency_range_min_unit', 'frequency_range_max', 'frequency_range_max_unit', 'cmc_base', 'cmc_multiplier', 'cmc_mult_unit', 'cmc_uncertainty_unit']
    assert table.columns.tolist() == expected_columns, f"Columns mismatch: expected {expected_columns}, got {table.columns.tolist()}"
    
    # Make sure no columns are empty
    for column in table.columns:
        assert not table[column].isnull().all(), f"Column {column} is empty"

    # Make sure no rows are empty
    for index, row in table.iterrows():
        assert not row.isnull().all(), f"Row {index} is empty"

    pass