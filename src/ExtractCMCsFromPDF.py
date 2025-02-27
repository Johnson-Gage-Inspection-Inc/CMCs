#!/usr/bin/env python3
import re
import pdfplumber
import pandas as pd
from tkinter import filedialog, Tk
from collections import defaultdict

###############################################################################
#                         HELPER FUNCTIONS                                    #
###############################################################################


def parse_range(range_text):
    """
    Extract RangeMin, RangeMax, and RangeUnit from a range string.
    Handles typical forms:
      1) "(min to max) unit"
      2) "Up to max unit"
      3) "single_value unit"
      4) "min to max unit" (no parentheses)

    Returns (RangeMin, RangeMax, RangeUnit).
    """
    if not range_text or not isinstance(range_text, str):
        return None, None, None

    # 1) Normalize any weird whitespace (non-breaking spaces, etc.)
    #    Remove non-ASCII control chars & unify multiple spaces.
    text = re.sub(r'[^\x20-\x7E]+', ' ', range_text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 2) Regex patterns in a logical order. Each pattern tries to capture
    #    the entire string ^...$ and breaks it into groups.

    # (min to max) unit  e.g. "(10 to 50) mm"
    #   group(1)=10, group(2)=50, group(3)=mm...
    pat1 = re.compile(r'^\(\s*([+-]?\d*\.?\d+)\s+to\s+([+-]?\d*\.?\d+)\s*\)\s+(.+)$', re.IGNORECASE)
    m = pat1.match(text)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()

    # "Up to max unit"  e.g. "Up to 9 in"
    pat2 = re.compile(r'^Up\s+to\s+([\-.\d]+)\s+(.+)$', re.IGNORECASE)
    m = pat2.match(text)
    if m:
        return None, m.group(1), m.group(2).strip()

    # "min to max unit"  e.g. "3.5 to 27 in"
    pat3 = re.compile(r'^([\-.\d]+)\s+to\s+([\-.\d]+)\s+(.+)$', re.IGNORECASE)
    m = pat3.match(text)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()

    # Single value unit  e.g. "3.5 in"
    pat4 = re.compile(r'^([\-.\d]+)\s+(.+)$', re.IGNORECASE)
    m = pat4.match(text)
    if m:
        return None, m.group(1), m.group(2).strip()

    # If still no match, return the original text in RangeUnit as a fallback
    return None, None, text


def expand_frequency_and_cmc(df):
    """
    Expands rows where:
      - Frequency and CMC (±) have the same number of lines.
      - Range & Parameter only have one line (after previous processing).

    If conditions match, this function:
      - Creates a row for each line in Frequency/CMC.
      - Repeats Parameter, Range, and Comments in each row.
    """
    expanded_data = []

    for _, row in df.iterrows():
        freq_split = row["Frequency"].split("\n") if pd.notna(row["Frequency"]) else []
        cmc_split = row["CMC (±)"].split("\n") if pd.notna(row["CMC (±)"]) else []
        range_split = row["Range"].split("\n") if pd.notna(row["Range"]) else []
        param_split = row["Parameter"].split("\n") if pd.notna(row["Parameter"]) else []

        # ✅ Only expand when Frequency & CMC have the same number of lines
        #    AND Range & Parameter have just one line (already processed)
        if (
            len(freq_split) == len(cmc_split) and len(range_split) == 1 and len(param_split) == 1
        ):
            for i in range(len(freq_split)):
                expanded_data.append(
                    {
                        "Equipment": row["Equipment"],
                        "Parameter": row["Parameter"],
                        "Range": row["Range"],
                        "Frequency": freq_split[i],
                        "CMC (±)": cmc_split[i],
                        "Comments": row["Comments"],
                    }
                )
        else:
            # Keep the row as-is if it doesn't meet the criteria
            expanded_data.append(row.to_dict())

    return pd.DataFrame(expanded_data)


def remove_superscripts(text):
    """Removes superscript numbers, special characters, and footnote markers."""
    if not text:
        return text
    # Remove common superscripts and footnote numbers
    return re.sub(
        r"[\u00B2\u00B3\u00B9\u2070-\u209F\d]$", "", text
    )  # Removes trailing numbers


