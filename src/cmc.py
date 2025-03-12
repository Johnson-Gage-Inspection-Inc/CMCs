from typing import Optional


def parse_cmc(input_text: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse the CMC (±) column's linear equation into four components:
      base, multiplier, multiplier conversion unit, and uncertainty unit.
    Expected format: "<base> + <multiplier>[<mult_unit>] ± <uncertainty_value>[<uncertainty_unit>]"
    For example: "10 + 0.2m ± 0.05m"
      - base: "10"
      - multiplier: "0.2"
      - multiplier conversion unit: "m"
      - uncertainty unit: "m"
    If the text does not match the expected format or is a placeholder (like '---'),
    returns a tuple of Nones.
    """
    import re
    text = input_text.strip()
    if text == "---" or not text:
        return (None, None, None, None)

    # Regex pattern:
    #  - Group 1: base (number)
    #  - Group 2: multiplier (number)
    #  - Group 3: optional multiplier conversion unit (letters, μ, µ, %, etc.)
    #  - Skip over the uncertainty numeric value (we assume we only want its unit)
    #  - Group 4: uncertainty unit (required)
    pattern = r'^\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)(?:\s*([A-Za-zμµ/%]+))?\s*±\s*[+-]?\d+(?:\.\d+)?\s*([A-Za-zμµ/%]+)\s*$'
    m = re.match(pattern, text)
    if m:
        base = m.group(1)
        multiplier = m.group(2)
        mult_unit = m.group(3) if m.group(3) else ""
        uncertainty_unit = m.group(4)
        return (base, multiplier, mult_unit, uncertainty_unit)
    else:
        # If no match, you can decide to raise an error, return None values,
        # or simply return the original string as the base.
        return (text, None, None, None)
