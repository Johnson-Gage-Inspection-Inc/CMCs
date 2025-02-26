from pdfplumber import open as pdfplumber_open
from pandas import DataFrame, notna
from tkinter import filedialog, Tk


def expand_rows(df):
    expanded_data = []

    for _, row in df.iterrows():
        # Use splitlines() to handle various newline conventions
        range_split = row["Range"].splitlines() if notna(row["Range"]) else []
        cmc_split = row["CMC (±)"].splitlines() if notna(row["CMC (±)"]) else []
        comments_split = row["Comments"].splitlines() if notna(row["Comments"]) else []
        parameter_split = (
            row["Parameter"].splitlines() if notna(row["Parameter"]) else []
        )

        # If there are multiple range entries, expand the row.
        if len(range_split) > 1:
            num_rows = len(range_split)
            # If the split count for CMC (or others) doesn't match, duplicate the value
            cmc_expanded = (
                cmc_split if len(cmc_split) == num_rows else [row["CMC (±)"]] * num_rows
            )
            comments_expanded = (
                comments_split
                if len(comments_split) == num_rows
                else [row["Comments"]] * num_rows
            )
            parameter_expanded = (
                parameter_split
                if len(parameter_split) == num_rows
                else (
                    [row["Parameter"]] * num_rows
                    if row["Parameter"]
                    else [None] * num_rows
                )
            )

            for i in range(num_rows):
                expanded_data.append(
                    {
                        "Equipment": row["Equipment"],
                        "Parameter": parameter_expanded[i],
                        "Range": range_split[i],
                        "CMC (±)": cmc_expanded[i],
                        "Comments": comments_expanded[i],
                    }
                )
        else:
            expanded_data.append(row.to_dict())

    return DataFrame(expanded_data)


def extract_pdf_tables(pdf_path):
    tables = []
    with pdfplumber_open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_table = page.extract_table()
            if extracted_table:
                headers = extracted_table[0]
                filtered_table = [row for row in extracted_table[1:] if row != headers]
                tables.extend(filtered_table)

    df = DataFrame(tables, columns=headers)

    # Use a regex split to separate "Parameter/Equipment"
    if "Parameter/Equipment" in df.columns:
        # Splits on any dash (hyphen or en dash) possibly surrounded by whitespace
        split_cols = df["Parameter/Equipment"].str.split(
            r"\s*[-–]\s*", n=1, expand=True
        )
        df["Equipment"] = split_cols[0]
        df["Parameter"] = split_cols[
            1
        ].str.lstrip()  # remove any leading whitespace/newlines
        df.drop(columns=["Parameter/Equipment"], inplace=True)

    # Rename the CMC column by looking for a column containing "CMC"
    for col in df.columns:
        if "CMC" in col:
            df.rename(columns={col: "CMC (±)"}, inplace=True)
            break

    desired_order = ["Equipment", "Parameter", "Range", "CMC (±)", "Comments"]
    df = df[[col for col in desired_order if col in df.columns]]

    df = expand_rows(df)

    return df


def browse_file():
    root = Tk()
    root.withdraw()
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
