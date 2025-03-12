import re


class CMC(dict):
    base: float
    multiplier: float
    mult_unit: str
    uncertainty_unit: str

    def __init__(self, base: float, multiplier: float, mult_unit: str, uncertainty_unit: str) -> None:
        self.base = base
        self.multiplier = multiplier
        self.mult_unit = mult_unit
        self.uncertainty_unit = uncertainty_unit

    def __eq__(self, other):
        if not isinstance(other, CMC):
            return False
        return (
            self.base == other.base and
            self.multiplier == other.multiplier and
            self.mult_unit == other.mult_unit and
            self.uncertainty_unit == other.uncertainty_unit
        )

    def __repr__(self):
        return (f"CMC({self.base!r}, {self.multiplier!r}, "
                f"{self.mult_unit!r}, {self.uncertainty_unit!r})")


def parse_cmc(input_text: str) -> CMC:
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
        return CMC(None, None, None, None)

    # Handle case without a plus sign (e.g., "27 µin")
    if '+' not in text:
        parts = text.split(maxsplit=1)
        base = parts[0]
        uncertainty_unit = parts[1] if len(parts) > 1 else ''
        return CMC(base, 0, None, uncertainty_unit)

    patterns = [
        # Pattern A: With '±' and uncertainty numeric value.
        r'^\s*\(?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)(?:\s*([A-Za-zμµ/%]+))?\s*\)?\s*±\s*[+-]?\d+(?:\.\d+)?\s*([A-Za-zμµ/%]+)\s*$',
        # Pattern B: Without '±' (uncertainty numeric value omitted)
        r'^\s*\(?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)(?:\s*([A-Za-zμµ/%]+))?\s*\)?\s*([A-Za-zμµ/%]+)\s*$',
        # Pattern C: Without multiplier and mult_unit
        r'^\s*([+-]?\d+(?:\.\d+)?)\s*([A-Za-zμµ/%\s]+)\s*$',
    ]
    for i, pattern in enumerate(patterns):
        if match := re.match(pattern, text):
            base = match.group(1)
            multiplier = match.group(2)
            mult_unit = match.group(3) if match.group(3) else ""
            uncertainty_unit = match.group(4)
            return CMC(base, multiplier, mult_unit, uncertainty_unit)
    return CMC(text, None, None, None)
