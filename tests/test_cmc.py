import pytest
from src.cmc import parse_cmc


@pytest.mark.parametrize(
    "input_text, expected",
    [
        # Standard case with multiplier unit present.
        ("10 + 0.2m ± 0.05m", ("10", "0.2", "m", "m")),
        # Variant without extra spaces.
        ("10+0.2m±0.05m", ("10", "0.2", "m", "m")),
        # Case with no multiplier conversion unit.
        ("10 + 0.2 ± 0.05m", ("10", "0.2", "", "m")),
        # Case with negative numbers.
        ("-10 + -0.2m ± -0.05m", ("-10", "-0.2", "m", "m")),
        # Case missing uncertainty unit – should fail to match and return the original text.
        ("10 + 0.2m ± 0.05", ("10 + 0.2m ± 0.05", None, None, None)),
        # Completely invalid input.
        ("Not a valid string", ("Not a valid string", None, None, None)),
        # Placeholder value.
        ("---", (None, None, None, None)),
    ]
)
def test_parse_cmc(input_text, expected):
    assert parse_cmc(input_text) == expected
