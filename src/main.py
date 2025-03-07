import tkinter as tk
from tkinter import filedialog
import pdfplumber
import pandas as pd
import json
import re
from src.reader import cleanColumn, parse_page_table
from src.expander import expand_frequency_and_cmc, parse_range

# --- New helper functions for enhanced parsing ---

# Regex pattern to match Unicode superscripts ( footnote markers)
SUPERSCRIPT_PATTERN = re.compile(r"[\u00B2\u00B3\u00B9\u2070-\u209F]")
# Pattern to split on a dash (–) that separates equipment from parameter
DASH_PATTERN = re.compile(r"\s*–\s*")


def main(pdf_file):
    # Step 1: Extract DataFrame from PDF without frequency expansion
    df_all = extract_pdf_tables_to_df(pdf_file)
    # Step 2: Expand Frequency and CMC using existing logic
    df_expanded = expand_frequency_and_cmc(df_all)
    # Add RangeMin, RangeMax, RangeUnit columns
    df_expanded[["RangeMin", "RangeMax", "RangeUnit"]] = df_expanded["Range"].apply(
        lambda x: pd.Series(parse_range(x))
    )
    df_expanded.to_csv("extracted_data.csv", index=False)
    print("Saved extracted_data.csv")


def extract_pdf_tables_to_df(pdf_path, save_intermediate=False):
    """
    Reads the PDF, extracts tables using positional data,
    merges them into one DataFrame, and performs minimal cleaning.
    """
    big_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            with open(f"export/pages/json/page{page.page_number}.json", "w") as f:
                json.dump(clean_for_json(page.to_dict()), f, indent=4)
            # Extract tables using positional information
            tables = (
                page.extract_tables()
            )  # or use your extract_tables_by_position(page) if defined
            for i, extracted_table in enumerate(tables):
                if extracted_table:
                    headers = extracted_table[0]
                    data_rows = extracted_table[1:]
                    df_page = pd.DataFrame(data_rows, columns=headers)
                    # Save the pre-parsed table for debugging
                    df_page.to_csv(
                        f"export/tables/pre/page{page.page_number}_table{i}.csv",
                        index=False,
                        encoding="utf-8-sig",
                    )
                    # Process the table with your enhanced logic
                    parsed_df_page = parse_page_table(df_page)
                    # Now apply the enhanced parsing for Parameter/Equipment and Comments
                    parsed_df_page = enhanced_parse_page_table(parsed_df_page)
                    # Save the parsed table
                    parsed_df_page.to_csv(
                        f"export/tables/parsed/page{page.page_number}_table{i}.csv",
                        index=False,
                        encoding="utf-8-sig",
                    )
                    big_tables.append(parsed_df_page)

    if not big_tables:
        return pd.DataFrame(
            columns=[
                "Equipment",
                "Parameter",
                "Range",
                "Frequency",
                "CMC (±)",
                "Comments",
            ]
        )
    df_all = pd.concat(big_tables, ignore_index=True)
    # Clean the Equipment and Parameter columns further
    df_all["Equipment"] = cleanColumn(df_all["Equipment"])
    df_all["Parameter"] = cleanColumn(df_all["Parameter"])
    if save_intermediate:
        df_all.to_csv("tests/test_data/intermediate_df.csv", index=False)
        print("Saved intermediate_df.csv")
    return df_all


def remove_superscripts(text: str) -> str:
    """Remove superscript characters (footnote markers) from text."""
    if not text:
        return text
    return SUPERSCRIPT_PATTERN.sub("", text)


def split_equipment_and_parameter(cell_text: str) -> tuple[str, str]:
    """
    If the cell text contains a dash, split it into equipment and parameter.
    Otherwise, treat the whole string as equipment.
    """
    text = remove_superscripts(cell_text).strip()
    parts = DASH_PATTERN.split(text, maxsplit=1)
    if len(parts) == 2:
        equipment, param = parts
        return equipment.strip(), param.strip()
    else:
        return text, ""


