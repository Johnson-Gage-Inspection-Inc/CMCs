import tkinter as tk
from tkinter import filedialog
import pdfplumber
import re
import logging
import json
import pandas as pd


# Logging configuration
logging.basicConfig(level=logging.INFO)
logfile = "main.log"
logging.basicConfig(filename=logfile, level=logging.DEBUG, filemode="w")

DASH_PATTERN = re.compile(r"\s*–\s*")


def main(pdf_path, save_intermediate=False):
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
    df.to_csv("export/parsed.csv", index=False, encoding="utf-8-sig")
    logging.info("Exported parsed data to 'export/parsed.csv'")


def custom_extract_tables(page, table_settings=None, vertical_thresh=14, indent_thresh=4):
    """
    Custom table extraction from a pdfplumber Page.
    ...
    """
    BEGIN_LINE_PATTERN = re.compile(r'^(?:\d|\(\d|\-\d|\(-\d|[<>]\s*\d)')

    def get_first_word_width(ln):
        if "chars" not in ln or not ln["chars"]:
            return 0
        first_word_chars = []
        for c in ln["chars"]:
            if c["text"].isspace():
                if first_word_chars:
                    break
                else:
                    continue
            first_word_chars.append(c)
        if not first_word_chars:
            return 0
        return first_word_chars[-1]["x1"] - first_word_chars[0]["x0"]

    # Use pdfplumber's table finder.
    tables = page.find_tables(table_settings=table_settings)
    custom_tables = []

    for table in tables:
        table_rows = []
        for row in table.rows:
            row_cells = []
            for cell in row.cells:
                if not cell:
                    row_cells.append([])
                    continue
                cell_crop = page.crop(cell)
                lines = cell_crop.extract_text_lines(layout=True, return_chars=True)
                visual_rows = []
                if not lines:
                    visual_rows.append({"text": "", "top": None})
                else:
                    lines.sort(key=lambda ln: ln["top"])
                    # Single-pass clustering
                    clusters = []
                    current_cluster = [lines[0]]
                    for ln in lines[1:]:
                        vertical_gap = ln["top"] - current_cluster[-1]["top"]
                        if vertical_gap >= vertical_thresh:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                            continue
                        available_space = cell[2] - current_cluster[-1]["x1"]
                        first_word_width = get_first_word_width(ln)
                        indent_prev = current_cluster[-1]["x0"] - cell[0]
                        indent_candidate = ln["x0"] - cell[0]
                        if abs(indent_prev - indent_candidate) > indent_thresh:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                        elif BEGIN_LINE_PATTERN.search(ln["text"].strip()):
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                        elif available_space >= first_word_width:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                        else:
                            current_cluster.append(ln)
                    clusters.append(current_cluster)

                    def convert_to_subscript(s):
                        mapping = {
                            "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
                            "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
                            "a": "ₐ", "A": "ₐ", "b": "ᵦ", "B": "ᵦ", "c": "c", "C": "c",
                            "d": "d", "D": "d", "e": "ₑ", "E": "ₑ", "f": "f", "F": "f",
                            "g": "g", "G": "g", "h": "ₕ", "H": "ₕ", "i": "ᵢ", "I": "ᵢ",
                            "j": "ⱼ", "J": "ⱼ", "k": "ₖ", "K": "ₖ", "l": "ₗ", "L": "ₗ",
                            "m": "ₘ", "M": "ₘ", "n": "ₙ", "N": "ₙ", "o": "ₒ", "O": "ₒ",
                            "p": "ₚ", "P": "ₚ", "q": "q", "Q": "q", "r": "ᵣ", "R": "ᵣ",
                            "s": "ₛ", "S": "ₛ", "t": "ₜ", "T": "ₜ", "u": "ᵤ", "U": "ᵤ",
                            "v": "ᵥ", "V": "ᵥ", "w": "w", "W": "w", "x": "ₓ", "X": "ₓ",
                            "y": "y", "Y": "y", "z": "z", "Z": "z"
                        }
                        return "".join(mapping.get(char, char) for char in s)

                    cluster_info = []
                    for clust in clusters:
                        if not clust:
                            continue
                        remove_small_chars(clust)
                        text = " ".join(ln["text"] for ln in clust).strip()
                        min_x0 = min(ln["x0"] for ln in clust)
                        max_x1 = max(ln["x1"] for ln in clust)
                        top_val = min(ln["top"] for ln in clust)
                        sizes = [c.get("size", 0) for ln in clust for c in ln.get("chars", []) if c.get("size")]
                        avg_font_size = sum(sizes) / len(sizes) if sizes else 0
                        cluster_info.append({
                            "text": text,
                            "min_x0": min_x0,
                            "max_x1": max_x1,
                            "top": top_val,
                            "font_size": avg_font_size
                        })

                    grouped_clusters = []
                    if cluster_info:
                        current_group = [cluster_info[0]]
                        for c in cluster_info[1:]:
                            # If the vertical difference is small, just add to the current group.
                            if abs(c["top"] - current_group[0]["top"]) < 5:
                                current_group.append(c)
                            else:
                                # Check if this new cluster is a short alphanumeric candidate (subscript)
                                trimmed = c["text"].strip()
                                if len(trimmed) <= 2 and re.fullmatch(r"[A-Za-z0-9]+", trimmed):
                                    # Merge it with the current group even though the vertical gap is larger.
                                    current_group.append(c)
                                else:
                                    grouped_clusters.append(current_group)
                                    current_group = [c]
                        grouped_clusters.append(current_group)
                    else:
                        grouped_clusters = []

                    merged_rows = []
                    tol_top = 2
                    tol_font = 1
                    for group in grouped_clusters:
                        baseline_cluster = max(group, key=lambda c: len(c["text"]))
                        baseline_top = baseline_cluster["top"]
                        baseline_font = baseline_cluster.get("font_size", 0)
                        filtered_group = [
                            c for c in group
                            if not ((baseline_top - c["top"]) > tol_top and (baseline_font - c["font_size"]) > tol_font)
                        ]
                        if not filtered_group:
                            continue
                        filtered_group.sort(key=lambda c: c["min_x0"])
                        merged_text = filtered_group[0]["text"]
                        current_max = filtered_group[0]["max_x1"]
                        for c in filtered_group[1:]:
                            trimmed_text = c["text"].strip()
                            # If the candidate is a short alphanumeric string (one or two characters)
                            if len(trimmed_text) <= 2 and re.fullmatch(r"[A-Za-z0-9]+", trimmed_text):
                                candidate = convert_to_subscript(trimmed_text)
                                # If the merged text ends with a closing parenthesis,
                                # insert the candidate before that.
                                if merged_text.endswith(")"):
                                    merged_text = merged_text[:-1].rstrip() + candidate + ")"
                                else:
                                    merged_text = merged_text.rstrip() + candidate
                            else:
                                gap = c["min_x0"] - current_max
                                if gap < 3:
                                    merged_text = merged_text.rstrip() + c["text"]
                                else:
                                    merged_text = merged_text + " " + c["text"]
                            current_max = max(current_max, c["max_x1"])

                        merged_text = re.sub(
                            r'([A-Za-z])\s+([A-Za-z])((?:[₀₁₂₃₄₅₆₇₈₉])\b)',
                            r'\1\3\2',
                            merged_text
                        )
                        base_indent = lines[0]["x0"] - cell[0]
                        indent = filtered_group[0]["min_x0"] - cell[0]
                        if indent > base_indent + indent_thresh:
                            merged_text = f'\t{merged_text}'
                        merged_rows.append({"text": merged_text, "top": filtered_group[0]["top"]})
                    visual_rows.extend(merged_rows)
                row_cells.append(visual_rows)
            table_rows.append(row_cells)
        custom_tables.append(table_rows)
    return custom_tables


