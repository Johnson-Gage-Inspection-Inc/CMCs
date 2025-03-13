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
- Export data at multiple stages of processing for verification

## Installation

### Requirements

- Python 3.8 or higher
- Required packages:

```sh
pip install -r requirements.txt
```

### Dependencies

- pdfplumber - For PDF extraction
- pandas - For data processing
- tkinter - For file dialogs
- Additional modules in the src/ directory

## Usage

1. Run the main script:

```sh
python -m src.main
```

2. In the file dialog, select your PDF file containing calibration scope data.

3. The script will process the file and generate several CSV files in the export directory:
   - `parsed.csv` - Initial extracted and formatted data
   - `range_parsed.csv` - Data with parsed range values
   - `cmc_parsed.csv` - Data with fully parsed CMC values

## Output Files

Each CSV file contains progressively refined data:

- **Initial parsed data** includes columns:
  - Equipment
  - Parameter
  - Range
  - Frequency
  - CMC (±)
  - Comments

- **Range parsed data** adds:
  - range_min
  - range_min_unit
  - range_max
  - range_max_unit

- **CMC parsed data** adds:
  - cmc_base
  - cmc_multiplier
  - cmc_mult_unit
  - cmc_uncertainty_unit

## Advanced Usage

To save intermediate extraction results for debugging:

```python
from src.main import main
main("path/to/your/pdf", save_intermediate=True)
```

This will save JSON files with raw extraction data in json.

## Development

- Source code is in the src directory
- Tests are in tests directory
- Run tests with pytest: `pytest`

## License

This tool is provided for internal use by JGI Quality. For external inquiries, please contact JGI Quality via their [official website](https://www.jgiquality.com).