# src/ExtractCMCsFromPDF.py
import tkinter as tk
from tkinter import filedialog
from src.reader import extract_tables_by_position, parse_page_table, cleanColumn
from src.expander import expand_frequency_and_cmc, parse_range
import pandas as pd
import pdfplumber
import json


def browse_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")]
    )


def process_pdf(pdf_file, save_intermediate=False):
    # Step 1: Extract DF (no expansions)
    df_all = extract_pdf_tables_to_df(pdf_file)
    if save_intermediate:
        df_all.to_csv("tests/test_data/intermediate_df.csv", index=False)
        print("Saved intermediate_df.csv")

    # Step 2: Expand
    df_expanded = expand_frequency_and_cmc(df_all)
    # Add RangeMin, RangeMax, RangeUnit columns
    df_expanded[["RangeMin", "RangeMax", "RangeUnit"]] = df_expanded["Range"].apply(
        lambda x: pd.Series(parse_range(x))
    )
    df_expanded.to_csv("extracted_data.csv", index=False)
    print("Saved extracted_data.csv")
    return df_expanded


def extract_pdf_tables_to_df(pdf_path):
    """
    Reads the PDF, extracts tables, merges them into one DataFrame,
    and cleans columns minimally (no row expansions yet).
    """
    big_tables = []

    class PDFJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                return super().default(obj)
            except TypeError:
                return str(obj)  # Convert non-serializable objects to strings

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_dict = page.to_dict()
            with open(f"export/pages/json/page{page.page_number}.json", "w") as f:
                json.dump(page_dict, f, indent=4, cls=PDFJSONEncoder)
            # Extract multiple tables from each page
            tables = extract_tables_by_position(page)
            for i, extracted_table in enumerate(tables):
                if extracted_table:
                    headers = extracted_table[0]
                    data_rows = extracted_table[1:]
                    df_page = pd.DataFrame(data_rows, columns=headers)
                    df_page.to_csv(
                        f"export/tables/pre/page{page.page_number}_table{i}.csv",
                        index=False,
                        encoding="utf-8-sig",
                    )
                    parsed_df_page = parse_page_table(df_page)
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

    # Combine all pages
    df_all = pd.concat(big_tables, ignore_index=True)

    # Clean columns
    df_all["Equipment"] = cleanColumn(df_all["Equipment"])
    df_all["Parameter"] = cleanColumn(df_all["Parameter"])

    return df_all


if __name__ == "__main__":
    pdf_file = browse_file()
    if pdf_file:
        final_df = process_pdf(pdf_file)
        print("Done! See extracted_data.csv.")
    else:
        print("No file selected.")
