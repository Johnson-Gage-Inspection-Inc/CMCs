import tkinter as tk
from tkinter import filedialog
import pdfplumber
import re
import logging
import json
import pandas as pd
from src.range import parse_range
from src.extract import custom_extract_tables
from src.cmc import parse_budget


# Logging configuration
logging.basicConfig(level=logging.INFO)
logfile = "main.log"
logging.basicConfig(filename=logfile, level=logging.DEBUG, filemode="w")

DASH_PATTERN = re.compile(r"\s*–\s*")


def main(pdf_path):
    df = pdf_table_processor(pdf_path)
    
    if parsed_csv_file_path := filedialog.asksaveasfilename(
        title="Save CSV file",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
    ):
        df.to_csv(parsed_csv_file_path, index=False, encoding="utf-8-sig")
        logging.info(f"Exported parsed range data to '{parsed_csv_file_path}'")
    else:
        logging.warning("Save operation was cancelled. No file was saved.")


def pdf_table_processor(pdf_path: str, save_intermediate=False) -> pd.DataFrame:
    """Process the PDF file and extract the table data into a DataFrame.

    Args:
        pdf_path (str): Path to the PDF file.
        save_intermediate (bool, optional): Save intermediate JSON files. Defaults to False.

    Returns:
        pd.DataFrame:
    """
    table_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = custom_extract_tables(page)
            # Save intermediate results if requested
            if save_intermediate:
                with open(f"export/pages/json/page{page.page_number}.json", "w") as f:
                    f.write(json.dumps(tables, indent=2))
            for table in tables:
                table_rows.extend(custom_parse_table(table))
    columns = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]
    df = pd.DataFrame(table_rows, columns=columns)
    
    if save_intermediate:
        df.to_csv("export/parsed.csv", index=False, encoding="utf-8-sig")
        logging.info("Exported parsed data to 'export/parsed.csv'")

    df[["range_min", "range_min_unit", "range_max", "range_max_unit"]] = df[
        "Range"
    ].apply(lambda x: pd.Series(parse_range(x)))
    if save_intermediate:
        df.to_csv("export/range_parsed.csv", index=False, encoding="utf-8-sig")
        logging.info("Exported parsed range data to 'export/range_parsed.csv'")

    df[["frequency_range_min", "frequency_range_min_unit", "frequency_range_max", "frequency_range_max_unit"]] = df[
        "Frequency"
    ].apply(lambda x: pd.Series(parse_range(x)))
    if save_intermediate:
        df.to_csv("export/frequency_parsed.csv", index=False, encoding="utf-8-sig")
        logging.info("Exported parsed frequency data to 'export/frequency_parsed.csv'")

    df[["cmc_base", "cmc_multiplier", "cmc_mult_unit", "cmc_uncertainty_unit"]] = df[
        "CMC (±)"
    ].apply(lambda x: parse_budget(x).__series__())
    return df


def flatten_hierarchical_comments(lines, delimiter="; "):
    """
    Given a list of lines (some may start with a leading tab '\t'),
    transform them so that:
      - A non-indented line becomes the current "prefix."
      - Any subsequent indented lines get combined with that prefix.
      - If a prefix never sees an indented child line, it appears on its own.
    Returns a new list of strings, each one either "prefix; child" or a lone prefix.
    """
    results = []
    prefix = None
    prefix_used = False

    for line in lines:
        if line.startswith("\t"):
            # Indented => combine with current prefix (if any)
            child_text = line.lstrip("\t")
            if prefix:
                results.append(prefix + delimiter + child_text)
                prefix_used = True
            else:
                # No prefix => just store child alone
                results.append(child_text)
        else:
            # New (non-indented) prefix
            if prefix and not prefix_used:
                # Previous prefix had no children => emit it by itself
                results.append(prefix)
            prefix = line
            prefix_used = False

    # If the final prefix was never used for a child, emit it by itself
    if prefix and not prefix_used:
        results.append(prefix)

    return results


def group_lines(lines, threshold=5):
    # Sort the lines by their "top" value.
    sorted_lines = sorted(lines, key=lambda x: x["top"])
    groups = []
    if not sorted_lines:
        return groups

    # Start the first group with the first line.
    current_group = [sorted_lines[0]]
    # Use the first line's top as the reference value.
    current_avg_top = sorted_lines[0]["top"]

    for line in sorted_lines[1:]:
        # If the difference between the current line's top and the group's average is below the threshold,
        # consider it part of the same group.
        if abs(line["top"] - current_avg_top) < threshold:
            current_group.append(line)
            # Update the average "top" value for the current group.
            current_avg_top = sum(item["top"] for item in current_group) / len(
                current_group
            )
        else:
            groups.append(current_group)
            current_group = [line]
            current_avg_top = line["top"]
    if current_group:
        groups.append(current_group)
    return groups


