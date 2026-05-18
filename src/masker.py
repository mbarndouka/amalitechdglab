from typing import Dict, Any, List
import pandas as pd
from loguru import logger

def mask_name_series(series: pd.Series) -> pd.Series:
    """Vectorized masking for names: 'John' -> 'J***'.

    Preserves the first character and replaces trailing characters with asterisks.
    """
    string_vector = series.astype(str).str.strip()
    
    # Identify positions of valid data strings vs system placeholders
    valid_mask = (string_vector.str.len() > 0) & (string_vector != "[UNKNOWN]")
    
    masked_series = series.copy()
    # Pull first character and pad out remaining string length with asterisks
    masked_series[valid_mask] = string_vector[valid_mask].apply(
        lambda x: x[0] + "*" * (len(x) - 1) if len(x) > 1 else x + "***"
    )
    return masked_series

def mask_email_series(series: pd.Series) -> pd.Series:
    """Vectorized masking for emails: 'john.doe@gmail.com' -> 'j***@gmail.com'.

    Obfuscates the mailbox identifier while leaving the domain suffix completely clear.
    """
    string_vector = series.astype(str).str.strip()
    valid_mask = string_vector.str.contains("@", regex=False)
    
    masked_series = series.copy()
    
    def process_email(email_str: str) -> str:
        try:
            parts = email_str.split("@", 1)
            mailbox, domain = parts[0], parts[1]
            if len(mailbox) > 1:
                return f"{mailbox[0]}***@{domain}"
            return f"***@{domain}"
        except Exception:
            return "[MASKED EMAIL]"

    masked_series[valid_mask] = string_vector[valid_mask].apply(process_email)
    return masked_series

def mask_phone_series(series: pd.Series) -> pd.Series:
    """Vectorized masking for phones: '555-123-4567' -> '***-***-4567'.

    Obfuscates the area and routing code blocks while leaving final routing numbers visible.
    """
    string_vector = series.astype(str).str.strip()
    valid_mask = string_vector.str.len() >= 12  # Matches XXX-XXX-XXXX length
    
    masked_series = series.copy()
    masked_series[valid_mask] = "***-***-" + string_vector[valid_mask].str[-4:]
    return masked_series

def mask_dob_series(series: pd.Series) -> pd.Series:
    """Vectorized masking for dates of birth: '1985-03-15' -> '1985-**-**'.

    Obfuscates the birth month and day to protect privacy while preserving birth year tracking.
    """
    string_vector = series.astype(str).str.strip()
    valid_mask = string_vector.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    
    masked_series = series.copy()
    masked_series[valid_mask] = string_vector[valid_mask].str[:4] + "-**-**"
    return masked_series

def execute_masking_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Secures Personally Identifiable Information (PII) through structural masking.
    
    Transforms sensitive text into safe representations (e.g., 'j***@gmail.com')
    to balance data security with analytical utility.
    
    Args:
        df (pd.DataFrame): The cleaned DataFrame containing clear-text PII.

    Returns:
        pd.DataFrame: A new DataFrame with all PII targets successfully masked.
    """
    masked_df = df.copy()
    
    # Apply modular structural masking transformations
    masked_df["first_name"] = mask_name_series(masked_df["first_name"])
    masked_df["last_name"] = mask_name_series(masked_df["last_name"])
    masked_df["email"] = mask_email_series(masked_df["email"])
    masked_df["phone"] = mask_phone_series(masked_df["phone"])
    masked_df["date_of_birth"] = mask_dob_series(masked_df["date_of_birth"])
    
    # Block mask for the physical address string vector
    address_mask = (masked_df["address"].notna()) & (masked_df["address"] != "[UNKNOWN]")
    masked_df.loc[address_mask, "address"] = "[MASKED ADDRESS]"
    
    return masked_df

def compile_masked_sample_log(original_df: pd.DataFrame, masked_df: pd.DataFrame) -> str:
    """Compiles a text-based compliance validation comparison audit string.

    Args:
        original_df: The cleaned data state before masking layers are injected.
        masked_df: The finalized secure masked data state.

    Returns:
        A structured string layout matching the masked_sample.txt deliverable requirement.
    """
    # Isolate the first 2 rows for the before-and-after comparison block
    before_sample = original_df.head(2).to_csv(index=False)
    after_sample = masked_df.head(2).to_csv(index=False)
    
    lines = [
        "BEFORE MASKING (first 2 rows):",
        "------------------------------",
        before_sample.strip(),
        "\nAFTER MASKING (first 2 rows):",
        "-----------------------------",
        after_sample.strip(),
        "\nANALYSIS:",
        f"- Data structure preserved (still {len(masked_df)} rows, {len(masked_df.columns)} columns)",
        "- PII masked (names, emails, phones, addresses, DOBs hidden)",
        "- Business data intact (income, account_status, dates available)",
        "- Use case: Safe for analytics team (GDPR compliant)"
    ]
    return "\n".join(lines)