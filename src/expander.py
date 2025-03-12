import re
from typing import Optional, Tuple


def parse_range(
    input_text: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    text = input_text.strip()

    def normalize(num_str: str) -> str:
        # Remove spaces within numbers and strip any leading '+'
        return num_str.replace(" ", "").lstrip("+")

    # Special placeholder: e.g. "---"
    if text == "---":
        return (None, None, "---", "---")

    # Handle ± notation: e.g. "±180º" -> ("-180", "º", "180", "º")
    if text.startswith("±"):
        m = re.match(r"±\s*([+-]?\d[\d\s\.,]*)\s*(.*)", text)
        if m:
            num = normalize(m.group(1))
            unit = m.group(2).strip()
            return ("-" + num, unit, num, unit)

    # Handle "Up to" (case insensitive): e.g. "Up to 600 in" -> (None, None, "600", "in")
    m = re.match(r"(?i)^Up\s+to\s+([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        number = normalize(m.group(1))
        unit = m.group(2).strip()
        return (None, None, number, unit)

    # Handle greater than: e.g. "> 62 % IACS" -> ("62", "% IACS", None, None)
    m = re.match(r"^>\s*([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        number = normalize(m.group(1))
        unit = m.group(2).strip()
        return (number, unit, None, None)

    # Handle less than: e.g. "< 250 HK" -> (None, None, "250", "HK")
    m = re.match(r"^<\s*([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        number = normalize(m.group(1))
        unit = m.group(2).strip()
        return (None, None, number, unit)

    # Handle explicit range in parentheses – now with potential left-side units.
    m = re.match(r"^\((.*)\)\s*(.*)$", text)
    if m:
        inner_text = m.group(1).strip()  # e.g. "-112 °F to 32"
        outer_unit = m.group(2).strip()  # e.g. "°F"
        if "to" in inner_text:
            parts = inner_text.split("to")
            left_text = parts[0].strip()  # e.g. "-112 °F"
            right_text = "to".join(parts[1:]).strip()  # e.g. "32"
            left_match = re.match(r"^([+-]?\d[\d\s\.,]*)(?:\s+(.+))?$", left_text)
            right_match = re.match(r"^([+-]?\d[\d\s\.,]*)(?:\s+(.+))?$", right_text)
            if left_match and right_match:
                num1 = normalize(left_match.group(1))
                unit1 = left_match.group(2).strip() if left_match.group(2) else ""
                num2 = normalize(right_match.group(1))
                unit2 = right_match.group(2).strip() if right_match.group(2) else ""
                # Use the outer unit if a side doesn't provide one
                if not unit1 and outer_unit:
                    unit1 = outer_unit
                if not unit2 and outer_unit:
                    unit2 = outer_unit
                return (num1, unit1, num2, unit2)

    # Handle generic range with "to" outside of parentheses.
    if "to" in text:
        parts = text.split("to")
        if len(parts) >= 2:
            left = parts[0].strip()
            right = "to".join(parts[1:]).strip()
            m_left = re.match(r"^([+-]?\d[\d\s\.,]*)(?:\s+(.+))?$", left)
            m_right = re.match(r"^([+-]?\d[\d\s\.,]*)(?:\s+(.+))?$", right)
            if m_left and m_right:
                num1 = normalize(m_left.group(1))
                unit1 = m_left.group(2).strip() if m_left.group(2) else ""
                num2 = normalize(m_right.group(1))
                unit2 = m_right.group(2).strip() if m_right.group(2) else ""
                # If one unit is missing, try to fill it from the other side.
                if not unit1 and unit2:
                    unit1 = unit2
                if not unit2 and unit1:
                    unit2 = unit1
                return (num1, unit1, num2, unit2)

    # Otherwise, assume a single value with a unit (applies to both min and max).
    m = re.match(r"^([+-]?\d[\d\s\.,]*)(?:\s+(.+))?$", text)
    if m:
        num = normalize(m.group(1))
        unit = m.group(2).strip() if m.group(2) else ""
        return (num, unit, num, unit)

    # Fallback: return the entire string as unit for max (should rarely happen).
    return (None, None, text, text)
