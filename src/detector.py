import re
import pandas as pd

def extract_regex_patterns(config: dict) -> dict:
    """Parses regular expression match schemas from config inputs."""
    patterns = config.get("regex_patterns", {})
    return {
        "email": patterns.get("email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    }

def scan_pii_metrics(df: pd.DataFrame, patterns: dict) -> dict:
    """Senior Vectorized PII Evaluation.

    Executes regex maps across array blocks instantaneously.
    """
    total_rows = len(df)
    if total_rows == 0:
        return {}

    # Vectorized string match check for email compliance
    clean_email_series = df["email"].astype(str).str.strip()
    email_matches = clean_email_series.str.match(patterns["email"], na=False).sum()
    
    # Vectorized character length count validation for address spaces
    address_matches = (df["address"].astype(str).str.strip().str.len() > 0).sum() - df["address"].isna().sum()

    # Vectorized string sequence extraction to verify valid phone configurations
    digit_extract = df["phone"].astype(str).str.replace(r"\D", "", regex=True)
    phone_matches = (digit_extract.str.len() >= 7).sum()

    # Vectorized classification filtering for Birthdate components
    clean_dob_series = df["date_of_birth"].astype(str).str.strip().str.lower()
    dob_matches = ((~clean_dob_series.str.contains("invalid")) & (clean_dob_series.str.len() > 0)).sum() - df["date_of_birth"].isna().sum()

    return {
        "total_rows": total_rows,
        "emails_found": int(email_matches),
        "email_pct": (email_matches / total_rows) * 100,
        "phones_found": int(phone_matches),
        "phone_pct": (phone_matches / total_rows) * 100,
        "addresses_found": int(address_matches),
        "address_pct": (address_matches / total_rows) * 100,
        "dobs_found": int(dob_matches),
        "dob_pct": (dob_matches / total_rows) * 100
    }

def compile_pii_report(metrics: dict) -> str:
    """Assembles security audit statistics into standard text layouts."""
    lines = [
        "PII DETECTION REPORT",
        "======================",
        "\nRISK ASSESSMENT:",
        "- HIGH: Names, emails, phone numbers, addresses, dates of birth",
        "- MEDIUM: Income (financial sensitivity)",
        "\nDETECTED PII:",
        f"- Emails found: {metrics['emails_found']} ({metrics['email_pct']:.0f}%)",
        f"- Phone numbers found: {metrics['phones_found']} ({metrics['phone_pct']:.0f}%)",
        f"- Addresses found: {metrics['addresses_found']} ({metrics['address_pct']:.0f}%)",
        f"- Dates of birth found: {metrics['dobs_found']} ({metrics['dob_pct']:.0f}%)",
        "\nEXPOSURE RISK:",
        "If this dataset were breached, attackers could:",
        "- Phish customers (have emails)",
        "- Spoof identities (have names + DOB + address)",
        "- Social engineer (have phone numbers)",
        "\nMITIGATION: Mask all PII before sharing with analytics teams"
    ]
    return "\n".join(lines)