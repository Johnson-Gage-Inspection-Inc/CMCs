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
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = custom_extract_tables(page)
            # Save intermediate results if requested
            if save_intermediate:
                with open(f"export/pages/json/page{page.page_number}.json", "w") as f:
                    f.write(json.dumps(tables, indent=2))
            for table in tables:
                headers, *rows = table
                header_names = [cell[0]["text"] for cell in headers]
                for row in rows:
                    for cell, header in zip(row, header_names):
                        for cluster in cell:
                            print(str(cluster))
                            # TODO: Handle multi-line cells


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


def custom_parse_table(input_data):
    """
    Convert the PDF table structure into a pandas DataFrame with the following columns:
      Equipment, Parameter, Range, Frequency, CMC (±), Comments

    Processing Logic:
      - Subheader rows (lines ending in "–") define the Equipment field and should be removed.
      - If a line contains "–" but does not end with it, split to get both Equipment and Parameter.
      - Subsequent indented lines (in the same column) are treated as Parameters.
      - All other columns (Range, CMC, Comments) follow their respective structure.
      - Ensure Frequency column is present but left empty.
    """
    dash_pattern = re.compile(r"\s*–\s*")

    # Standardize column names
    columns = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]

    data_rows = []
    equipment = ""  # Keep track of the last known Equipment name
    section_comment = ""  # Track section header comments

    # Process each data row (skip header row)
    for row in input_data[1:]:
        # Process first column: Equipment/Parameter
        cell0_texts = [item.get("text", "").strip() for item in row[0] if item.get("text")]
        cell1_texts = [item.get("text", "").strip() for item in row[1] if item.get("text")]
        cell2_texts = [item.get("text", "").strip() for item in row[2] if item.get("text")]
        cell3_texts = [item.get("text", "").strip() for item in row[3] if item.get("text")]

        # Check if this is a section header row (Range and CMC empty)
        is_header_row = not cell1_texts and not cell2_texts

        if is_header_row and cell0_texts:
            # This is a section header
            first_line = cell0_texts[0]
            if first_line.endswith("–"):
                equipment = first_line.replace("–", "").strip()
            else:
                equipment = first_line.strip()

            # Store section comment if present
            if cell3_texts:
                section_comment = cell3_texts[0]
            continue  # Skip adding this row

        if cell0_texts:
            first_line = cell0_texts[0]
            parts = dash_pattern.split(first_line)

            if len(parts) > 1:
                # Case where Equipment and Parameter are in the same line
                equipment = parts[0].strip()
                first_param = parts[1].strip()
                parameters = [first_param] if first_param else []
                # Add any additional parameters
                parameters.extend([text.lstrip('\t') for text in cell0_texts[1:]])
            else:
                # Normal parameter row under the current equipment
                parameters = [text.lstrip('\t') if text.startswith('\t') else text for text in cell0_texts]
        else:
            parameters = []

        # Process comments - combine section comment with row comments
        processed_comments = []
        if cell3_texts:
            for comment in cell3_texts:
                if section_comment and not comment == section_comment:
                    # Add section comment as prefix if it's not already there
                    if section_comment not in comment:
                        processed_comments.append(f"{section_comment}; {comment.lstrip('\t')}")
                    else:
                        processed_comments.append(comment)
                else:
                    processed_comments.append(comment)
        elif section_comment and equipment == "Coordinate Measuring Machines (CMM)":
            # If we have a section comment but no row comment for CMM
            processed_comments.append(section_comment)

        # Determine the number of sub-rows needed
        num_subrows = max(len(parameters), len(cell1_texts), len(cell2_texts), len(processed_comments))
        if num_subrows == 0:
            num_subrows = 1  # Ensure at least one row is created

        for i in range(num_subrows):
            # If there's only one parameter, propagate it to every subrow.
            if len(parameters) == 1:
                param = parameters[0]
            else:
                param = parameters[i] if i < len(parameters) else ""
            range_val = cell1_texts[i] if i < len(cell1_texts) else ""
            cmc_val = cell2_texts[i] if i < len(cell2_texts) else ""
            comments_val = processed_comments[i] if i < len(processed_comments) else ""
            data_rows.append([equipment, param, range_val, "", cmc_val, comments_val])

    # Convert to DataFrame
    df = pd.DataFrame(data_rows, columns=columns)
    return df


if __name__ == "__main__":
    # Initialize file dialog for PDF selection.
    root = tk.Tk()
    root.withdraw()
    pdf_path = filedialog.askopenfilename(title="Select PDF file", filetypes=[("PDF files", "*.pdf")])
    if not pdf_path:
        print("No PDF selected. Exiting.")
        exit()
    main(pdf_path)
