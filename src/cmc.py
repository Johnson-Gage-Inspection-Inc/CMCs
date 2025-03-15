from re import match as re_match, search


class budget(dict):
    base: float
    multiplier: float
    mult_unit: str
    uncertainty_unit: str

    def __init__(
        s, base: float, multiplier: float, mult_unit: str, uncertainty_unit: str
    ) -> None:
        s.base = base
        s.multiplier = multiplier
        s.mult_unit = mult_unit
        s.uncertainty_unit = uncertainty_unit

    def __eq__(s, other):
        if not isinstance(other, budget):
            return False
        return all(
            [
                s.base == other.base,
                s.multiplier == other.multiplier,
                s.mult_unit == other.mult_unit,
                s.uncertainty_unit == other.uncertainty_unit,
            ]
        )

    def __repr__(s):
        return (
            f"budget({s.base!r}, {s.multiplier!r}, "
            f"{s.mult_unit!r}, {s.uncertainty_unit!r})"
        )

    # Add method to allow list coercion (i.e. list(budget_instance))
    def __list__(s):
        return [s.base, s.multiplier, s.mult_unit, s.uncertainty_unit]

    # Add method to allow pd.Series coercion (i.e. pd.Series(budget_instance))
    def __series__(s):
        import pandas as pd

        return pd.Series(s.__list__())


def parse_num_unit(s: str, force_float: bool = False):
    """
    Extract a numeric portion and the rest of the string.
    If force_float is True, always return the number as a float.
    Otherwise, return a float only if the numeric string contains a dot,
    else leave it as a string.
    """
    s = s.strip()
    match = re_match(r"^([+-]?\d+(?:\.\d+)?)(.*)$", s)
    if not match:
        return s, ""
    num_str, unit_str = match.group(1), match.group(2).strip()
    if force_float:
        try:
            num = float(num_str)
        except ValueError:
            num = num_str
    else:
        if "." in num_str:
            num = float(num_str)
        else:
            num = num_str
    return num, unit_str


def parse_budget(input_text: str) -> budget:
    """
    Parse the CMC (±) column's linear equation into it's four components.

    Args:
        input_text (str): The text to parse.

    Returns:
        budget: (base, multiplier, mult_unit, uncertainty_unit)
    """
    text = input_text.strip()
    # Handle placeholders.
    if text == "---" or not text:
        return budget(None, None, None, None)

    # If there's a plus sign, we assume a two-part expression.
    if "+" in text:
        # Case 1: Parenthesized expression like "(36 + 2.3D) µin"
        if text.startswith("("):
            # Expect format: (<base> + <multiplier>[unit]) <uncertainty_unit>
            closing_index = text.find(")")
            inner = text[1:closing_index].strip()
            outer = text[closing_index + 1:].strip()  # uncertainty unit
            if (closing_index == -1) or ("+" not in inner):
                # Malformed; fall through to generic handling
                return budget(text, None, None, None)
            left_inner, right_inner = inner.split("+", 1)
            left_inner = left_inner.strip()
            right_inner = right_inner.strip()
            left_val, left_unit = parse_num_unit(left_inner, force_float=True)
            right_val, right_unit = parse_num_unit(right_inner, force_float=True)
            # If the base part had an attached unit, use it;
            # otherwise, fall back to the multiplier part’s attached unit.
            if left_unit:
                return budget(right_val, left_unit, left_unit, outer)
            elif right_unit:
                return budget(left_val, right_val, right_unit, outer)
            # Malformed; fall through to generic handling
            return budget(text, None, None, None)
        else:
            # Case 2: No parentheses; expect format like "0.034 % + 3.6 µV" or "1.3 % rdg + 120 µF"
            left, right = text.split("+", 1)
            left = left.strip()
            right = right.strip()
            mult_val, left_unit = parse_num_unit(left, force_float=True)
            base_val, right_unit = parse_num_unit(right, force_float=True)
            # In this format, the left part’s unit is taken as the multiplier conversion unit.
            return budget(
                base_val, mult_val, left_unit if left_unit else "", right_unit
            )
    else:
        if text.__contains__("%"):
            pattern = r"([+-]?\d+(?:\.\d+)?)(?=\s*% rdg)"
            if match := search(pattern, text):
                mult_val = float(match.group(1))
                return budget(0, mult_val, "% rdg", None)
            else:
                base_val, rest = parse_num_unit(text, force_float=True)
                return budget(base_val, 0, None, rest)
        # No plus sign. Expect format: "<number> <uncertainty_unit>"
        # Split on first whitespace.
        if parts := text.split(maxsplit=1):
            base_str = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            base_val, _ = parse_num_unit(base_str, force_float=False)
            return budget(base_val, 0, None, rest.strip())
        return budget(text, None, None, None)
