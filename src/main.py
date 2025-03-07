import tkinter as tk
from tkinter import filedialog
import pdfplumber
# import pandas as pd
# import json
import re

# Regex pattern to match Unicode superscripts ( footnote markers)
SUPERSCRIPT_PATTERN = re.compile(r"[\u00B2\u00B3\u00B9\u2070-\u209F]")

# Pattern to split on a dash (–) that separates equipment from parameter
DASH_PATTERN = re.compile(r"\s*–\s*")


def main(pdf_path, save_intermediate=False):
    # big_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = custom_extract_tables(page)
            for table in tables:
                headers, *rows = table
                header_names = [cell[0]["text"] for cell in headers]
                # df = pd.DataFrame(columns=header_names)
                for row in rows:
                    for cell, header in zip(row, header_names):
                        for cluster in cell:
                            print(str(cluster))
                            # TODO: Handle multi-line cells


def custom_extract_tables(page, table_settings=None, vertical_thresh=12, indent_thresh=4):
    """
    Custom table extraction from a pdfplumber Page.

    Instead of returning a simple list of lists of strings,
    this function returns a list of tables, where each table is a list of rows,
    each row is a list of cells, and each cell is represented as a list of visual rows.

    Each visual row is a dict with:
      - 'text': the extracted text for that wrapped line,
      - 'top': the vertical coordinate (top) of the visual row,
      - 'indent': the horizontal indent (difference between the line's x0 and cell's x0)

    Parameters:
      page: a pdfplumber.Page instance.
      table_settings: (optional) settings to pass to page.find_tables().
      vertical_thresh: maximum vertical gap (in PDF points) to group lines together.
      indent_thresh: threshold (in PDF points) such that if a line's indent exceeds the base indent by more than this,
                     it is not treated as wrapped text.

    Returns:
      A list of tables. Each table is structured as:
         table -> row -> cell -> list of visual row dicts.
    """
    def get_first_word_width(ln):
        """Return the width of the first word in a line using character metadata."""
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

    # Find tables using pdfplumber's built-in finder.
    tables = page.find_tables(table_settings=table_settings)
    custom_tables = []

    for table in tables:
        table_rows = []
        # table.rows: each row is a list of cell objects (each with a bounding box)
        for row in table.rows:
            row_cells = []
            for cell in row.cells:
                if not cell:
                    # If no bbox is available, we simply return an empty cell.
                    row_cells.append([])
                    continue
                # Crop the page to the cell's bounding box.
                cell_crop = page.crop(cell)
                # Extract text lines (with character metadata) from the cell.
                lines = cell_crop.extract_text_lines(layout=True, return_chars=True)
                visual_rows = []
                if not lines:
                    visual_rows.append({"text": "", "top": None, "indent": None})
                else:
                    # Sort lines by their vertical position.
                    lines.sort(key=lambda ln: ln["top"])
                    # Cluster lines that are close vertically to handle text wrapping.
                    clusters = []
                    current_cluster = [lines[0]]
                    base_indent = current_cluster[0]["x0"] - cell[0]
                    for ln in lines[1:]:
                        vertical_gap = ln["top"] - current_cluster[-1]["top"]
                        ln_indent = ln["x0"] - cell[0]
                        # Check basic conditions: small vertical gap and similar indent.
                        if vertical_gap < vertical_thresh and ln_indent <= base_indent + indent_thresh:
                            # Compute available space on the previous line.
                            available_space = cell[2] - current_cluster[-1]["x1"]
                            first_word_width = get_first_word_width(ln)
                            # If there's enough room for the first word on the previous line,
                            # then this line is not a forced wrap and should start a new cluster.
                            if available_space >= first_word_width:
                                clusters.append(current_cluster)
                                current_cluster = [ln]
                            else:
                                current_cluster.append(ln)
                        else:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                    clusters.append(current_cluster)

                    # For each cluster, merge the text and record top and indent.
                    for clust in clusters:
                        min_x0 = min(ln["x0"] for ln in clust)
                        indent = min_x0 - cell[0]
                        top_val = min(ln["top"] for ln in clust)
                        text = " ".join(ln["text"] for ln in clust)
                        # Mark clusters that are indented.
                        if indent > base_indent + indent_thresh:
                            text = r'\t' + text
                        visual_rows.append({"text": text, "top": top_val, "indent": indent})
                row_cells.append(visual_rows)
            table_rows.append(row_cells)
        custom_tables.append(table_rows)

    return custom_tables


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    pdf_path = filedialog.askopenfilename(title="Select PDF file", filetypes=[("PDF files", "*.pdf")])
    if not pdf_path:
        print("No PDF selected. Exiting.")
        exit()

    main(pdf_path, save_intermediate=True)
