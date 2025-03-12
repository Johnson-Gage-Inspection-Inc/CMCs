import pytest
from src.range import parse_range


@pytest.mark.parametrize(
    "input_text, expected_min, expected_min_unit, expected_max, expected_max_unit",
    [
        # Standard Cases
        ("(10 to 50) mm", "10", "mm", "50", "mm"),
        ("(3 to 11) A", "3", "A", "11", "A"),
        ("Up to 9 in", None, None, "9", "in"),
        ("Up to 600 in", None, None, "600", "in"),
        ("Up to 16 % IACS", None, None, "16", "% IACS"),
        ("100 mA to 1 A", "100", "mA", "1", "A"),  # Different units
        ("3.5 to 27 in", "3.5", "in", "27", "in"),
        (
            "-0.0015 to +0.0015 in",
            "-0.0015",
            "in",
            "0.0015",
            "in",
        ),  # Plus/minus parsing
        ("120 µin", "120", "µin", "120", "µin"),  # Single value
        ("> 62 % IACS", "62", "% IACS", None, None),  # Greater than parsing
        ("> 600 HV", "600", "HV", None, None),  # Greater than parsing
        ("< 250 HK", None, None, "250", "HK"),  # Less than parsing
        ("100 nA to 1 µA", "100", "nA", "1", "µA"),
        # Edge Cases
        (
            "(200 to 10 000) psi",
            "200",
            "psi",
            "10000",
            "psi",
        ),  # Handles extra spaces in numbers
        ("Up to 1 in", None, None, "1", "in"),
        ("---", None, None, "---", "---"),  # Placeholder value
        ("±180º", "-180", "º", "180", "º"),  # Plus/minus parsing
        (
            "(-112 °F to 32) °F",
            "-112",
            "°F",
            "32",
            "°F",
        ),  # min unit same as max unit, but in parentheses
        ("(> 225 to 650) HBW", "225", "HBW", "650", "HBW"),  # Greater than parsing
        ("≤ 225 HBW", None, None, "225", "HBW"),  # Less than or equal to parsing
        ("5X to 100X", "5", "X", "100", "X"),  # X as a unit (Magnification)
    ],
)
def test_parse_range(
    input_text, expected_min, expected_min_unit, expected_max, expected_max_unit
):
    assert parse_range(input_text) == (
        expected_min,
        expected_min_unit,
        expected_max,
        expected_max_unit,
    )
