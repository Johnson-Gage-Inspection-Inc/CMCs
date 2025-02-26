#!/usr/bin/env python3
import re
import pandas as pd
from collections import defaultdict
import pdfplumber
from tkinter import filedialog, Tk


def segment_by_blank_lines(lines):
    """
    Split a list of lines into segments using blank lines as boundaries.
    """
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
    """
    First-pass expansion: splits Range & CMC by blank lines,
    tries to distribute Parameter lines 1-to-1 if they match exactly.
    Otherwise replicates.
    """
    eqp = row.get("Equipment", "") or ""
    comments = row.get("Comments", "") or ""
    param_text = row.get("Parameter", "") or ""
    range_text = row.get("Range", "") or ""
    cmc_text = row.get("CMC (±)", "") or ""

    param_lines = param_text.splitlines()
    range_lines = range_text.splitlines()
    cmc_lines = cmc_text.splitlines()

    # Segment Range & CMC on blank lines
    range_segments = segment_by_blank_lines(range_lines)
    cmc_segments = segment_by_blank_lines(cmc_lines)

    # If mismatch in segment counts, do simpler expansion
    if len(range_segments) != len(cmc_segments):
        if len(range_lines) > 1:
            new_rows = []
            # Possibly many Range lines, replicate CMC if needed
            cmc_expanded = (
                cmc_lines
                if len(cmc_lines) == len(range_lines)
                else [cmc_text] * len(range_lines)
            )
            for r, c in zip(range_lines, cmc_expanded):
                new_rows.append(
                    {
                        "Equipment": eqp,
                        "Parameter": param_text,
                        "Range": r,
                        "CMC (±)": c,
                        "Comments": comments,
                    }
                )
            return new_rows
        else:
            # Nothing to expand
            return [row]

    # If segments match, flatten them and see if param_lines matches total_range_lines
    flattened_rows = []
    for r_seg, c_seg in zip(range_segments, cmc_segments):
        for r, c in zip(r_seg, c_seg):
            flattened_rows.append((r, c))

    total_range_lines = len(flattened_rows)
    # If param_lines is the same length, do a 1-to-1 match
    if param_lines and len(param_lines) == total_range_lines:
        new_rows = []
        for i, (r, c) in enumerate(flattened_rows):
            new_rows.append(
                {
                    "Equipment": eqp,
                    "Parameter": param_lines[i],
                    "Range": r,
                    "CMC (±)": c,
                    "Comments": comments,
                }
            )
        return new_rows
    else:
        # Fallback: replicate entire param_text for each flattened line
        new_rows = []
        for r, c in flattened_rows:
            new_rows.append(
                {
                    "Equipment": eqp,
                    "Parameter": param_text,
                    "Range": r,
                    "CMC (±)": c,
                    "Comments": comments,
                }
            )
        return new_rows


def param_lines_are_thermocouples(lines):
    """
    Returns True if EVERY non-blank line in 'lines' matches something like 'Type E', 'Type K', etc.
    Regex is flexible: 'Type' followed by any letter(s) or digits.
    """
    pattern = re.compile(r"^Type\s+[A-Za-z0-9]", re.IGNORECASE)
    for line in lines:
        txt = line.strip()
        if txt and not pattern.match(txt):
            return False
    return True


