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
    Given a row with multi-line strings for Parameter, Range, CMC (±) and Comments,
    this function applies a dynamic segmentation strategy. It splits the Range and CMC (±)
    columns into segments based on blank lines (a proxy for double line breaks).
    Then it attempts to distribute the Parameter lines across the segments.
    Returns a list of dictionaries, one per final row.
    """
    equipment = row.get("Equipment", "")
    comments = row.get("Comments", "")
    param_text = row.get("Parameter", "")
    range_text = row.get("Range", "")
    cmc_text = row.get("CMC (±)", "")

    # Split each field into lines
    param_lines = param_text.splitlines() if param_text else []
    range_lines = range_text.splitlines() if range_text else []
    cmc_lines = cmc_text.splitlines() if cmc_text else []

    # Segment the range and cmc lists by blank lines.
    range_segments = segment_by_blank_lines(range_lines)
    cmc_segments = segment_by_blank_lines(cmc_lines)

    # If the number of segments don’t match, fallback to a simple expansion:
    if len(range_segments) != len(cmc_segments):
        # If there are simply multiple range lines, zip them up (or duplicate CMC if needed)
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

    # Now, try to distribute parameter lines.
    # If the total number of range lines across all segments equals the number of parameter lines,
    # assign one-to-one; otherwise, use the whole Parameter text for each segment.
    total_range_lines = sum(len(seg) for seg in range_segments)
    new_rows = []
    if param_lines and len(param_lines) == total_range_lines:
        # Distribute parameter lines in order:
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
        # Fallback: for each line in each segment, repeat the full Parameter text.
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
    For each row in the DataFrame, if the Range column has multiple lines,
    apply a dynamic segmentation and expansion.
    """
    expanded_data = []
    for _, row in df.iterrows():
        range_val = row.get("Range", "")
        if range_val and len(range_val.splitlines()) > 1:
            new_rows = dynamic_expand_row(row)
            expanded_data.extend(new_rows)
        else:
            expanded_data.append(row.to_dict())
    return pd.DataFrame(expanded_data)


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

    # Split "Parameter/Equipment" into separate columns using a regex that splits on any dash
    if "Parameter/Equipment" in df.columns:
        split_cols = df["Parameter/Equipment"].str.split(
            r"\s*[-–]\s*", n=1, expand=True
        )
        df["Equipment"] = split_cols[0]
        df["Parameter"] = split_cols[1].str.lstrip() if split_cols.shape[1] > 1 else ""
        df.drop(columns=["Parameter/Equipment"], inplace=True)

    # Rename the CMC column (if not already named) by looking for any column containing "CMC"
    for col in df.columns:
        if "CMC" in col and col != "CMC (±)":
            df.rename(columns={col: "CMC (±)"}, inplace=True)
            break

    desired_order = ["Equipment", "Parameter", "Range", "CMC (±)", "Comments"]
    df = df[[col for col in desired_order if col in df.columns]]
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
