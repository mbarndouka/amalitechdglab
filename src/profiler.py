import os
import pandas as pd
from loguru import logger
from typing import Dict, Any, List

def load_raw_data(file_path: str) -> pd.DataFrame:
    """
    Safely loads the target dataset from disk into memory.
    
    Args:
        file_path (str): The absolute or relative path to the CSV file.

    Returns:
        pd.DataFrame: The loaded dataset.
        
    Raises:
        FileNotFoundError: If the specified file_path does not exist.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        logger.info(f"Successfully loaded {len(df)} rows for pure functional profiling.")
        return df
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        raise
    
def analyze_completeness(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    total_rows = len(df)
    if total_rows == 0:
        logger.warning("No data to analyze.")
        return {}
    return {
        col: {
            "percentage": ((total_rows - int(df[col].isna().sum())) / total_rows) * 100,
            "missing_count": int(df[col].isna().sum())
        }
        for col in df.columns
    }
    
def analyze_data_types(df: pd.DataFrame) -> Dict[str, str]:
    return {col: str(dtype).upper() for col, dtype in df.dtypes.items()}

def scan_anomalies(df: pd.DataFrame, config: Dict[str, Any] = None) -> Dict[str, List[str]]:
    valid_statuses = config.get('validation_rules', {}).get('valid_statuses', ['active', 'inactive', 'suspended']) if config else ['active', 'inactive', 'suspended']
    
    issues = {
        "uniqueness_failures": [],
        "date_format_anomalies": [],
        "income_anomalies": [],
        "status_anomalies": []
    }
    
    # 1. Vectorized Uniqueness Check
    if not df['customer_id'].is_unique:
        duplicates = df.loc[df['customer_id'].duplicated(keep=False), 'customer_id'].tolist()
        issues["uniqueness_failures"].append(f"customer_id has duplicates: {duplicates}")
        
    # 2. Vectorized Date Checks
    for date_col in ['date_of_birth', 'created_date']:
        if date_col in df.columns:
            # Check for generic invalid strings or slash/dot formats
            mask_invalid_string = df[date_col].astype(str).str.lower().str.contains('invalid_date', na=False)
            mask_slash_dot = df[date_col].astype(str).str.contains(r'[/.]', regex=True, na=False)
            invalid_dates_idx = df[mask_invalid_string | mask_slash_dot].index
            for idx in invalid_dates_idx:
                issues["date_format_anomalies"].append(f"Row {idx + 1}: {date_col} Non-standard string.'{df.at[idx, date_col]}'")

    # 3. Vectorized Income Checks
    if 'income' in df.columns:
        # Check negative incomes
        numeric_incomes = pd.to_numeric(df['income'], errors='coerce')
        negative_idx = df[numeric_incomes < 0].index
        for idx in negative_idx:
            issues["income_anomalies"].append(f"Row {idx + 1}: Negative income value '{df.at[idx, 'income']}'")
            
        # Check non-numeric/empty values that were originally not empty but failed numeric conversion
        # Empty cells
        empty_income_idx = df[df['income'].isna()].index
        for idx in empty_income_idx:
            issues["income_anomalies"].append(f"Row {idx + 1}: Empty valuation cell")

    # 4. Vectorized Status Checks
    if 'account_status' in df.columns:
        empty_status_idx = df[df['account_status'].isna()].index
        for idx in empty_status_idx:
            issues["status_anomalies"].append(f"Row {idx + 1}: Account status cell is null")
            
        status_clean = df['account_status'].astype(str).str.strip().str.lower()
        invalid_status_mask = ~status_clean.isin(valid_statuses) & df['account_status'].notna()
        invalid_status_idx = df[invalid_status_mask].index
        for idx in invalid_status_idx:
            issues["status_anomalies"].append(f"Row {idx + 1}: Invalid categorical status token '{df.at[idx, 'account_status']}'")
                
    return issues
    
def generate_report_string(completeness: Dict[str, Dict[str, Any]], data_types: Dict[str, str], anomalies: Dict[str, List[str]]) -> str:
    """Pure function focusing solely on text layout generation.

    Takes computed measurements and compiles them into the final text layout.
    """
    critical = len(anomalies["uniqueness_failures"])
    high = len([x for x in anomalies["date_format_anomalies"] if "invalid_date" in x])
    medium = len(anomalies["income_anomalies"]) + len(anomalies["status_anomalies"]) + len([x for x in anomalies["date_format_anomalies"] if "/" in x])

    lines = [
        "DATA QUALITY PROFILE REPORT",
        "===========================\n",
        "COMPLETENESS:"
    ]
    
    for col, m in completeness.items():
        lines.append(f"- {col}: {m['percentage']:.0f}% ({m['missing_count']} missing)")
        
    lines.append("\nDATA TYPES:")
    for col, dtype in data_types.items():
        flag = "✓" if "DATE" not in col and "ID" not in col or dtype != "OBJECT" else "X (Requires casting)"
        lines.append(f"- {col}: {dtype} {flag}")

    lines.append("\nQUALITY ISSUES:")
    counter = 1
    for issue_type, errs in anomalies.items():
        if errs:
            lines.append(f"{counter}. {issue_type.replace('_', ' ').title()}:")
            for err in errs:
                lines.append(f"   - {err}")
            counter += 1

    lines.append("\nSEVERITY:")
    lines.append(f"- Critical (blocks processing): {critical}")
    lines.append(f"- High (data incorrect): {high}")
    lines.append(f"- Medium (needs cleaning): {medium}")

    return "\n".join(lines)
    