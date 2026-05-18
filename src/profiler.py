import os
import pandas as pd
from loguru import logger

def load_raw_data(file_path: str) -> pd.DataFrame:
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
    
def analyze_completeness(df:pd.DataFrame) -> dict:
    total_rows = len(df)
    if total_rows == 0:
        logger.warning("No data to analyze.")
        return{}
    return{
        col:{
            "percentage": ((total_rows - int(df[col].isna().sum())) / total_rows) * 100,
            "missing_count": int(df[col].isna().sum())
        }
        for col in df.columns
    }
    
def analyze_data_types(df: pd.DataFrame) -> dict:
    return {col: str(dtype).upper() for col, dtype in df.dtypes.items()}

def scan_anomalies(df: pd.DataFrame) -> dict:
    issues = {
        "uniqueness_failures": [],
        "date_format_anomalies": [],
        "income_anomalies": [],
        "status_anomalies": []
    }
    
    if not df['customer_id'].is_unique:
        duplicates = df['customer_id'][df['customer_id'].duplicated(keep=False)].tolist()
        issues["uniqueness_failures"].append(f"customer_id has duplicates: {duplicates}")
        
    for idx, row in df.iterrows():
        row_num = idx + 1
        
        for date_col in ['date_of_birth', 'created_date']:
            val = str(row[date_col]).strip()
            if 'invalid_date' in val.lower() or '/' in val or '.' in val:
                issues["date_format_anomalies"].append(f"Row {row_num}: {date_col} Non-standard string.'{val}'")
                
            try:
                income_val = float(row['income'])
                if income_val < 0:
                    issues["income_anomalies"].append(f"Row {row_num}: Negative income value '{income_val}'")
            except (ValueError, TypeError):
                if pd.isna(row['income']):
                    issues["income_anomalies"].append(f"Row {row_num}: Empty valuation cell")
                    
            status = str(row['account_status']).strip()
            if pd.isna(row['account_status']):
                issues["status_anomalies"].append(f"Row {row_num}: Account status cell is null")
            elif status not in ['active', 'inactive', 'suspended']:
                issues["status_anomalies"].append(f"Row {row_num}: Invalid categorical status token '{status}'")
                
    return issues
    
def generate_report_string(completeness: dict, data_types: dict, anomalies: dict) -> str:
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
    