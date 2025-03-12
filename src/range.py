import re
from typing import Optional, Tuple


def parse_range(
    input_text: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    text = input_text.strip()

    def normalize(num_str: str) -> str:
        # Remove inner spaces and any leading '+'
        return num_str.replace(" ", "").lstrip("+")

    def extract_value(s: str) -> Tuple[str, str]:
        """
        Extract a numeric value and its unit from the string s.
        This function also strips any leading comparator symbols (>, <, ≤, ≥).
        """
        s = s.strip()
        # Remove any leading comparator symbols and whitespace.
        s = re.sub(r"^[><≤≥]+\s*", "", s)
        # Match a number (with optional decimals, spaces, or commas) followed by any unit.
        m = re.match(r"([+-]?\d+(?:[\d\s,\.]*\d)?)(.*)", s)
        if m:
            num = normalize(m.group(1))
            unit = m.group(2).strip()
            return num, unit
        return s, ""

    # Placeholder value.
    if text == "---":
        return (None, None, "---", "---")

    # Plus/minus notation.
    if text.startswith("±"):
        m = re.match(r"±\s*([+-]?\d+(?:[\d\s,\.]*\d)?)(.*)", text)
        if m:
            num = normalize(m.group(1))
            unit = m.group(2).strip()
            return ("-" + num, unit, num, unit)

    # "Up to" case.
    if text.lower().startswith("up to"):
        remainder = text[5:].strip()  # remove "Up to"
        num, unit = extract_value(remainder)
        return (None, None, num, unit)

    # Greater than: e.g. "> 62 % IACS" should yield (num, unit, None, None)
    if text.startswith(">"):
        remainder = text[1:].strip()
        num, unit = extract_value(remainder)
        return (num, unit, None, None)

    # Less than (or less than or equal to): e.g. "< 250 HK" or "≤ 225 HBW"
    if text.startswith("<") or text.startswith("≤"):
        remainder = re.sub(r"^[<≤]+\s*", "", text)
        num, unit = extract_value(remainder)
        return (None, None, num, unit)

    # Parentheses branch – this also covers cases where one side contains a comparator.
    if text.startswith("(") and ")" in text:
        m = re.match(r"^\((.*)\)\s*(.*)$", text)
        if m:
            inner_text = m.group(1).strip()  # e.g. "> 225 to 650"
            outer_unit = m.group(2).strip()  # e.g. "HBW"
            if "to" in inner_text:
                parts = inner_text.split("to")
                left_text = parts[0].strip()
                right_text = "to".join(parts[1:]).strip()
                num1, unit1 = extract_value(left_text)
                num2, unit2 = extract_value(right_text)
                # If a side doesn't provide its own unit, use the outer unit.
                if not unit1 and outer_unit:
                    unit1 = outer_unit
                if not unit2 and outer_unit:
                    unit2 = outer_unit
                return (num1, unit1, num2, unit2)

    # Generic "to" branch outside parentheses.
    if "to" in text:
        parts = text.split("to")
        if len(parts) >= 2:
            left = parts[0].strip()
            right = "to".join(parts[1:]).strip()
            num1, unit1 = extract_value(left)
            num2, unit2 = extract_value(right)
            if not unit1 and unit2:
                unit1 = unit2
            if not unit2 and unit1:
                unit2 = unit1
            return (num1, unit1, num2, unit2)

    # Single value case.
    num, unit = extract_value(text)
    return (num, unit, num, unit)
