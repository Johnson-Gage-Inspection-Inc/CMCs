# PDF Table Extraction Script

## Overview
This script extracts tabular data from a calibration scope PDF and formats it into a structured CSV file. It processes the scope document provided by A2LA and JGI Quality to create a tidy dataset for further analysis.

## Source Documents
- A2LA Directory: [JGI Quality Scope](https://customer.a2la.org/index.cfm?event=directory.detail&labPID=46ECE43E-423E-465E-8FBB-36DC011ED988)
- JGI Quality Website: [Scope PDF](https://www.jgiquality.com/_files/ugd/cf351a_08c216c7b17d49e799faea8e7125925b.pdf)

## Features
- Extracts tables from a selected PDF file.
- Splits "Parameter/Equipment" into separate "Equipment" and "Parameter" columns.
- Cleans column names, ensuring a standardized format.
- Expands rows where multiple values exist within a single row, ensuring proper data normalization.
- Outputs a cleaned CSV file for easy data analysis.

## Installation
### Requirements
- Python 3.8+
- Required Python packages:
  ```sh
  pip install pdfplumber pandas tkinter
  ```

## Usage
1. Run the script:
   ```sh
   python extract_pdf_tables.py
   ```
2. A file selection dialog will appear. Choose the PDF file containing the scope data.
3. The script processes the file and saves the extracted data as `extracted_data.csv`.

## Output
- The resulting CSV file (`extracted_data.csv`) contains the structured data with the following columns:
  - Equipment
  - Parameter
  - Range
  - CMC (±)
  - Comments

## Notes
- The script only splits rows when clear splitting rules apply (i.e., when Range and CMC contain an equal number of line breaks).
- If a row does not meet splitting conditions, it remains unchanged.

## License
This script is provided for internal use by JGI Quality and affiliated auditors. For external inquiries, please contact JGI Quality via their [official website](https://www.jgiquality.com).

