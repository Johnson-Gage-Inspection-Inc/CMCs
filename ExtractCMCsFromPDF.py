from pdfplumber import open as pdfplumber_open
from pandas import DataFrame, notna
from tkinter import filedialog, Tk


def expand_rows(df):
    expanded_data = []

    for _, row in df.iterrows():
        range_split = row["Range"].split("\n") if notna(row["Range"]) else []
        cmc_split = row["CMC (±)"].split("\n") if notna(row["CMC (±)"]) else []
        comments_split = (
            row["Comments"].split("\n") if notna(row["Comments"]) else []
        )
        parameter_split = (
            row["Parameter"].split("\n") if notna(row["Parameter"]) else []
        )

        if len(range_split) == len(cmc_split) and len(range_split) > 1:
            num_rows = len(range_split)
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
                        "CMC (±)": cmc_split[i],
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
                # Remove duplicate headers
                headers = extracted_table[0]
                filtered_table = [row for row in extracted_table[1:] if row != headers]
                tables.extend(filtered_table)

    # Convert extracted tables into a structured DataFrame
    df = DataFrame(tables, columns=headers)

    # Splitting 'Parameter/Equipment' column into 'Equipment' and 'Parameter'
    if "Parameter/Equipment" in df.columns:
        df[["Equipment", "Parameter"]] = df["Parameter/Equipment"].str.split(
            "–", n=1, expand=True
        )
        df["Parameter"] = df["Parameter"].str.lstrip("\n")  # Remove leading linebreak
        df.drop(columns=["Parameter/Equipment"], inplace=True)

    # Rename the CMC column by removing numbers and commas
    for col in df.columns:
        if "CMC" in col:
            new_col_name = "CMC (±)"
            df.rename(columns={col: new_col_name}, inplace=True)
            break  # Assuming only one CMC column needs renaming

    # Reorder columns to desired order
    desired_order = ["Equipment", "Parameter", "Range", "CMC (±)", "Comments"]
    df = df[[col for col in desired_order if col in df.columns]]

    # Expand rows where necessary
    df = expand_rows(df)

    return df


def browse_file():
    root = Tk()
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
