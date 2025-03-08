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
                with open(f"export/pages/page_{page.page_number}.json", "w") as f:
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
                        subscript_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
                        return s.translate(subscript_map)

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
                            if abs(c["top"] - current_group[0]["top"]) < 5:
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
                            gap = c["min_x0"] - current_max
                            if gap < 3:
                                if re.fullmatch(r"\d+", c["text"]):
                                    merged_text = merged_text.rstrip() + convert_to_subscript(c["text"])
                                else:
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

    Header processing:
      - If the first cell’s text is "Parameter/Equipment", it is split into two header columns:
        "Equipment" and "Parameter". A "Frequency" column is inserted between the Range and CMC columns.
    Data row processing:
      - For the first cell, if a dash (–) is found in the first visual line, the text before the dash is used
        as Equipment and any trailing text on that line is ignored.
      - Any subsequent visual lines in the first cell are treated as Parameter entries.
      - For the other cells (Range, CMC, Comments), each visual row becomes a sub-row.
      - The final number of sub-rows is the maximum number of lines found among the cells.
      - For each sub-row, missing values are filled with an empty string and Frequency is always blank.
    """
    import re

    dash_pattern = re.compile(r"\s*–\s*")

    # Process header row (first row of input_data)
    header_row = input_data[0]
    header0_text = "".join(item.get("text", "").strip() for item in header_row[0])
    if header0_text == "Parameter/Equipment":
        # Although header texts are available in the JSON,
        # we enforce the expected column names.
        columns = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]
    else:
        columns = ["".join(item.get("text", "").strip() for item in cell)
                   for cell in header_row]

    # Override to expected column names.
    columns = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]

    data_rows = []
    # Process each data row (skip header row)
    for row in input_data[1:]:
        # Process cell0: Equipment/Parameter column
        cell0_texts = [item.get("text", "").strip() for item in row[0] if item.get("text")]
        if cell0_texts:
            first_line = cell0_texts[0]
            parts = dash_pattern.split(first_line)
            if len(parts) > 1:
                equipment = parts[0].strip()
                # Use trailing text only if non-empty; otherwise, ignore it.
                first_param = parts[1].strip()
                parameters = [first_param] if first_param else []
                # Append any subsequent visual rows as additional parameter lines.
                if len(cell0_texts) > 1:
                    for text in cell0_texts[1:]:
                        if text:
                            parameters.append(text)
            else:
                equipment = ""
                parameters = cell0_texts
        else:
            equipment = ""
            parameters = []

        # Process the other cells (Range, CMC (±), Comments)
        cell1_texts = [item.get("text", "").strip() for item in row[1] if item.get("text")]
        cell2_texts = [item.get("text", "").strip() for item in row[2] if item.get("text")]
        cell3_texts = [item.get("text", "").strip() for item in row[3] if item.get("text")]

        # Determine the number of sub-rows to output
        num_subrows = max(len(parameters), len(cell1_texts), len(cell2_texts), len(cell3_texts))
        for i in range(num_subrows):
            param = parameters[i] if i < len(parameters) else ""
            range_val = cell1_texts[i] if i < len(cell1_texts) else ""
            cmc_val = cell2_texts[i] if i < len(cell2_texts) else ""
            comments_val = cell3_texts[i] if i < len(cell3_texts) else ""
            # Frequency is not provided; leave it empty.
            data_rows.append([equipment, param, range_val, "", cmc_val, comments_val])

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
