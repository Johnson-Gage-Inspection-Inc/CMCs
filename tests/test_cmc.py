import pytest
from src.cmc import parse_budget, budget


@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("(36 + 2.3D) µin", budget("36", "2.3", "D", "µin")),
        ("(7.8 + 3.8L) µin", budget("7.8", "3.8", "L", "µin")),
        ("27 µin", budget("27", 0, None, "µin")),
        ("0.43 parts in 10", budget("0.43", 0, None, "parts in 10")),
        ("0.013 % of magnification", budget("0.013", 0, None, "% of magnification")),
        ("---", budget(None, None, None, None)),
    ]
)
def test_parse_cmc(input_text, expected):
    assert parse_budget(input_text) == expected