def split_parameter_equipment(cell_value):
    """
    If the table has a 'Parameter/Equipment' column, split it on a dash
    (or en dash) into 'Equipment' and 'Parameter'. This is the older logic.
    """
    if not cell_value:
        return ("", "")
    # Splits on any dash surrounded by optional whitespace
    split_cols = re.split(r"\s*[-–]\s*", cell_value, maxsplit=1)
    if len(split_cols) == 2:
        equipment, param = split_cols
        return (equipment.strip(), param.strip())
    else:
        # if we can't split, treat the entire cell as parameter
        return ("", cell_value.strip())


def split_parameter_range(cell_value):
    """
    If the table has a single 'Parameter/Range' column plus a separate 'Frequency',
    we can do a basic heuristic:
      - first (non-blank) line is the Parameter
      - last (non-blank) line is the Range
    """
    if not cell_value:
        return ("", "")
    lines = [ln.strip() for ln in cell_value.splitlines() if ln.strip()]
    if len(lines) == 1:
        # only one line => treat as Parameter, no Range
        return (lines[0], "")
    else:
        # first line => Parameter, last line => Range
        return (lines[0], lines[-1])


def segment_by_blank_lines(lines):
    """
    Split a list of lines into segments using blank lines as boundaries.
    Used in the dynamic expansion logic for Range/CMC.
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
    First-pass expansion for a single row:
      - We split Range & CMC by blank lines, flatten them,
        and either match them 1-to-1 with Parameter lines or replicate.
    """
    eqp = row.get("Equipment", "") or ""
    param_txt = row.get("Parameter", "") or ""
    rng_txt = row.get("Range", "") or ""
    cmc_txt = row.get("CMC (±)", "") or ""
    comm_txt = row.get("Comments", "") or ""

    param_lines = param_txt.splitlines()
    range_lines = rng_txt.splitlines()
    cmc_lines = cmc_txt.splitlines()

    # Segment Range & CMC
    range_segments = segment_by_blank_lines(range_lines)
    cmc_segments = segment_by_blank_lines(cmc_lines)

    # If mismatch, fallback
    if len(range_segments) != len(cmc_segments):
        if len(range_lines) > 1:
            new_rows = []
            # replicate if needed
            if len(range_lines) == len(cmc_lines):
                for r, c in zip(range_lines, cmc_lines):
                    new_rows.append(
                        {
                            "Equipment": eqp,
                            "Parameter": param_txt,
                            "Range": r,
                            "CMC (±)": c,
                            "Comments": comm_txt,
                        }
                    )
            else:
                # replicate entire cmc_txt if mismatch
                for r in range_lines:
                    new_rows.append(
                        {
                            "Equipment": eqp,
                            "Parameter": param_txt,
                            "Range": r,
                            "CMC (±)": cmc_txt,
                            "Comments": comm_txt,
                        }
                    )
            return new_rows
        else:
            return [row]

    # Flatten
    flattened = []
    for r_seg, c_seg in zip(range_segments, cmc_segments):
        for r, c in zip(r_seg, c_seg):
            flattened.append((r, c))

    total_range_lines = len(flattened)
    if param_lines and len(param_lines) == total_range_lines:
        # 1-1 match with Parameter lines
        out = []
        for i, (r, c) in enumerate(flattened):
            out.append(
                {
                    "Equipment": eqp,
                    "Parameter": param_lines[i],
                    "Range": r,
                    "CMC (±)": c,
                    "Comments": comm_txt,
                }
            )
        return out
    else:
        # replicate entire param_txt for each line
        out = []
        for r, c in flattened:
            out.append(
                {
                    "Equipment": eqp,
                    "Parameter": param_txt,
                    "Range": r,
                    "CMC (±)": c,
                    "Comments": comm_txt,
                }
            )
        return out


def param_lines_are_thermocouples(lines):
    """
    Check if all lines match something like "Type E", "Type K" etc.
    """
    pattern = re.compile(r"^Type\s+[A-Za-z0-9]", re.IGNORECASE)
    for ln in lines:
        ln = ln.strip()
        if ln and not pattern.match(ln):
            return False
    return True


