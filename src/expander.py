import re
import pandas as pd
from collections import defaultdict


def parse_range(range_text):
    # Keep your existing parse_range logic
    if not range_text or not isinstance(range_text, str):
        return None, None, None

    text = re.sub(r"[^\x20-\x7E]+", " ", range_text)
    text = re.sub(r"\s+", " ", text).strip()

    pat1 = re.compile(
        r"^\(\s*([+-]?\d*\.?\d+)\s+to\s+([+-]?\d*\.?\d+)\s*\)\s+(.+)$", re.IGNORECASE
    )
    m = pat1.match(text)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()

    pat2 = re.compile(r"^Up\s+to\s+([\-.\d]+)\s+(.+)$", re.IGNORECASE)
    m = pat2.match(text)
    if m:
        return None, m.group(1), m.group(2).strip()

    pat3 = re.compile(r"^([\-.\d]+)\s+to\s+([\-.\d]+)\s+(.+)$", re.IGNORECASE)
    m = pat3.match(text)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()

    pat4 = re.compile(r"^([\-.\d]+)\s+(.+)$", re.IGNORECASE)
    m = pat4.match(text)
    if m:
        return None, m.group(1), m.group(2).strip()

    return None, None, text


def expand_frequency_and_cmc(df):
    expanded_data = []
    for _, row in df.iterrows():
        freq_split = row["Frequency"].split("\n") if pd.notna(row["Frequency"]) else []
        cmc_split = row["CMC (±)"].split("\n") if pd.notna(row["CMC (±)"]) else []
        range_split = row["Range"].split("\n") if pd.notna(row["Range"]) else []
        param_split = row["Parameter"].split("\n") if pd.notna(row["Parameter"]) else []

        if (
            len(freq_split) == len(cmc_split)
            and len(range_split) == 1
            and len(param_split) == 1
        ):
            for i in range(len(freq_split)):
                expanded_data.append(
                    {
                        **row.to_dict(),
                        "Frequency": freq_split[i],
                        "CMC (±)": cmc_split[i],
                    }
                )
        else:
            expanded_data.append(row.to_dict())

    return pd.DataFrame(expanded_data)


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
    # eqp = row.get("Equipment", "")
    param_txt = row.get("Parameter", "")
    rng_txt = row.get("Range", "")
    cmc_txt = row.get("CMC (±)", "")
    # comm_txt = row.get("Comments", "")

    param_lines = param_txt.splitlines()
    range_lines = rng_txt.splitlines()
    cmc_lines = cmc_txt.splitlines()

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
            return [row.to_dict()]

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
                    group_rows[i : i + chunk_size]
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
    return out


def expand_rows(df):
    """
    - Expand multi-line rows (dynamic_expand_row).
    - Distribute multi-line parameters (distribute_multi_line_parameter).
    - Expand frequency/CMC lines (expand_frequency_and_cmc).
    - Finally apply parse_range to fill RangeMin, RangeMax, RangeUnit.
    """
    first_pass = []
    for _, row in df.iterrows():
        rng = row.get("Range", "")
        if len(rng.splitlines()) > 1:
            new_rows = dynamic_expand_row(row)
            first_pass.extend(new_rows)
        else:
            first_pass.append(row.to_dict())

    second_pass = distribute_multi_line_parameter(first_pass)
    df_expanded = pd.DataFrame(second_pass)
    df_expanded = expand_frequency_and_cmc(df_expanded)

    # Add RangeMin, RangeMax, RangeUnit columns
    df_expanded[["RangeMin", "RangeMax", "RangeUnit"]] = df_expanded["Range"].apply(
        lambda x: pd.Series(parse_range(x))
    )

    return df_expanded
