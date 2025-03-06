import pytest
import os
import pandas as pd
from src.ExtractCMCsFromPDF import extract_pdf_tables_to_df
from src.reader import parse_page_table
from src.reader import distribute_multi_line_parameter


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
def test_parse_page_table_with_detailed_diff(table_file):
    """Test parse_page_table with detailed diff output when comparison fails."""
    # Load the input table
    input_path = f"tests/test_data/tables/pre/{table_file}"
    input_df = pd.read_csv(input_path)

    # Process the table
    result_df = parse_page_table(input_df.copy())
    result_df = result_df.reset_index(drop=True)

    # Load the expected output
    expected_path = f"tests/test_data/tables/parsed/{table_file}"
    expected_df = pd.read_csv(expected_path).fillna("")
    expected_df = expected_df.reset_index(drop=True)

    # Compare shape first for easier debugging
    if result_df.shape != expected_df.shape:
        pytest.fail(
            f"DataFrame shapes don't match!\n"
            f"Expected shape: {expected_df.shape}\n"
            f"Got shape: {result_df.shape}\n"
        )

    # Compare columns
    if list(result_df.columns) != list(expected_df.columns):
        pytest.fail(
            f"DataFrame columns don't match!\n"
            f"Expected columns: {list(expected_df.columns)}\n"
            f"Got columns: {list(result_df.columns)}\n"
        )

    # Detailed row-by-row comparison with differences highlighted
    try:
        pd.testing.assert_frame_equal(result_df, expected_df, check_dtype=False)
    except AssertionError:
        # Get the differences in a readable format
        diffs = []
        for i in range(min(len(result_df), len(expected_df))):
            for col in result_df.columns:
                if col in expected_df.columns:
                    expected_val = expected_df.loc[i, col]
                    actual_val = result_df.loc[i, col]
                    if expected_val != actual_val:
                        diffs.append(
                            f"Row {i}, Column '{col}':\n"
                            f"  Expected (-want): {expected_val}\n"
                            f"  Got (+got):      {actual_val}\n"
                        )

        # Add info about any extra or missing rows
        if len(result_df) > len(expected_df):
            diffs.append(
                f"Extra rows in result: {len(result_df) - len(expected_df)}"
            )
        elif len(result_df) < len(expected_df):
            diffs.append(
                f"Missing rows in result: {len(expected_df) - len(result_df)}"
            )

        # Fail with detailed information
        pytest.fail("DataFrames are not equal:\n" + "\n".join(diffs))


def test_distribute_multi_line_parameter():
    """Test the distribute_multi_line_parameter function using the saved intermediate files."""

    # Load the first pass DataFrame (input to distribute_multi_line_parameter)
    input_path = "tests/test_data/tables/expanded/first_pass.csv"
    input_df = pd.read_csv(input_path).fillna("")

    # Convert DataFrame to list of dictionaries like the function expects
    first_pass_data = input_df.to_dict('records')

    # Process the data
    result_df = distribute_multi_line_parameter(first_pass_data)
    result_df = result_df.reset_index(drop=True)

    # Load the expected output
    expected_path = "tests/test_data/tables/parsed/page1_table0.csv"
    expected_df = pd.read_csv(expected_path).fillna("")
    expected_df = expected_df.reset_index(drop=True)

    # Compare shape first for easier debugging
    if result_df.shape != expected_df.shape:
        pytest.fail(
            f"DataFrame shapes don't match!\n"
            f"Expected shape: {expected_df.shape}\n"
            f"Got shape: {result_df.shape}\n"
        )

    # Compare columns
    if list(result_df.columns) != list(expected_df.columns):
        pytest.fail(
            f"DataFrame columns don't match!\n"
            f"Expected columns: {list(expected_df.columns)}\n"
            f"Got columns: {list(result_df.columns)}\n"
        )

    # Detailed row-by-row comparison with differences highlighted
    try:
        pd.testing.assert_frame_equal(result_df, expected_df, check_dtype=False)
    except AssertionError:
        # Get the differences in a readable format
        diffs = []
        for i in range(min(len(result_df), len(expected_df))):
            for col in result_df.columns:
                if col in expected_df.columns:
                    expected_val = expected_df.loc[i, col]
                    actual_val = result_df.loc[i, col]
                    if expected_val != actual_val:
                        diffs.append(
                            f"Row {i}, Column '{col}':\n"
                            f"  Expected (-want): {expected_val}\n"
                            f"  Got (+got):      {actual_val}\n"
                        )

        # Add info about any extra or missing rows
        if len(result_df) > len(expected_df):
            diffs.append(
                f"Extra rows in result: {len(result_df) - len(expected_df)}"
            )
        elif len(result_df) < len(expected_df):
            diffs.append(
                f"Missing rows in result: {len(expected_df) - len(result_df)}"
            )

        # Fail with detailed information
        pytest.fail("DataFrames are not equal:\n" + "\n".join(diffs))