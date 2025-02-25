# This script should help get the CMCs from the PDFs into a usable format

import pdfplumber
import pandas as pd
import tkinter as tk
from tkinter import filedialog


def extract_pdf_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_table = page.extract_table()
            if extracted_table:
                tables.extend(extracted_table)

    # Convert extracted tables into a structured DataFrame
    df = pd.DataFrame(tables)
    return df


def browse_file():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
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