def restructure_input_data(input_data, threshold=5):
    """
    Restructure the nested PDF table data into a list of rows, each row being a list
    of 4 cell texts, ordered from top to bottom. Each cell text is obtained by grouping
    text elements that have similar 'top' values (within the threshold).

    The input_data is assumed to be a list of rows (with the header row at index 0).
    Each row is a list of 4 columns, and each column is a list of dictionaries
    with at least "text" and "top" keys.
    """
    # Flatten the structure: extract a flat list of all cell entries from the data
    headers = [item[0]["text"] for item in input_data[0]]
    cell_entries = []
    for row in input_data[1:]:  # skip header row
        for col_idx, cell in enumerate(row):
            for item in cell:
                if "text" in item and "top" in item:
                    cell_entries.append(
                        {"col": col_idx, "top": item["top"], "text": item["text"]}
                    )

    # Sort all cell entries by their vertical position
    cell_entries.sort(key=lambda x: x["top"])

    # Group entries into horizontal lines based on the threshold.
    # Two entries belong to the same line if their "top" values differ by less than the threshold.
    lines = []
    if cell_entries:
        current_group = [cell_entries[0]]
        for entry in cell_entries[1:]:
            if abs(entry["top"] - current_group[-1]["top"]) < threshold:
                current_group.append(entry)
            else:
                lines.append(current_group)
                current_group = [entry]
        lines.append(current_group)

    # For each grouped line, build a row with exactly 4 columns, using '' for missing values.
    final_rows = []
    for group in lines:
        line_dict = {}
        for entry in group:
            col = entry["col"]
            # If multiple entries fall in the same column, join them with a space.
            if col in line_dict:
                line_dict[col] += " " + entry["text"]
            else:
                line_dict[col] = entry["text"]

        # Force exactly 4 columns. If a column is missing, use an empty string as placeholder.
        row_line = [line_dict.get(i, "") for i in range(4)]
        final_rows.append((group[0]["top"], row_line))

    # Sort the final rows by their vertical position and return just the row data.
    final_rows.sort(key=lambda x: x[0])
    # Add the header row back to the final rows.
    final_rows.insert(0, (0, headers))
    return [row for _, row in final_rows]


def custom_parse_table(input_data):
    """
    Convert the PDF table structure into a pandas DataFrame with the following columns:
      Equipment, Parameter, Range, Frequency, CMC (±), Comments
    """
    data = restructure_input_data(input_data, threshold=5)
    headers = data[0]

    # Initialize variables to store the current values for each column.
    equipment = ""
    parameter = ""
    range_val = ""
    frequency = ""
    cmc = ""
    preComment = ""
    comment = ""
    parameter2 = ""

    data_rows = []
    for row in data[1:]:
        row[0] = row[0].replace("(cont)", "").strip(" ")
        if headers[0] == "Parameter/Equipment":
            frequency = ""
            if row[0].endswith("–"):
                equipment = row[0].strip("–").strip()
                parameter = ""
                range_val = ""
                cmc = ""
                preComment = row[3]
                comment = ""
                parameter2 = ""
                continue
            elif "–" in row[0]:
                equipment, parameter = [part.strip() for part in row[0].split("–", 1)]
            elif row[0].startswith("\t"):
                parameter = row[0].strip("\t")
            elif row[0]:
                equipment = row[0]
                parameter = ""

            range_val = row[1].strip("\t")
            if row[1].startswith("H"):
                parameter2 = range_val
                range_val = ""
            elif range_val.endswith(":"):
                parameter2 = range_val if parameter else range_val
                range_val = ""
            cmc = row[2]

        elif headers[0] == "Parameter/Range":
            parameter2 = ""
            if "–" in row[0]:
                # equipment, parameter = [part.strip() for part in row[0].split('–', 1)]
                equipment = ""
                parameter = row[0]
                range_val = ""
                frequency = ""
                cmc = ""
                preComment = row[3]
                comment = ""
                continue
            elif row[0].startswith("\t"):
                range_val = row[0].strip("\t")

            frequency = row[1]
            cmc = row[2]

        if row[3].startswith("\t"):
            comment = preComment + "; " + row[3].strip("\t")
        elif row[3]:
            comment = row[3]
            preComment = ""

        if not equipment:
            equipment = comment

        if not cmc:
            continue
        param = ""
        if parameter and parameter2:
            param = parameter + "; " + parameter2
        elif parameter:
            param = parameter
        elif parameter2:
            param = parameter2
        data_rows.append([equipment, param, range_val, frequency, cmc, comment])
    return data_rows


if __name__ == "__main__":
    # Initialize file dialog for PDF selection.
    root = tk.Tk()
    root.withdraw()
    pdf_path = filedialog.askopenfilename(
        title="Select PDF file", filetypes=[("PDF files", "*.pdf")]
    )
    if not pdf_path:
        print("No PDF selected. Exiting.")
        exit()
    main(pdf_path)
