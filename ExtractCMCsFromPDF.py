#!/usr/bin/env python3
import pdfplumber
import pandas as pd
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


def distribute_multi_line_parameter(expanded_rows):
    """
    Second-pass: If a single PDF row expanded into multiple lines
    but there's also a multi-line Parameter, we may want to
    split those lines in a chunked manner.

    Example:
    - Parameter has 2 lines (e.g. 'Pt 385, 100 Ω' / 'Pt 385, 1000 Ω').
    - We have 10 expanded rows for Range/CMC.
      => We'll give the first 5 expansions to the first Parameter line,
         and the next 5 expansions to the second Parameter line,
         etc.

    If the # of expansions is not evenly divisible by the number of
    Parameter lines, we just do a fallback: replicate param_text
    on each row (which might have already happened).
    """
    # Group expansions by the original (Equipment, Parameter, Range, CMC, Comments) "batch"
    # We'll rely on 'Parameter' for grouping. In practice, you might need
    # to store an ID from the original row or something similar.

    # We'll do a naive approach: for any row that has multiple lines *in the Parameter column itself*,
    # we try to slice up the expansions evenly.
    # A more robust approach might be to detect a single row's expansions with a row-id, etc.

    output = []
    # We can group by (Equipment, Comments, plus everything except Parameter/Range/CMC).
    # But simpler: We'll just look for repeated Parameter text with newlines => chunk if possible.
    from collections import defaultdict

    # Key: everything but Parameter, Range, and CMC
    def row_key(r):
        return (r["Equipment"], r["Comments"])

    grouped = defaultdict(list)
    for row in expanded_rows:
        grouped[row_key(row)].append(row)

    for grp_key, rows_in_grp in grouped.items():
        # Check if all these expansions share the EXACT same param_text (with newlines).
        # If not, or if there's only 1 row, no chunking needed.
        if len(rows_in_grp) == 1:
            output.extend(rows_in_grp)
            continue

        # See how many distinct Parameter values exist among these expansions
        distinct_params = {r["Parameter"] for r in rows_in_grp}
        if len(distinct_params) > 1:
            # Already splitted, just pass them along
            output.extend(rows_in_grp)
            continue

        # There's a single repeated parameter text => see if it's multi-line
        param_text = next(iter(distinct_params))  # the one param text
        param_lines = [line for line in param_text.splitlines() if line.strip()]

        if len(param_lines) <= 1:
            # Nothing to chunk
            output.extend(rows_in_grp)
            continue

        # If we do have multiple param lines, see if # expansions is divisible
        # We'll also confirm that the expansions differ only by Range/CMC
        # i.e. Equipment, Comments is the same. Possibly also any other columns you want stable.
        expansions_count = len(rows_in_grp)
        param_count = len(param_lines)

        if expansions_count % param_count == 0:
            # Let's chunk expansions_count into param_count slices
            slice_size = expansions_count // param_count
            # Sort rows_in_grp by Range or something stable, so chunking is consistent
            # We'll just keep the order we have them in.
            sorted_grp = rows_in_grp  # or sorted(rows_in_grp, key=lambda r: r["Range"])

            chunked = [
                sorted_grp[i: i + slice_size]
                for i in range(0, expansions_count, slice_size)
            ]
            # For each chunk, assign the corresponding param line
            for i, chunk in enumerate(chunked):
                p_line = param_lines[i]
                for row_item in chunk:
                    new_row = dict(row_item)
                    new_row["Parameter"] = p_line
                    output.append(new_row)
        else:
            # Not evenly divisible => fallback
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
