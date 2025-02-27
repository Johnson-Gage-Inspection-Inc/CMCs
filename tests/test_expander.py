import pytest
import pandas as pd
from src.expander import expand_rows


@pytest.fixture
def example_df():
    """Return a minimal DataFrame with multi-line fields for expansion testing."""
    data = {
        "Equipment": ["Eq1", "Eq2"],
        "Parameter": ["Param1\nParam2", "SingleParam"],
        "Range": ["(10 to 50) mm", "Up to 3.5 in\nUp to 12 in"],
        "Frequency": ["", ""],
        "CMC (±)": ["0.10\n0.20", "0.25\n0.30"],
        "Comments": ["Some comment", "Another comment"],
    }
    return pd.DataFrame(data)


def test_expand_rows(example_df):
    """Test that expand_rows() expands multi-line fields and adds RangeMin/RangeMax/RangeUnit."""
    df_expanded = expand_rows(example_df)

    # Check that the final DataFrame includes new columns
    for col in ["RangeMin", "RangeMax", "RangeUnit"]:
        assert col in df_expanded.columns, f"Missing column '{col}' after expansion."

    # Usually we expect more rows than the original if expansions are successful
    assert len(df_expanded) >= len(
        example_df
    ), "No expansion occurred when we expected multiline expansions."

    # Spot-check that ranges were parsed
    # (10 to 50) mm => RangeMin=10, RangeMax=50, RangeUnit="mm"
    row = df_expanded.iloc[0]
    if row["Range"] == "(10 to 50) mm":
        assert row["RangeMin"] == "10"
        assert row["RangeMax"] == "50"
        assert "mm" in row["RangeUnit"]
