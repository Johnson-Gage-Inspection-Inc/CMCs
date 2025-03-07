import pandas as pd
import re
from collections import defaultdict
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# (Optionally import from a "utils.py" if you want smaller functions)
# from .utils import remove_superscripts, split_parameter_equipment, split_parameter_range


def remove_superscripts(text):
    if not text:
        return text
    return re.sub(r"[\u00B2\u00B3\u00B9\u2070-\u209F\d]$", "", text)


def split_parameter_equipment(cell_value):
    if not cell_value:
        return ("", "")
    split_cols = re.split(r"\s*[-–]\s*", cell_value, maxsplit=1)
    if len(split_cols) == 2:
        equipment, param = split_cols
        return (equipment.strip(), param.strip())
    else:
        # If there is no dash, treat the entire thing as Equipment
        return (cell_value.strip(), "")


def split_parameter_range(cell_value):
    """Split a Parameter/Range cell into separate parameter and range values.
    Preserves all content rather than just first/last lines."""
    if not cell_value:
        return ("", "")

    # Convert to string if needed
    if not isinstance(cell_value, str):
        cell_value = str(cell_value)

    lines = [ln.strip() for ln in cell_value.splitlines() if ln.strip()]
    if len(lines) == 1:
        return (lines[0], "")
    elif len(lines) > 1:
        # Extract parameter (first line) and combine all remaining lines as range
        param = lines[0]
        range_val = "\n".join(lines[1:])
        return (param, range_val)
    else:
        return ("", "")


def cleanColumn(col):
    # Example: remove '(cont)' from the strings
    return col.str.replace(r"\(cont\)", "", regex=True).str.strip()


def param_lines_are_thermocouples(lines):
    pattern = re.compile(r"^Type\s+[A-Za-z0-9]", re.IGNORECASE)
    for ln in lines:
        ln = ln.strip()
        if ln and not pattern.match(ln):
            return False
    return True


def segment_by_blank_lines(lines):
    segments = []
    current_seg = []
    for line in lines:
        if not line.strip():
            if current_seg:
                segments.append(current_seg)
                current_seg = []
        else:
            current_seg.append(line)
    if current_seg:
        segments.append(current_seg)
    return segments


def dynamic_expand_row(row):
    param_txt = row.get("Parameter", "")
    rng_txt = row.get("Range", "")
    cmc_txt = row.get("CMC (±)", "")

    # Convert to strings and ensure consistent line breaks
    param_lines = str(param_txt).replace("\r\n", "\n").splitlines() if param_txt else []
    range_lines = str(rng_txt).replace("\r\n", "\n").splitlines() if rng_txt else []
    cmc_lines = str(cmc_txt).replace("\r\n", "\n").splitlines() if cmc_txt else []

    # Normalize empty lines
    param_lines = [ln.strip() for ln in param_lines if ln.strip()]
    range_lines = [ln.strip() for ln in range_lines if ln.strip()]
    cmc_lines = [ln.strip() for ln in cmc_lines if ln.strip()]

    range_segments = segment_by_blank_lines(range_lines)
    cmc_segments = segment_by_blank_lines(cmc_lines)

    # If mismatch:
    if len(range_segments) != len(cmc_segments):
        if len(range_lines) > 1:
            new_rows = []
            if len(range_lines) == len(cmc_lines):
                for r, c in zip(range_lines, cmc_lines):
                    nr = row.to_dict()
                    nr["Range"] = r
                    nr["CMC (±)"] = c
                    new_rows.append(nr)
            else:
                for r in range_lines:
                    nr = row.to_dict()
                    nr["Range"] = r
                    nr["CMC (±)"] = cmc_txt
                    new_rows.append(nr)
            return new_rows
        else:
            new_row = row.to_dict()
            new_row["Range"] = range_lines[0] if range_lines else ""
            new_row["CMC (±)"] = cmc_lines[0] if cmc_lines else ""
            return [new_row]

    # Flatten
    flattened = []
    for r_seg, c_seg in zip(range_segments, cmc_segments):
        for r, c in zip(r_seg, c_seg):
            flattened.append((r, c))

    total_range_lines = len(flattened)
    if param_lines and len(param_lines) == total_range_lines:
        out = []
        for i, (r, c) in enumerate(flattened):
            nr = row.to_dict()
            nr["Parameter"] = param_lines[i]
            nr["Range"] = r
            nr["CMC (±)"] = c
            out.append(nr)
        return out
    else:
        out = []
        for r, c in flattened:
            nr = row.to_dict()
            nr["Range"] = r
            nr["CMC (±)"] = c
            out.append(nr)
        return out


