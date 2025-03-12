import pytest
from src.cmc import parse_cmc, CMC


@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("(36 + 2.3D) µin", CMC("36", "2.3", "D", "µin")),
        ("(7.8 + 3.8L) µin", CMC("7.8", "3.8", "L", "µin")),
        ("27 µin", CMC("27", 0, None, "µin")),
        ("0.43 parts in 10", CMC("0.43", 0, None, "parts in 10")),
        ("0.013 % of magnification", CMC("0.013", 0, None, "% of magnification")),
        ("---", CMC(None, None, None, None)),
    ]
)
def test_parse_cmc(input_text, expected):
    assert parse_cmc(input_text) == expected
