import pytest
from src.ExtractCMCsFromPDF import parse_range


@pytest.mark.parametrize("input_text, expected_min, expected_max, expected_unit", [
    # Standard Cases
    ("(10 to 50) mm", "10", "50", "mm"),
    ("Up to 600 in", None, "600", "in"),
    ("3.5 to 27 in", "3.5", "27", "in"),
    ("-0.0015 to +0.0015 in", "-0.0015", "+0.0015", "in"),
    ("120 µin", None, "120", "µin"),

    # Edge Cases
    ("Up to 9 in", None, "9", "in"),
    ("(200 to 10 000) psi", "200", "10000", "psi"),  # Handles extra spaces in numbers
    ("Up to 1 in", None, "1", "in"),
    ("> 600 HV", None, "600", "HV"),  # Greater than parsing
    ("< 250 HK", "250", None, "HK"),  # Less than parsing
    ("---", None, None, "---"),  # Placeholder value

    # Unexpected Cases
    ("Knoop:", None, None, "Knoop:"),  # Likely a label, not a range
    ("10 Hz", None, "10", "Hz"),  # Single value
    ("(3 to 11) A", "3", "11", "A"),
    ("100 mA to 1 A", "100", "1", "A"),
])
def test_parse_range(input_text, expected_min, expected_max, expected_unit):
    assert parse_range(input_text) == (expected_min, expected_max, expected_unit)
