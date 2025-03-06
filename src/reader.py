import pdfplumber
import pandas as pd
import re


# (Optionally import from a "utils.py" if you want smaller functions)
# from .utils import remove_superscripts, split_parameter_equipment, split_parameter_range


def remove_superscripts(text):
    if not text:
        return text
    return re.sub(r"[\u00B2\u00B3\u00B9\u2070-\u209F\d]$", "", text)


def split_parameter_equipment(cell_value):
    if not cell_value:
        return ("", "")
    split_cols = re.split(r"\s*[-–]\s*", cell_value, maxsplit=1)
    if len(split_cols) == 2:
        equipment, param = split_cols
        return (equipment.strip(), param.strip())
    else:
        return ("", cell_value.strip())


def split_parameter_range(cell_value):
    if not cell_value:
        return ("", "")
    lines = [ln.strip() for ln in cell_value.splitlines() if ln.strip()]
    if len(lines) == 1:
        return (lines[0], "")
    else:
        return (lines[0], lines[-1])


def cleanColumn(col):
    # Example: remove '(cont)' from the strings
    return col.str.replace(r"\(cont\)", "", regex=True).str.strip()


def parse_page_table(df_page):
    """
    Convert a single extracted table (list of lists) into a cleaned DataFrame.
    """
    # Ensure columns exist
    df_page["Equipment"] = df_page.get("Equipment", "")
    df_page["Parameter"] = df_page.get("Parameter", "")
    df_page["Range"] = df_page.get("Range", "")
    df_page["Frequency"] = df_page.get("Frequency", "")
    df_page["CMC (±)"] = df_page.get("CMC (±)", "")
    df_page["Comments"] = df_page.get("Comments", "")

    # 1) If "Parameter/Equipment" col => split into "Equipment", "Parameter"
    if "Parameter/Equipment" in df_page.columns:
        eqp_par = df_page["Parameter/Equipment"].apply(split_parameter_equipment)
        df_page["Equipment"], df_page["Parameter"] = zip(*eqp_par)
        df_page.drop(columns=["Parameter/Equipment"], inplace=True)

    # 2) If "Parameter/Range" col => split into "Parameter", "Range"
    if "Parameter/Range" in df_page.columns:
        pr_cols = df_page["Parameter/Range"].apply(split_parameter_range)
        df_page["Parameter"], df_page["Range"] = zip(*pr_cols)
        df_page.drop(columns=["Parameter/Range"], inplace=True)

    # 3) Rename any columns that contain "CMC" => "CMC (±)"
    for col in list(df_page.columns):
        if "CMC" in col and col != "CMC (±)":
            df_page.rename(columns={col: "CMC (±)"}, inplace=True)

    # 4) Remove duplicate columns if needed
    df_page = df_page.loc[:, ~df_page.columns.duplicated()]

    # 5) Reorder columns
    final_cols = ["Equipment", "Parameter", "Range", "Frequency", "CMC (±)", "Comments"]
    existing_cols = [c for c in final_cols if c in df_page.columns]
    df_page = df_page[existing_cols]

    return df_page


def extract_pdf_tables_to_df(pdf_path):
    """
    Reads the PDF, extracts tables, merges them into one DataFrame,
    and cleans columns minimally (no row expansions yet).
    """
    big_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Extract multiple tables from each page
            tables = page.extract_tables()
            for extracted_table in tables:
                if extracted_table:
                    headers = extracted_table[0]
                    data_rows = extracted_table[1:]
                    df_page = pd.DataFrame(data_rows, columns=headers)
                    df_page.to_csv(f"tests/test_data/tables/pre/page{page.page_number}_table{i}.csv", index=False, encoding="utf-8-sig")
                    parsed_df_page = parse_page_table(df_page)
                    parsed_df_page.to_csv(f"tests/test_data/tables/parsed/page{page.page_number}_table{i}.csv", index=False, encoding="utf-8-sig")
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

    # Remove superscripts
    for col in df_all.columns:
        df_all[col] = df_all[col].apply(
            lambda x: remove_superscripts(str(x)) if pd.notna(x) else x
        )

    # Clean columns
    df_all["Equipment"] = cleanColumn(df_all["Equipment"])
    df_all["Parameter"] = cleanColumn(df_all["Parameter"])

    return df_all