def process_parameter_equipment(cell_text: str) -> list:
    """
    Process the raw text of the Parameter/Equipment cell.
    The expected format is:
      - A left-justified main header (equipment) that may contain a dash (–) to separate an initial parameter.
      - Followed by one or more indented lines (tab or extra spaces) that represent additional parameters.
    Returns a list of (equipment, parameter) tuples.
    """
    # Split the cell text into lines
    lines = cell_text.splitlines()
    results = []
    equipment = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Use a simple heuristic: if the line starts with a tab or at least 4 leading spaces, treat it as indented
        indent = len(line) - len(line.lstrip(" "))
        if indent >= 4:
            # This is a sub-item: add the current equipment with this parameter text
            results.append((equipment, stripped))
        else:
            # This is a new main heading line.
            eqp, param = split_equipment_and_parameter(stripped)
            equipment = eqp  # update current equipment
            if param:
                results.append((equipment, param))
    # If no sub-items were found, use the equipment as the only row.
    if not results and equipment:
        results = [(equipment, "")]
    return results


def process_comments(cell_text: str) -> list:
    """
    Process the Comments cell text.
    The Comments cell may have a left-justified main comment header, followed by one or more indented sub-items.
    This function returns a list where each sub-item is combined with the main header,
    separated by a semicolon.
    """
    lines = cell_text.splitlines()
    results = []
    main_heading = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent >= 4:
            # Indented sub-item: combine with main heading (if present)
            if main_heading:
                results.append(f"{main_heading}; {stripped}")
            else:
                results.append(stripped)
        else:
            # New main heading line
            main_heading = remove_superscripts(stripped)
    # If there were no sub-items, use the main heading
    if not results and main_heading:
        results = [main_heading]
    return results


def enhanced_parse_page_table(df_page: pd.DataFrame) -> pd.DataFrame:
    """
    Apply enhanced parsing to the extracted table DataFrame.
    This function processes:
      - The "Parameter/Equipment" column: splits into Equipment and Parameter based on left-justification and dash.
      - The "Comments" column: concatenates main header and indented sub-items.
    It then replicates rows to flatten these multi-line values.
    """
    new_rows = []
    # If the DataFrame has a "Parameter/Equipment" column, use it;
    # otherwise, fall back to using existing Equipment and Parameter columns.
    for _, row in df_page.iterrows():
        # Process Parameter/Equipment
        pe_cell = row.get("Parameter/Equipment", "")
        if pe_cell:
            eqp_param_list = process_parameter_equipment(pe_cell)
        else:
            # Use existing columns (if present)
            eqp_param_list = [
                (row.get("Equipment", "").strip(), row.get("Parameter", "").strip())
            ]

        # Process Comments similarly
        comments_cell = row.get("Comments", "")
        if comments_cell:
            comment_list = process_comments(comments_cell)
        else:
            comment_list = [row.get("Comments", "").strip()]

        # Create one output row per combination.
        # (For simplicity, we take the Cartesian product of equipment/parameter pairs and comment items.)
        for eqp, param in eqp_param_list:
            for comment in comment_list:
                new_row = row.to_dict()
                new_row["Equipment"] = eqp
                new_row["Parameter"] = param
                new_row["Comments"] = comment
                new_rows.append(new_row)
    df_enhanced = pd.DataFrame(new_rows)
    # Optionally, remove any remaining newline characters from all cells.
    for col in df_enhanced.columns:
        df_enhanced[col] = (
            df_enhanced[col].astype(str).replace("\n", " ", regex=True).str.strip()
        )
    return df_enhanced


# --- End of helper functions ---


def clean_for_json(obj):
    """Clean non-serializable objects for JSON dumping."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)


def browse_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")]
    )


if __name__ == "__main__":
    pdf_file = browse_file()
    if pdf_file:
        main(pdf_file)
        print("Done! See extracted_data.csv.")
    else:
        print("No file selected.")
