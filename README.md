# PII Validation Pipeline

Fintech data quality validation and PII masking pipeline. Ingests raw customer CSV data, profiles it, cleans it, validates schema contracts, detects PII exposure, and masks sensitive fields for GDPR compliance.

## Pipeline Stages

| Stage | Module | Action |
|-------|--------|--------|
| 1 | `profiler.py` | Load raw CSV, analyze completeness, data types, anomalies |
| 2 | `cleaner.py` | Normalize phone/date formats, fix capitalization, impute missing values |
| 3 | `validator.py` | Enforce schema contracts via Pandera (pre- and post-clean) |
| 4 | `detector.py` | Regex scan for PII exposures (email, phone, address, DOB) |
| 5 | `masker.py` | Obfuscate all PII fields (names, emails, phones, addresses, DOBs) |
| 6 | `orchestrator.py` | Write all output assets and audit reports to disk |

## Project Structure

```
.
├── config.toml                  # Pipeline configuration
├── pyproject.toml
├── src/
│   ├── main.py                  # Entry point
│   ├── orchestrator.py          # Pipeline controller
│   ├── profiler.py              # Data quality profiling
│   ├── detector.py              # PII detection
│   ├── validator.py             # Schema validation
│   ├── cleaner.py               # Data cleaning
│   └── masker.py                # PII masking
├── data/
│   ├── raw/
│   │   └── customers_raw.csv    # Input data
│   └── processed/
│       ├── customers_cleaned.csv
│       └── customers_masked.csv
├── reports/
│   ├── data_quality_report.txt
│   ├── validation_results.txt
│   ├── pii_detection_report.txt
│   ├── cleaning_log.txt
│   ├── masked_sample.txt
│   └── pipeline_execution_report.txt
└── logs/
    └── pipeline_run.log
```

## Requirements

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
# With uv
uv sync

# With pip
pip install .
```

Dev dependencies (pytest, black):

```bash
uv sync --group dev
```

## Configuration

Edit `config.toml` to change paths, validation rules, regex patterns, PII target columns, and cleaning defaults.

```toml
[paths]
raw_data_path = "data/raw/customers_raw.csv"
output_dir = "reports"
cleaned_data_output = "data/processed/customers_cleaned.csv"
masked_data_output = "data/processed/customers_masked.csv"

[validation_rules]
max_income = 10000000.0
valid_statuses = ["active", "inactive", "suspended"]

[pii_settings]
target_columns = ["first_name", "last_name", "email", "phone", "date_of_birth", "address"]
```

## Usage

Place raw customer data at `data/raw/customers_raw.csv`, then run:

```bash
python -m src.main
```

On success:

```
✓ SUCCESS: Production Data Refinery Automation Sequence Finalized Cleanly!
  All unified reporting outputs safe inside: 'reports/'
```

Logs written to `logs/pipeline_run.log` (rotates at 10 MB).

## Output Reports

| File | Contents |
|------|----------|
| `data_quality_report.txt` | Completeness, data types, anomaly scan |
| `validation_results.txt` | Pandera schema contract results (pre-clean) |
| `pii_detection_report.txt` | PII exposure counts per field |
| `cleaning_log.txt` | Mutation trace — rows modified per cleaning step |
| `masked_sample.txt` | Side-by-side sample showing original vs masked values |
| `pipeline_execution_report.txt` | Full runtime audit: all 6 stages, row counts, status |

## Masking Strategy

| Field | Method |
|-------|--------|
| Names | First character + asterisk padding |
| Emails | Local mailbox hidden, domain preserved |
| Phones | Area code obscured |
| Addresses | Replaced with block placeholder |
| Dates of Birth | Month and day generalized |

## Running Tests

```bash
pytest
```
