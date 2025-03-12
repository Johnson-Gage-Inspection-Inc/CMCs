import re


class budget(dict):
    base: float
    multiplier: float
    mult_unit: str
    uncertainty_unit: str

    def __init__(s, base: float, multiplier: float, mult_unit: str, uncertainty_unit: str) -> None:
        s.base = base
        s.multiplier = multiplier
        s.mult_unit = mult_unit
        s.uncertainty_unit = uncertainty_unit

    def __eq__(s, other):
        if not isinstance(other, budget):
            return False
        return all(
            s.base == other.base,
            s.multiplier == other.multiplier,
            s.mult_unit == other.mult_unit,
            s.uncertainty_unit == other.uncertainty_unit
        )

    def __repr__(s):
        return (f"budget({s.base!r}, {s.multiplier!r}, "
                f"{s.mult_unit!r}, {s.uncertainty_unit!r})")

    # Add method to allow list coercion (i.e. list(budget_instance))
    def __list__(s):
        return [s.base, s.multiplier, s.mult_unit, s.uncertainty_unit]

    # Add method to allow pd.Series coercion (i.e. pd.Series(budget_instance))
    def __series__(s):
        import pandas as pd
        return pd.Series(s.__list__())


def parse_budget(input_text: str) -> budget:
    """
    Parse the CMC (±) column's linear equation into four components:
      base, multiplier, multiplier conversion unit, and uncertainty unit.

    Expected formats:
      Format A: "<base> + <multiplier>[<mult_unit>] ± <uncertainty_value>[<uncertainty_unit>]"
        e.g. "10+0.2m±0.05m"  --> ("10", "0.2", "m", "m")
      Format B: "(<base> + <multiplier>[<mult_unit>]) <uncertainty_unit>"
        e.g. "(36 + 2.3D) µin"  --> ("36", "2.3", "D", "µin")

    If the text does not match either expected format or is a placeholder (like '---'),
    returns a tuple with the original text as the first element (or None for placeholders)
    and None for the other components.
    """
    text = input_text.strip()
    # Handle placeholders.
    if text == "---" or not text:
        return budget(None, None, None, None)

    # Handle case without a plus sign (e.g., "27 µin")
    if '+' not in text:
        parts = text.split(maxsplit=1)
        base = parts[0]
        uncertainty_unit = parts[1] if len(parts) > 1 else ''
        return budget(base, 0, None, uncertainty_unit)

    patterns = [
        # Pattern A: With '±' and uncertainty numeric value.
        r'^\s*\(?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)(?:\s*([A-Za-zμµ/%]+))?\s*\)?\s*±\s*[+-]?\d+(?:\.\d+)?\s*([A-Za-zμµ/%]+)\s*$',
        # Pattern B: Without '±' (uncertainty numeric value omitted)
        r'^\s*\(?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)(?:\s*([A-Za-zμµ/%]+))?\s*\)?\s*([A-Za-zμµ/%]+)\s*$',
    ]
    for i, pattern in enumerate(patterns):
        if match := re.match(pattern, text):
            base = match.group(1)
            multiplier = match.group(2)
            mult_unit = match.group(3) if match.group(3) else ""
            uncertainty_unit = match.group(4)
            return budget(base, multiplier, mult_unit, uncertainty_unit)
    return budget(text, None, None, None)