def remove_small_chars(clust):
    for ln in clust:
        if all(c["size"] < 7.5 for c in ln["chars"]):
            logging.debug("Subscript detected: " + ln["text"])
            return
        median_y1 = sorted([char["y1"] for char in ln['chars']])[len(ln['chars']) // 2]
        string = ""
        i = 0
        for char in ln["text"]:
            if char == ' ':
                string += char
            elif ln["chars"][i]["size"] > 7.5 and ln["chars"][i]["y1"] < median_y1 + 1:
                string += ln["chars"][i]["text"]
                i += 1
            else:
                logging.debug("Subscript detected: " + ln["chars"][i]["text"])
                ln["chars"].pop(i)
        while "  " in string:
            string = string.replace("  ", " ")
        ln["text"] = string.strip()


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
    sorted_lines = sorted(lines, key=lambda x: x['top'])
    groups = []
    if not sorted_lines:
        return groups

    # Start the first group with the first line.
    current_group = [sorted_lines[0]]
    # Use the first line's top as the reference value.
    current_avg_top = sorted_lines[0]['top']

    for line in sorted_lines[1:]:
        # If the difference between the current line's top and the group's average is below the threshold,
        # consider it part of the same group.
        if abs(line['top'] - current_avg_top) < threshold:
            current_group.append(line)
            # Update the average "top" value for the current group.
            current_avg_top = sum(item['top'] for item in current_group) / len(current_group)
        else:
            groups.append(current_group)
            current_group = [line]
            current_avg_top = line['top']
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
                    cell_entries.append({
                        "col": col_idx,
                        "top": item["top"],
                        "text": item["text"]
                    })

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
    equipment = ''
    parameter = ''
    range_val = ''
    frequency = ''
    cmc = ''
    preComment = ''
    comment = ''

    data_rows = []
    for row in data[1:]:
        row[0] = row[0].replace("(cont)", "").strip(' ')
        if headers[0] == 'Parameter/Equipment':
            frequency = ''
            if row[0].endswith("–"):
                equipment = row[0].strip('–').strip()
                parameter = ''
                range_val = ''
                cmc = ''
                preComment = row[3]
                comment = ''
                continue
            elif '–' in row[0]:
                equipment, parameter = [part.strip() for part in row[0].split('–', 1)]
            elif row[0].startswith('\t'):
                parameter = row[0].strip('\t')
            elif row[0]:
                equipment = row[0]
                parameter = ''

            range_val = row[1].strip('\t')
            cmc = row[2]

            if row[3].startswith('\t'):
                comment = preComment + '; ' + row[3].strip('\t')
            elif row[3]:
                comment = row[3]
                preComment = ''

        elif headers[0] == 'Parameter/Range':
            if '–' in row[0]:
                # equipment, parameter = [part.strip() for part in row[0].split('–', 1)]
                equipment = ''
                parameter = row[0]
                range_val = ''
                frequency = ''
                cmc = ''
                preComment = row[3]
                comment = ''
                continue
            elif row[0].startswith('\t'):
                range_val = row[0].strip('\t')

            frequency = row[1]
            cmc = row[2]

            if row[3].startswith('\t'):
                comment = preComment + '; ' + row[3].strip('\t')
            elif row[3]:
                comment = row[3]
                preComment = ''

        if not cmc:
            continue
        data_rows.append([equipment, parameter, range_val, frequency, cmc, comment])
    return data_rows


if __name__ == "__main__":
    # Initialize file dialog for PDF selection.
    root = tk.Tk()
    root.withdraw()
    pdf_path = filedialog.askopenfilename(title="Select PDF file", filetypes=[("PDF files", "*.pdf")])
    if not pdf_path:
        print("No PDF selected. Exiting.")
        exit()
    main(pdf_path)