def distribute_multi_line_parameter(expanded_rows):
    """
    Second pass: group expansions that share the same (Equipment, Comments).
    If the Parameter text has multiple lines, decide how to replicate:
      - If all lines match 'Type ...', replicate for each line (thermocouple approach).
      - Otherwise do the chunk approach (like for Pt 385 lines).
      - If chunk is not perfectly divisible, fallback to no distribution.
    """
    out = []

    def row_key(r):
        # Group by these columns so expansions from a single PDF line
        # get processed together
        return (r.get("Equipment", ""), r.get("Comments", ""))

    grouped = defaultdict(list)
    for row in expanded_rows:
        grouped[row_key(row)].append(row)

    for _, group_rows in grouped.items():
        # If there's only one row in the group, no distribution needed
        if len(group_rows) == 1:
            out.extend(group_rows)
            continue

        # Check if they all share the same exact Parameter text
        distinct_params = {r["Parameter"] for r in group_rows}
        if len(distinct_params) > 1:
            # Already differ => skip
            out.extend(group_rows)
            continue

        # There's a single repeated param_text
        param_text = next(iter(distinct_params))
        plines = [ln.strip() for ln in param_text.splitlines() if ln.strip()]
        if len(plines) <= 1:
            # Only one non-blank line => nothing special
            out.extend(group_rows)
            continue

        # If they all look like "Type X" => replicate each row for each line
        if param_lines_are_thermocouples(plines):
            for row_item in group_rows:
                for tline in plines:
                    nr = dict(row_item)
                    nr["Parameter"] = tline
                    out.append(nr)
        else:
            # Otherwise do the chunk approach
            expansions_count = len(group_rows)
            param_count = len(plines)
            if expansions_count % param_count == 0:
                chunk_size = expansions_count // param_count
                # We'll keep them in the same order
                # Or you can do sorted(..., key=lambda r: r["Range"]) if you prefer
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
                # fallback => keep them stacked
                out.extend(group_rows)
    return out


def expand_rows(df):
    """
    Calls dynamic_expand_row on each row, then second-pass distribute_multi_line_parameter,
    and then handles cases where Frequency and CMC should be expanded into separate rows.
    """
    first_pass = []
    for _, row in df.iterrows():
        rng = row.get("Range", "") or ""

        if len(rng.splitlines()) > 1:
            new_rows = dynamic_expand_row(row)
            first_pass.extend(new_rows)
        else:
            first_pass.append(row.to_dict())

    second_pass = distribute_multi_line_parameter(first_pass)

    # Convert to DataFrame before handling Frequency expansion
    df_expanded = pd.DataFrame(second_pass)

    # ✅ Handle Frequency & CMC expansion when conditions match
    if "Frequency" in df_expanded.columns and "CMC (±)" in df_expanded.columns:
        df_expanded = expand_frequency_and_cmc(df_expanded)

    return df_expanded


###############################################################################
#                          MAIN EXTRACTION LOGIC                               #
###############################################################################


