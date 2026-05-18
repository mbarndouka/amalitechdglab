from typing import Dict, Any, Pattern, List
import re
import pandas as pd
from loguru import logger

def compile_security_patterns(config: Dict[str, Any]) -> Dict[str, Pattern[str]]:
    """Compiles string regular expression templates into immutable thread-safe Pattern configurations.

    Args:
        config: A decoupled dictionary matching the infrastructure configuration schema.

    Returns:
        A dictionary containing compiled, high-performance regex pattern matchers.
    """
    regex_section: Dict[str, str] = config.get("regex_patterns", {})
    fallback_email_regex: str = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    return {
        "email": re.compile(regex_section.get("email", fallback_email_regex), re.IGNORECASE)
    }

def scan_pii_metrics(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates data vectors for PII vulnerabilities using high-performance vector masking.

    This operation maintains functional purity; it performs calculations completely 
    isolated from I/O operations and guarantees zero schema side effects on the source frame.

    Args:
        df: An immutable reference to the active pandas DataFrame matrix.
        config: The decoupled master architecture configuration mapping metrics rules.

    Returns:
        A dictionary containing computed metrics, counts, and calculated exposure ratios.
        
    Raises:
        KeyError: If a mandatory column required for structural auditing is missing.
    """
    total_rows: int = len(df)
    if total_rows == 0:
        logger.warning("Empty matrix slice provided to the structural PII scanner.")
        return {
            "total_rows": 0, "emails_found": 0, "email_pct": 0.0,
            "phones_found": 0, "phone_pct": 0.0, "addresses_found": 0,
            "address_pct": 0.0, "dobs_found": 0, "dob_pct": 0.0
        }

    # Defensive validation: Ensure target operational vectors exist in memory
    required_fields: List[str] = ["email", "phone", "address", "date_of_birth"]
    missing_fields: List[str] = [field for field in required_fields if field not in df.columns]
    if missing_fields:
        logger.critical(f"PII Scanning halted. Structural field mismatch: Missing columns {missing_fields}")
        raise KeyError(f"Missing mandatory validation target array structures: {missing_fields}")

    pii_settings: Dict[str, Any] = config.get("pii_settings", {})
    phone_min_digits: int = pii_settings.get("phone_min_digits", 7)
    compiled_regex: Dict[str, Pattern[str]] = compile_security_patterns(config)

    # 1. Vectorized Email Match (Bypassing row loops entirely via Pandas .str accessors)
    email_vector: pd.Series = df["email"].astype(str).str.strip()
    email_mask: pd.Series = email_vector.str.match(compiled_regex["email"].pattern, na=False)
    email_matches: int = int(email_mask.sum())

    # 2. Vectorized Address Match (Evaluating string lengths safely while managing nulls)
    address_vector: pd.Series = df["address"].astype(str).str.strip()
    address_mask: pd.Series = (address_vector.str.len() > 0) & (~df["address"].isna())
    address_matches: int = int(address_mask.sum())

    # 3. Vectorized Phone Match (Extracting formatting characters directly inside C-optimized routines)
    phone_digits_only: pd.Series = df["phone"].astype(str).str.replace(r"\D", "", regex=True)
    phone_mask: pd.Series = (phone_digits_only.str.len() >= phone_min_digits) & (~df["phone"].isna())
    phone_matches: int = int(phone_mask.sum())

    # 4. Vectorized Date of Birth Match (Isolating malformed data strings from real date information)
    dob_vector: pd.Series = df["date_of_birth"].astype(str).str.strip().str.lower()
    dob_mask: pd.Series = (dob_vector.str.len() > 0) & (~dob_vector.str.contains("invalid")) & (~df["date_of_birth"].isna())
    dob_matches: int = int(dob_mask.sum())

    return {
        "total_rows": total_rows,
        "emails_found": email_matches,
        "email_pct": (email_matches / total_rows) * 100.0,
        "phones_found": phone_matches,
        "phone_pct": (phone_matches / total_rows) * 100.0,
        "addresses_found": address_matches,
        "address_pct": (address_matches / total_rows) * 100.0,
        "dobs_found": dob_matches,
        "dob_pct": (dob_matches / total_rows) * 100.0
    }

def compile_pii_report(metrics: Dict[str, Any]) -> str:
    """A pure functional layout compiler that formats analytical counts into an audited logging template.

    Args:
        metrics: Calculated matrix measurements generated upstream.

    Returns:
        A structural string matching the enterprise compliance layout.
    """
    lines: List[str] = [
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