# src/ExtractCMCsFromPDF.py
import tkinter as tk
from tkinter import filedialog
from src.reader import extract_pdf_tables_to_df
from src.expander import expand_rows


def browse_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")]
    )


def process_pdf(pdf_file, save_intermediate=True):
    # Step 1: Extract DF (no expansions)
    df_all = extract_pdf_tables_to_df(pdf_file)
    # if save_intermediate:
    #     df_all.to_csv("tests/test_data/intermediate_df.csv", index=False)
    #     print("Saved intermediate_df.csv")

    # Step 2: Expand
    df_expanded = expand_rows(df_all)
    df_expanded.to_csv("extracted_data.csv", index=False)
    print("Saved extracted_data.csv")
    return df_expanded


if __name__ == "__main__":
    pdf_file = browse_file()
    if pdf_file:
        final_df = process_pdf(pdf_file)
        print("Done! See extracted_data.csv.")
    else:
        print("No file selected.")