def distribute_multi_line_parameter(expanded_rows):
    out = []

    def row_key(r):
        return (r.get("Equipment", ""), r.get("Comments", ""))

    grouped = defaultdict(list)
    for row in expanded_rows:
        grouped[row_key(row)].append(row)

    for _, group_rows in grouped.items():
        if len(group_rows) == 1:
            out.extend(group_rows)
            continue

        distinct_params = {r["Parameter"] for r in group_rows}
        if len(distinct_params) > 1:
            out.extend(group_rows)
            continue

        param_text = next(iter(distinct_params))
        plines = [ln.strip() for ln in param_text.splitlines() if ln.strip()]

        if len(plines) <= 1:
            out.extend(group_rows)
            continue

        if param_lines_are_thermocouples(plines):
            # replicate each row for each line
            for row_item in group_rows:
                for tline in plines:
                    nr = dict(row_item)
                    nr["Parameter"] = tline
                    out.append(nr)
        else:
            expansions_count = len(group_rows)
            param_count = len(plines)
            if expansions_count % param_count == 0:
                chunk_size = expansions_count // param_count
                chunks = [
                    group_rows[i: i + chunk_size]
                    for i in range(0, expansions_count, chunk_size)
                ]
                for i, chunk in enumerate(chunks):
                    line_val = plines[i]
                    for row_item in chunk:
                        nr = dict(row_item)
                        nr["Parameter"] = line_val
                        out.append(nr)
            else:
                out.extend(group_rows)

    df_expanded = pd.DataFrame(out)
    # Remove any remaining linebreaks from each cell
    for col in df_expanded.columns:
        df_expanded[col] = df_expanded[col].apply(
            lambda x: str(x).replace("\n", " ").strip()
        )
    return df_expanded


def expand_multi_line_rows(df):
    first_pass = []
    logging.debug(f"Original rows: {len(df)}")
    for _, row in df.iterrows():
        rng = row.get("Range", "")
        if len(rng.splitlines()) > 1:
            new_rows = dynamic_expand_row(row)
            logging.debug(f"Expanded 1 row into {len(new_rows)} rows")
            first_pass.extend(new_rows)
        else:
            first_pass.append(row.to_dict())

    logging.debug(f"After first pass: {len(first_pass)} rows")
    second_pass = distribute_multi_line_parameter(first_pass)
    logging.debug(f"After second pass: {len(second_pass)} rows")
    return second_pass


def extract_tables_by_position(page):
    """Extract table data using positional information of text elements"""
    words = page.extract_words()

    # Group by vertical position (rows)
    rows = defaultdict(list)
    for word in words:
        # Use a tolerance value to group words on approximately the same line
        row_key = round(word["top"] / 10) * 10  # Adjust tolerance as needed
        rows[row_key].append(word)

    # Sort rows by vertical position
    sorted_rows = []
    for row_key in sorted(rows.keys()):
        # Sort words in row by horizontal position
        row_words = sorted(rows[row_key], key=lambda w: w["x0"])
        row_text = [w["text"] for w in row_words]
        sorted_rows.append(row_text)

    # Detect column boundaries and organize into cells
    # (This would require additional logic based on your specific PDF layout)

    return sorted_rows
