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
    big_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = custom_extract_tables(page)
            for table in tables:
                table1 = fix_rows(table)


def fix_rows(table):

    return table


def custom_extract_tables(page, table_settings=None, vertical_thresh=3, indent_thresh=3):
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
      indent_thresh: (not used here for splitting, but can be used later to flag sub-rows)

    Returns:
      A list of tables. Each table is structured as:
         table -> row -> cell -> list of visual row dicts.
    """
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
                    for ln in lines[1:]:
                        if ln["top"] - current_cluster[-1]["top"] < vertical_thresh:
                            current_cluster.append(ln)
                        else:
                            clusters.append(current_cluster)
                            current_cluster = [ln]
                    clusters.append(current_cluster)

                    # For each cluster, merge the text and record top and indent.
                    for clust in clusters:
                        # The indent is computed as the minimum x0 in the cluster, relative to the cell's left edge.
                        min_x0 = min(ln["x0"] for ln in clust)
                        indent = min_x0 - cell[0]
                        # The top coordinate is the minimum 'top' in the cluster.
                        top_val = min(ln["top"] for ln in clust)
                        # Concatenate the text from each line in order.
                        text = " ".join(ln["text"] for ln in clust)
                        visual_rows.append({"text": text, "top": top_val, "indent": indent})
                row_cells.append(visual_rows)
            table_rows.append(row_cells)
        custom_tables.append(table_rows)

    return custom_tables

# Example usage:
# with pdfplumber.open("2820-01-page1.pdf") as pdf:
#     page = pdf.pages[0]
#     tables = custom_extract_tables(page)
#     for table in tables:
#         for row in table:
#             for cell in row:
#                 print(cell)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    pdf_path = filedialog.askopenfilename(title="Select PDF file", filetypes=[("PDF files", "*.pdf")])
    if not pdf_path:
        print("No PDF selected. Exiting.")
        exit()

    main(pdf_path, save_intermediate=True)
