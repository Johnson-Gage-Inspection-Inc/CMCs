import pytest
from src.expander import parse_range


@pytest.mark.parametrize(
    "input_text, expected_min, expected_min_unit, expected_max, expected_max_unit",
    [
        # Standard Cases
        ("(10 to 50) mm", "10", "mm", "50", "mm"),
        ("Up to 600 in", None, None, "600", "in"),
        ("3.5 to 27 in", "3.5", "in", "27", "in"),
        ("-0.0015 to +0.0015 in", "-0.0015", "in", "0.0015", "in"),
        ("120 µin", "120", "µin", "120", "µin"),
        ("> 62 % IACS", "62", "% IACS", None, None),  # Greater than parsing
        ("Up to 16 % IACS", None, "16", "% IACS"),
        ('100 nA to 1 µA', '100', '1', 'µA'),
        # Edge Cases
        ("Up to 9 in", None, "9", "in"),
        (
            "(200 to 10 000) psi",
            "200",
            "10000",
            "psi",
        ),  # Handles extra spaces in numbers
        ("Up to 1 in", None, "1", "in"),
        ("> 600 HV", "600", None, "HV"),  # Greater than parsing
        ("< 250 HK", None, "250", "HK"),  # Less than parsing
        ("---", None, None, "---"),  # Placeholder value
        ("±180º", "-180", "180", "º"),  # Plus/minus parsing
        # Unexpected Cases
        ("(3 to 11) A", "3", "11", "A"),
        ("100 mA to 1 A", "100", "1", "A"),
    ],
)
def test_parse_range(input_text, expected_min, expected_max, expected_unit):
    assert parse_range(input_text) == (expected_min, expected_max, expected_unit)
