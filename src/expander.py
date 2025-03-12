import re
from typing import Optional, Tuple


def parse_range(input_text: str) -> Tuple[Optional[str], Optional[str], str]:
    text = input_text.strip()

    # Special placeholder
    if text == "---":
        return (None, None, "---")

    def normalize(num_str: str) -> str:
        # Remove all spaces inside the number and strip any leading '+'
        return num_str.replace(" ", "").lstrip("+")

    # Handle ± notation: e.g. "±180º" => ("-180", "180", "º")
    if text.startswith("±"):
        m = re.match(r"±\s*([+-]?\d[\d\s\.,]*)\s*(.*)", text)
        if m:
            num = normalize(m.group(1))
            unit = m.group(2).strip()
            return ("-" + num, num, unit)

    # Handle "Up to" (case insensitive): e.g. "Up to 600 in"
    m = re.match(r"(?i)^Up\s+to\s+([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        number = normalize(m.group(1))
        unit = m.group(2).strip()
        return (None, number, unit)

    # Handle greater than: e.g. "> 62 % IACS"
    m = re.match(r"^>\s*([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        number = normalize(m.group(1))
        unit = m.group(2).strip()
        return (number, None, unit)

    # Handle less than: e.g. "< 250 HK"
    m = re.match(r"^<\s*([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        number = normalize(m.group(1))
        unit = m.group(2).strip()
        return (None, number, unit)

    # Handle explicit range in parentheses: e.g. "(10 to 50) mm"
    m = re.match(
        r"^\(\s*([+-]?\d[\d\s\.,]*)\s+to\s+([+-]?\d[\d\s\.,]*)\s*\)\s*(.*)", text
    )
    if m:
        num1 = normalize(m.group(1))
        num2 = normalize(m.group(2))
        unit = m.group(3).strip()
        return (num1, num2, unit)

    # Handle generic range with "to": e.g. "3.5 to 27 in" or "100 mA to 1 A"
    if "to" in text:
        parts = text.split("to")
        if len(parts) >= 2:
            left = parts[0].strip()
            right = "to".join(parts[1:]).strip()
            m_left = re.match(r"([+-]?\d[\d\s\.,]*)", left)
            num1 = normalize(m_left.group(1)) if m_left else None
            m_right = re.match(r"([+-]?\d[\d\s\.,]*)\s*(.*)", right)
            if m_right:
                num2 = normalize(m_right.group(1))
                unit = m_right.group(2).strip()
            else:
                num2 = None
                unit = ""
            return (num1, num2, unit)

    # Otherwise, assume a single numeric value with a unit: e.g. "120 µin" or "10 Hz"
    m = re.match(r"([+-]?\d[\d\s\.,]*)\s*(.*)", text)
    if m:
        num = normalize(m.group(1))
        unit = m.group(2).strip()
        return (None, num, unit)

    # Fallback: return the entire string as the unit
    return (None, None, text)
