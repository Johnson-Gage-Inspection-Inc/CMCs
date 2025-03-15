# CMCs PDF Table Extraction Tool

[![Latest Release](https://img.shields.io/github/v/release/Johnson-Gage-Inspection-Inc/CMCs)](https://github.com/Johnson-Gage-Inspection-Inc/CMCs/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Johnson-Gage-Inspection-Inc/CMCs)](https://github.com/Johnson-Gage-Inspection-Inc/CMCs/commits/main/)
[![Issues](https://img.shields.io/github/issues/Johnson-Gage-Inspection-Inc/CMCs)](https://github.com/Johnson-Gage-Inspection-Inc/CMCs/issues)

## Overview

This tool extracts and processes tabular data from calibration scope PDFs, specifically designed for A2LA scope documents. It produces structured CSV files with normalized data for easy analysis and reporting.

## Features

- Extract tables from PDF files with intelligent parsing
- Process specialized calibration data including equipment details and parameters
- Split combined fields (like "Parameter/Equipment") into separate columns
- Parse complex range values into min/max with units
- Process CMC (Calibration and Measurement Capability) data
- Handle hierarchical comments and nested data structures
- Export data in CSV format for analysis

## Usage

1. Download the latest release of `CMCs_PdfToCsv.exe` from the [releases page](https://github.com/Johnson-Gage-Inspection-Inc/CMCs/releases/latest)
2. Run the executable
3. In the file dialog, select your PDF file containing calibration scope data
4. When prompted, specify where to save the processed CSV file
5. The application will process and export the data in CSV format

## Output Data

The final CSV file contains the following columns:

- Equipment
- Parameter
- Range
- Frequency
- CMC (±)
- Comments
- range_min
- range_min_unit
- range_max
- range_max_unit
- frequency_range_min
- frequency_range_min_unit
- frequency_range_max
- frequency_range_max_unit
- cmc_base
- cmc_multiplier
- cmc_mult_unit
- cmc_uncertainty_unit

## Integration with Excel

The repository includes [`CMC_Calculator.xlsm`](CMC_Calculator.xlsm) for further analysis of the extracted data. After generating the CSV file, you can:

1. Open the Excel workbook
2. Use the built-in macros to import and process the CSV data
3. Perform additional calculations and reporting

## Project Structure

- [`src`](src) - Source code directory
  - `main.py` - Entry point for the application
  - `extract.py` - PDF extraction functionality
  - `cmc.py` - CMC data processing
  - `range.py` - Range parsing functionality
- [`tests`](tests) - Test files for the application
- [`CMC_Calculator.xlsm`](CMC_Calculator.xlsm) - Excel workbook for calculating CMCs from the data

## License

This tool is provided for internal use by JGI Quality. For external inquiries, please contact JGI Quality via their [official website](https://www.jgiquality.com).
