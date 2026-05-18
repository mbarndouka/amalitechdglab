from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from loguru import logger

def normalize_phone_vector(phone_series: pd.Series) -> Tuple[pd.Series, int]:
    """Vectorized normalization of messy phone numbers to XXX-XXX-XXXX format.

    Args:
        phone_series: The target messy string series.

    Returns:
        A tuple containing the cleaned phone series and the absolute count of modified rows.
    """
    # Extract only the raw digits from the string vector
    digits_only = phone_series.astype(str).str.replace(r"\D", "", regex=True)
    
    # Isolate valid 10-digit components
    valid_mask = digits_only.str.len() == 10
    
    # Reformat using vectorized slicing
    cleaned_phones = phone_series.copy()
    cleaned_phones[valid_mask] = (
        digits_only[valid_mask].str[:3] + "-" +
        digits_only[valid_mask].str[3:6] + "-" +
        digits_only[valid_mask].str[6:]
    )
    
    # Identify how many items did not match the ideal standard configuration initially
    modified_count = int((phone_series != cleaned_phones).sum())
    return cleaned_phones, modified_count

def normalize_date_vector(date_series: pd.Series) -> Tuple[pd.Series, int]:
    """Vectorized standardization of messy dates to YYYY-MM-DD format safely.

    Args:
        date_series: The target date string series.

    Returns:
        A tuple containing the cleaned date string series and the count of modified rows.
    """
    # Replace explicit 'invalid_date' string entries with actual NaT (Not a Time)
    sanitized = date_series.astype(str).str.strip()
    invalid_mask = sanitized.str.lower().str.contains("invalid")
    
    # Coerce to datetime vectors cleanly using pandas C-optimized engine
    datetime_coerced = pd.to_datetime(sanitized.where(~invalid_mask), errors='coerce')
    
    # Format valid dates to YYYY-MM-DD, map NaT/Null entries back to 'invalid_date' placeholder
    cleaned_dates = datetime_coerced.dt.strftime('%Y-%m-%d')
    cleaned_dates = cleaned_dates.fillna("invalid_date")
    
    modified_count = int((date_series != cleaned_dates).sum())
    return cleaned_dates, modified_count

def execute_cleaning_pipeline(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes vectorized transformations to clean and standardize the DataFrame.
    
    Operations include filling missing names, standardizing phone numbers,
    coercing invalid dates, and normalizing string casing.
    
    Args:
        df (pd.DataFrame): The raw dataframe to clean.
        config (dict): Configuration mappings for imputation and formatting.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: The newly cleaned DataFrame.
            - dict: A metrics dictionary logging how many rows were mutated per column.
    """
    cleaned_df = df.copy()
    defaults = config.get("cleaning_defaults", {})
    
    placeholder = defaults.get("placeholder_text", "[UNKNOWN]")
    default_inc = defaults.get("default_income", 0.0)
    default_stat = defaults.get("default_status", "unknown")

    # --- 1. Normalization Step ---
    cleaned_df["phone"], phone_mods = normalize_phone_vector(cleaned_df["phone"])
    cleaned_df["date_of_birth"], dob_mods = normalize_date_vector(cleaned_df["date_of_birth"])
    cleaned_df["created_date"], created_mods = normalize_date_vector(cleaned_df["created_date"])
    
    # Vectorized capitalization formatting (Title Case)
    name_mask = cleaned_df["first_name"].notna() & (cleaned_df["first_name"].astype(str).str.istitle() == False)
    name_mods = int(name_mask.sum())
    cleaned_df["first_name"] = cleaned_df["first_name"].astype(str).str.strip().str.title()
    cleaned_df["last_name"] = cleaned_df["last_name"].astype(str).str.strip().str.title()

    # --- 2. Imputation Step (Handling Missing Values) ---
    missing_metrics = {
        "first_name": int(cleaned_df["first_name"].isna().sum() + (cleaned_df["first_name"] == "Nan").sum()),
        "last_name": int(cleaned_df["last_name"].isna().sum() + (cleaned_df["last_name"] == "Nan").sum()),
        "address": int(cleaned_df["address"].isna().sum()),
        "income": int(cleaned_df["income"].isna().sum()),
        "account_status": int(cleaned_df["account_status"].isna().sum())
    }

    cleaned_df["first_name"] = cleaned_df["first_name"].replace("Nan", placeholder).fillna(placeholder)
    cleaned_df["last_name"] = cleaned_df["last_name"].replace("Nan", placeholder).fillna(placeholder)
    cleaned_df["address"] = cleaned_df["address"].fillna(placeholder)
    
    # Safe numerical imputation
    cleaned_df["income"] = pd.to_numeric(cleaned_df["income"], errors='coerce').fillna(default_inc)
    cleaned_df["account_status"] = cleaned_df["account_status"].str.strip().fillna(default_stat)

    metrics_log = {
        "phone_mods": phone_mods,
        "date_mods": dob_mods + created_mods,
        "name_mods": name_mods,
        "missing_counts": missing_metrics
    }
    
    return cleaned_df, metrics_log

def compile_cleaning_log(metrics: Dict[str, Any], validation_before: int, validation_after: int, output_rows: int) -> str:
    """Compiles execution metrics into the strict cleaning_log.txt layout standard.

    Args:
        metrics: Captured modification statistics.
        validation_before: Count of rows failing checks before modifications.
        validation_after: Count of rows failing checks after modifications.
        output_rows: Total processed output volume.

    Returns:
        A structural string matching the required audit contract.
    """
    missing = metrics["missing_counts"]
    status_flag = "PASS" if validation_after == 0 else "FAIL"
    
    lines = [
        "DATA CLEANING LOG",
        "=================\n",
        "ACTIONS TAKEN:",
        "--------------",
        "Normalization:",
        f"- Phone format: Converted formats -> XXX-XXX-XXXX ({metrics['phone_mods']} rows affected)",
        f"- Date format: Converted formats -> YYYY-MM-DD ({metrics['date_mods']} rows affected)",
        f"- Name case: Applied title case ({metrics['name_mods']} rows affected)\n",
        "Missing Values:",
        f"- first_name: {missing['first_name']} row missing -> filled with '[UNKNOWN]'",
        f"- last_name: {missing['last_name']} row missing -> filled with '[UNKNOWN]'",
        f"- address: {missing['address']} rows missing -> filled with '[UNKNOWN]'",
        f"- income: {missing['income']} row missing -> filled with 0",
        f"- account_status: {missing['account_status']} row missing -> filled with 'unknown'\n",
        "Validation After Cleaning:",
        f"- Before: {validation_before} rows failed",
        f"- After: {validation_after} rows failed",
        f"- Status: {status_flag}\n",
        f"Output: customers_cleaned.csv ({output_rows} rows, 10 columns)"
    ]
    return "\n".join(lines)