def parse_page_table(extracted_table):
    """
    Given the raw extracted table (list of lists) from pdfplumber for one page,
    determine which header layout we have, build a DataFrame, unify columns,
    and return it.
    """
    headers = extracted_table[0]
    data_rows = extracted_table[1:]
    # Filter out repeated header rows if any
    data_rows = [r for r in data_rows if r != headers]

    # Convert to DataFrame
    df_page = pd.DataFrame(data_rows, columns=headers)

    # We might have:
    # 1) Parameter, Range, CMC (±), Comments
    # 2) Parameter/Equipment, Range, CMC (±), Comments
    # 3) Parameter/Range, Frequency, CMC (±), Comments
    # (Or other variations.)
    # We'll unify them into:
    # Equipment, Parameter, Range, Frequency, CMC (±), Comments

    # Start with placeholders so we always have the columns
    df_page["Equipment"] = df_page.get("Equipment", "")
    df_page["Parameter"] = df_page.get("Parameter", "")
    df_page["Range"] = df_page.get("Range", "")
    df_page["Frequency"] = df_page.get("Frequency", "")
    df_page["CMC (±)"] = df_page.get("CMC (±)", "")
    df_page["Comments"] = df_page.get("Comments", "")

    # 1) If there's a "Parameter/Equipment" col, parse it out
    if "Parameter/Equipment" in df_page.columns:
        # parse => Equipment, Parameter
        eqp_par = df_page["Parameter/Equipment"].apply(split_parameter_equipment)
        df_page["Equipment"], df_page["Parameter"] = zip(*eqp_par)
        df_page.drop(columns=["Parameter/Equipment"], inplace=True)

    # 2) If there's a "Parameter/Range" col, parse it out
    if "Parameter/Range" in df_page.columns:
        pr_cols = df_page["Parameter/Range"].apply(split_parameter_range)
        df_page["Parameter"], df_page["Range"] = zip(*pr_cols)
        df_page.drop(columns=["Parameter/Range"], inplace=True)

    # 3) If we don't have a column named "Frequency" but do see "Frequency" in headers
    # or if there's an actual column named "Frequency", then keep it
    # (We already created an empty "Frequency" above if needed.)

    # 4) If there's a column that looks like "CMC" not named "CMC (±)", rename it
    for col in list(df_page.columns):
        if "CMC" in col and col != "CMC (±)":
            df_page.rename(columns={col: "CMC (±)"}, inplace=True)

    # 5) Now remove duplicates if any:
    df_page = df_page.loc[:, ~df_page.columns.duplicated()]

    # 6) We might have fewer / extra columns from the PDF.
    # Let's keep the relevant ones in a final set:
    final_cols = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]
    # We'll reorder them
    existing_cols = [c for c in final_cols if c in df_page.columns]
    df_page = df_page[existing_cols]

    return df_page


def extract_pdf_tables(pdf_path):
    """
    Extracts tables from the PDF, processes them, and expands necessary columns.
    """
    big_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for i, extracted_table in enumerate(tables):
                if extracted_table:
                    df_page = parse_page_table(extracted_table)
                    df_page.to_csv(f"tests/test_data/page{page.page_number}_table{i}.csv", index=False)
                    big_tables.append(df_page)

    if not big_tables:
        return pd.DataFrame(
            columns=[
                "Equipment",
                "Parameter",
                "RangeMin",
                "RangeMax",
                "RangeUnit",
                "CMC (±)",
                "Comments",
            ]
        )

    df_all = pd.concat(big_tables, ignore_index=True)

    # ✅ Apply superscript removal **before** range parsing
    for col in df_all.columns:
        df_all[col] = df_all[col].apply(
            lambda x: remove_superscripts(str(x)) if pd.notna(x) else x
        )

    # Debug check: Are new columns appearing?
    print("DEBUG: After Range Parsing:\n", df_all.head())

    # ✅ Ensure new columns are part of the final dataset
    # df_all.drop(columns=["Range"], inplace=True, errors="ignore")  # Commented out to keep the Range column

    # Remove "(cont)" from Equipment and Parameter
    df_all["Equipment"] = cleanColumn(df_all["Equipment"])
    df_all["Parameter"] = cleanColumn(df_all["Parameter"])

    # Expand rows as needed
    df_expanded = expand_rows(df_all)

    # ✅ Apply range parsing
    df_expanded[["RangeMin", "RangeMax", "RangeUnit"]] = df_expanded["Range"].apply(
        lambda x: pd.Series(parse_range(x))
    )

    # Ensure final DataFrame includes new columns
    final_columns = [
        "Equipment",
        "Parameter",
        "Range",
        "RangeMin",
        "RangeMax",
        "RangeUnit",
        "CMC (±)",
        "Comments",
        "Frequency",
    ]
    df_expanded = df_expanded.reindex(columns=final_columns, fill_value="")

    return df_expanded


def cleanColumn(col):
    return col.str.replace(r"\(cont\)", "", regex=True).str.strip()


def browse_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")]
    )
    return file_path


###############################################################################
#                             ENTRY POINT                                     #
###############################################################################

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
