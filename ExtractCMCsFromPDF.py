#!/usr/bin/env python3
import re
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


def replicate_row_for_multiple_types(row):
    """
    If the Parameter field has multiple 'Type ...' lines but only
    a single Range line and single CMC line, replicate this row
    once per 'Type ...' line. Otherwise, return it unchanged.
    """
    equipment = row.get("Equipment", "")
    param_text = row.get("Parameter", "") or ""
    range_text = row.get("Range", "")
    cmc_text = row.get("CMC (±)", "")
    comments = row.get("Comments", "")

    # Split the parameter field by lines
    lines = [l.strip() for l in param_text.splitlines() if l.strip()]

    # Collect only lines that match something like "Type S", "Type K", etc.
    # Adapt the regex if you have more variety, e.g. "Type B (some note)"
    type_regex = re.compile(r"^Type\s+[A-Z]", re.IGNORECASE)
    type_lines = [l for l in lines if type_regex.match(l)]

    # If we have more than one "Type" line AND exactly 1 Range and 1 CMC line,
    # replicate the row. Otherwise, leave it unchanged.
    if len(type_lines) > 1:
        # Check how many lines in Range & CMC
        range_count = len([r for r in range_text.splitlines() if r.strip()])
        cmc_count = len([c for c in cmc_text.splitlines() if c.strip()])

        if range_count == 1 and cmc_count == 1:
            # Replicate the row for each Type line
            new_rows = []
            for t_line in type_lines:
                new_rows.append(
                    {
                        "Equipment": equipment,
                        "Parameter": t_line,
                        "Range": range_text,
                        "CMC (±)": cmc_text,
                        "Comments": comments,
                    }
                )
            return new_rows

    # Otherwise, return the original row as a single list
    return [row]


def dynamic_expand_row(row):
    """
    Splits Range & CMC by blank lines, then tries to distribute Parameter lines.
    """
    equipment = row.get("Equipment", "")
    comments = row.get("Comments", "")
    param_text = row.get("Parameter", "")
    range_text = row.get("Range", "")
    cmc_text = row.get("CMC (±)", "")

    param_lines = param_text.splitlines() if param_text else []
    range_lines = range_text.splitlines() if range_text else []
    cmc_lines = cmc_text.splitlines() if cmc_text else []

    # Segment Range & CMC
    range_segments = segment_by_blank_lines(range_lines)
    cmc_segments = segment_by_blank_lines(cmc_lines)

    # If the number of segments don’t match, do a simpler expansion
    if len(range_segments) != len(cmc_segments):
        if len(range_lines) > 1:
            new_rows = []
            num = len(range_lines)
            cmc_expanded = cmc_lines if len(cmc_lines) == num else [cmc_text] * num
            for r, c in zip(range_lines, cmc_expanded):
                new_rows.append(
                    {
                        "Equipment": equipment,
                        "Parameter": param_text,
                        "Range": r,
                        "CMC (±)": c,
                        "Comments": comments,
                    }
                )
            return new_rows
        else:
            return [row]

    # Attempt to distribute param lines across segments
    total_range_lines = sum(len(seg) for seg in range_segments)
    new_rows = []
    if param_lines and len(param_lines) == total_range_lines:
        index = 0
        for r_seg, c_seg in zip(range_segments, cmc_segments):
            for r, c in zip(r_seg, c_seg):
                new_rows.append(
                    {
                        "Equipment": equipment,
                        "Parameter": param_lines[index],
                        "Range": r,
                        "CMC (±)": c,
                        "Comments": comments,
                    }
                )
                index += 1
    else:
        # Fallback: replicate entire param text for each line in each segment
        for r_seg, c_seg in zip(range_segments, cmc_segments):
            for r, c in zip(r_seg, c_seg):
                new_rows.append(
                    {
                        "Equipment": equipment,
                        "Parameter": param_text,
                        "Range": r,
                        "CMC (±)": c,
                        "Comments": comments,
                    }
                )
    return new_rows


def expand_rows(df):
    """
    Apply dynamic_expand_row to handle Range/CMC segmentation,
    then apply replicate_row_for_multiple_types to handle multiple
    'Type ...' lines in Parameter.
    """
    expanded_data = []
    # First pass: expand each row with dynamic_expand_row
    for _, row in df.iterrows():
        range_val = row.get("Range", "")
        if range_val and len(range_val.splitlines()) > 1:
            new_rows = dynamic_expand_row(row)
            expanded_data.extend(new_rows)
        else:
            expanded_data.append(row.to_dict())

    # Second pass: replicate the new set of rows for multiple 'Type ...' lines
    final_data = []
    for row in expanded_data:
        # replicate_row_for_multiple_types always returns a list
        multi = replicate_row_for_multiple_types(row)
        final_data.extend(multi)

    return pd.DataFrame(final_data)


def extract_pdf_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_table = page.extract_table()
            if extracted_table:
                headers = extracted_table[0]
                filtered_table = [row for row in extracted_table[1:] if row != headers]
                tables.extend(filtered_table)
    df = pd.DataFrame(tables, columns=headers)

    # Split "Parameter/Equipment" if it exists
    if "Parameter/Equipment" in df.columns:
        split_cols = df["Parameter/Equipment"].str.split(
            r"\s*[-–]\s*", n=1, expand=True
        )
        df["Equipment"] = split_cols[0]
        df["Parameter"] = split_cols[1].str.lstrip() if split_cols.shape[1] > 1 else ""
        df.drop(columns=["Parameter/Equipment"], inplace=True)

    # Rename the CMC column if needed
    for col in df.columns:
        if "CMC" in col and col != "CMC (±)":
            df.rename(columns={col: "CMC (±)"}, inplace=True)
            break

    # Reorder columns
    desired_order = ["Equipment", "Parameter", "Range", "CMC (±)", "Comments"]
    df = df[[c for c in desired_order if c in df.columns]]

    # Expand rows
    df = expand_rows(df)
    return df


def browse_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")]
    )
    return file_path


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
