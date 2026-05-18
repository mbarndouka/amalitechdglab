import sys
import os 
from typing import Dict, Any, Pattern, List
from loguru import logger
import tomllib
from src.validator import (
    execute_validation_pipeline,
    compile_validation_report
    )
from detector import (
    scan_pii_metrics,
    compile_pii_report
    )
from profiler import (
    load_raw_data,
    analyze_completeness, 
    analyze_data_types,
    scan_anomalies,
    generate_report_string)
from src.cleaner import execute_cleaning_pipeline, compile_cleaning_log
from src.masker import execute_masking_pipeline, compile_masked_sample_log
from src.orchestrator import run_orchestrator

if __name__ == "__main__":
    run_orchestrator()