def distribute_multi_line_parameter(expanded_rows):
    """
    Second pass:
      - If multiple Parameter lines are all 'Type ...': replicate each row for each type line.
      - Else if multiple Parameter lines (like 'Pt 385, 100 Ω' / 'Pt 385, 1000 Ω'), try chunking them
        evenly among the expanded rows.
      - Otherwise, leave them as-is.
    """

    output = []

    # Group expansions by some stable key so we know which set of expansions came from the same original row.
    # For simplicity, we'll use (Equipment, Comments) or you might add other stable columns.
    def row_key(r):
        return (r["Equipment"], r.get("Comments", ""))

    grouped = defaultdict(list)
    for row in expanded_rows:
        grouped[row_key(row)].append(row)

    for grp_key, rows_in_grp in grouped.items():
        # If there's only one row, or the Parameter texts differ, just keep them as-is.
        if len(rows_in_grp) == 1:
            output.extend(rows_in_grp)
            continue
        distinct_params = {r["Parameter"] for r in rows_in_grp}
        if len(distinct_params) > 1:
            # They’ve already been split somehow, or differ for some reason—leave them.
            output.extend(rows_in_grp)
            continue

        # So we have multiple expanded rows that all share the exact same param_text.
        # Let's see if it's multi-line text:
        param_text = next(iter(distinct_params))  # the single shared text
        param_lines = [list for list in param_text.splitlines() if list.strip()]

        if len(param_lines) <= 1:
            # Nothing to distribute
            output.extend(rows_in_grp)
            continue

        # Distinguish Thermocouples vs. RTD-like chunking
        if param_lines_are_thermocouples(param_lines):
            # ### THERMOCOUPLE-STYLE REPLICATION ###
            # For each expanded row, replicate it once per param_line,
            # changing the 'Parameter' to each line.
            new_rows = []
            for orig in rows_in_grp:
                for pline in param_lines:
                    nr = dict(orig)
                    nr["Parameter"] = pline
                    new_rows.append(nr)
            output.extend(new_rows)
        else:
            # ### CHUNK-STYLE (e.g. Pt 385) ###
            expansions_count = len(rows_in_grp)
            param_count = len(param_lines)

            # If expansions_count is evenly divisible by param_count, chunk them
            if expansions_count % param_count == 0:
                sorted_grp = rows_in_grp  # or sort by e.g. Range if needed
                slice_size = expansions_count // param_count
                chunks = [
                    sorted_grp[i: i + slice_size]
                    for i in range(0, expansions_count, slice_size)
                ]
                for i, chunk in enumerate(chunks):
                    line_val = param_lines[i]
                    for row_item in chunk:
                        nr = dict(row_item)
                        nr["Parameter"] = line_val
                        output.append(nr)
            else:
                # fallback: can't chunk evenly => do nothing special
                output.extend(rows_in_grp)

    return output


def expand_rows(df):
    """
    1) Expand each row with dynamic_expand_row (Range/CMC splitting).
    2) Attempt to distribute multi-line Parameter across expansions
       if the lines are chunkable (like 2 param lines => half expansions each).
    """
    first_pass_expanded = []
    for _, row in df.iterrows():
        # If the Range column has multiple lines, do dynamic expansion
        r = (row.get("Range", "") or "").splitlines()
        if len(r) > 1:
            new_rows = dynamic_expand_row(row)
            first_pass_expanded.extend(new_rows)
        else:
            first_pass_expanded.append(row.to_dict())

    # Second pass: chunk expansions among multiple parameter lines
    second_pass = distribute_multi_line_parameter(first_pass_expanded)
    return pd.DataFrame(second_pass)


def extract_pdf_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tbl = page.extract_table()
            if tbl:
                headers = tbl[0]
                filtered = [row for row in tbl[1:] if row != headers]
                tables.extend(filtered)
    df = pd.DataFrame(tables, columns=headers)

    # If there's a "Parameter/Equipment" column
    if "Parameter/Equipment" in df.columns:
        split_cols = df["Parameter/Equipment"].str.split(
            r"\s*[-–]\s*", n=1, expand=True
        )
        df["Equipment"] = split_cols[0].fillna("")
        df["Parameter"] = split_cols[1].str.lstrip().fillna("")
        df.drop(columns=["Parameter/Equipment"], inplace=True)

    # Rename "CMC" column if needed
    for col in df.columns:
        if "CMC" in col and col != "CMC (±)":
            df.rename(columns={col: "CMC (±)"}, inplace=True)
            break

    # Reorder columns
    desired = ["Equipment", "Parameter", "Range", "CMC (±)", "Comments"]
    df = df[[c for c in desired if c in df.columns]]

    df = expand_rows(df)
    return df


def browse_file():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")]
    )


if __name__ == "__main__":
    pdf_file = browse_file()
    if pdf_file:
        df_extracted = extract_pdf_tables(pdf_file)
        print("Extracted Data:")
        print(df_extracted)
        df_extracted.to_csv("extracted_data.csv", index=False)
        print("Data saved to extracted_data.csv")
    else:
        print("No file selected.")
