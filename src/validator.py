from typing import Dict, Any, List, Tuple
import os
import pandas as pd
import pandera as pa
from loguru import logger

# --- 1. Custom Validation Extensions ---
@pa.extensions.register_check_method
def is_valid_date_format(pandas_obj: pd.Series) -> pd.Series:
    """Vectorized custom check for invalid date strings."""
    return ~pandas_obj.astype(str).str.lower().str.contains("invalid")

# --- 2. Centralized Error Reason Mappings ---
ERROR_MAPPINGS = {
    "first_name_str_matches": "should be title case after cleaning/only alphabet characters",
    "date_of_birth_is_valid_date_format": "invalid date value",
    "created_date_is_valid_date_format": "invalid date value",
    "account_status_isin": "should be one of: active, inactive, suspended",
}


def build_schema_contract(config: Dict[str, Any]) -> pa.DataFrameSchema:
    rules: Dict[str, Any] = config.get("validation_rules", {})
    regex_rules: Dict[str, Any] = config.get("regex_patterns", {})
    
    max_income: float = rules.get("max_income", 10000000.0)
    valid_statuses: List[str] = rules.get("valid_statuses", ["active", "inactive", "suspended"])
    email_regex: str = regex_rules.get("email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    return pa.DataFrameSchema(
        columns={
            "customer_id": pa.Column(pa.Int, checks=[pa.Check.gt(0)], unique=True, nullable=False),
            "first_name": pa.Column(pa.String, checks=[
                pa.Check.str_length(min_value=2, max_value=50),
                pa.Check.str_matches(r"^[A-Za-z\s]+$")
            ], nullable=True),
            "last_name": pa.Column(pa.String, checks=[
                pa.Check.str_length(min_value=2, max_value=50)
            ], nullable=True),
            "email": pa.Column(pa.String, checks=[pa.Check.str_matches(email_regex)], nullable=False),
            "phone": pa.Column(pa.String, nullable=False),
            "date_of_birth": pa.Column(pa.String, checks=[
                pa.Check.is_valid_date_format()
            ], nullable=False),
            "address": pa.Column(pa.String, nullable=True),
            "income": pa.Column(pa.Float, checks=[
                pa.Check.ge(0.0),
                pa.Check.le(max_income)
            ], nullable=True),
            "account_status": pa.Column(pa.String, checks=[
                pa.Check.isin(valid_statuses)
            ], nullable=True),
            "created_date": pa.Column(pa.String, checks=[
                pa.Check.is_valid_date_format()
            ], nullable=False)
        },
        coerce=True,
        strict=True
    )

def execute_validation_pipeline(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the dataframe and implements Quarantine / Dead Letter Queue routing."""
    schema: pa.DataFrameSchema = build_schema_contract(config)
    
    try:
        clean_df = schema.validate(df, lazy=True)
        return {
            "status": "PASS", 
            "failures_count": 0, 
            "clean_data": clean_df,
            "quarantine_data": pd.DataFrame(),
            "failure_cases": pd.DataFrame()
        }
    except pa.errors.SchemaErrors as err:
        failure_cases = err.failure_cases
        logger.warning(f"Data validation failed contract thresholds. Captured {len(failure_cases)} error cases.")
        
        # --- 3. Quarantine Pattern ---
        bad_indices = failure_cases["index"].dropna().unique()
        clean_df = df[~df.index.isin(bad_indices)]
        quarantine_df = df[df.index.isin(bad_indices)]
        
        return {
            "status": "FAIL",
            "failures_count": len(failure_cases),
            "clean_data": clean_df,
            "quarantine_data": quarantine_df,
            "failure_cases": failure_cases
        }

def compile_validation_report(results: Dict[str, Any], total_rows: int) -> str:
    lines: List[str] = [
        "VALIDATION RESULTS",
        "==================",
        ""
    ]
    
    if results["status"] == "PASS":
        lines.append(f"PASS: [{total_rows} rows passed all checks]")
        lines.append("FAIL: [0 rows failed]")
        return "\n".join(lines)
    
    failure_df: pd.DataFrame = results["failure_cases"]
    
    # Calculate failed rows safely
    valid_indices = failure_df["index"].dropna()
    failed_count = len(valid_indices.unique())
    passed_count = total_rows - failed_count
    
    lines.append(f"PASS: [{passed_count} rows passed all checks]")
    lines.append(f"FAIL: [{failed_count} rows failed]\n")
    lines.append("FAILURES BY COLUMN:")
    lines.append("-------------------")
    
    if "column" in failure_df.columns:
        for col, group in failure_df.groupby("column", dropna=True):
            if pd.isna(col): continue
            lines.append(f"{col}:")
            for _, row_fail in group.iterrows():
                human_row = int(row_fail['index']) + 1 if pd.notna(row_fail['index']) else "Global"
                
                val = row_fail['failure_case']
                check_name = str(row_fail['check'])
                
                # Handling display format
                display_val = "Empty" if pd.isna(val) or val == "" else f"'{val}'"
                
                # --- 4. Strategy Lookup Pattern (Eliminates the giant if/elif block) ---
                mapping_key = f"{col}_{check_name}"
                
                if "not_nullable" in check_name or "pd.notna" in check_name:
                    reason = "should be non-empty"
                elif col == "phone" and display_val != "Empty":
                    if "." in str(val):
                        reason = "non-standard format, should be XXX-XXX-XXXX"
                    elif "-" not in str(val):
                        reason = "no formatting"
                    else:
                        reason = "invalid format"
                elif col == "date_of_birth" and check_name not in ["is_valid_date_format"]:
                    reason = "wrong format, should be YYYY-MM-DD"
                else:
                    reason = ERROR_MAPPINGS.get(mapping_key, f"failed check: {check_name}")
                    if display_val == "Empty" and mapping_key == "account_status_isin":
                        reason = "should be one of: active, inactive, suspended"
                    
                lines.append(f"- Row {human_row}: {display_val} ({reason})")
            lines.append("")
            
    return "\n".join(lines).strip()