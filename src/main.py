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

def load_config(config_path: str = "config.toml") -> dict:
    if not os.path.exists(config_path):
        logger.warning(f"Config file {config_path} not found. Using defaults.")
        return {}
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def run_pipeline():
    logger.add("logs/pipeline_run.log", rotation="10 MB", level="INFO")
    logger.info("Executing Phase 1 Pure Functional Data Profiler...")
    
    config = load_config()
    paths_config = config.get("paths", {})
    
    raw_path = paths_config.get("raw_data_path", "data/raw/customers_raw.csv")
    output_dir = paths_config.get("output_dir", "reports")
    
    report_target_path = os.path.join(output_dir, "data_quality_report.txt")
    cleaned_out_path: str = config.get("paths", {}).get("cleaned_data_output", "data/processed/customers_cleaned.csv")
    
    try:
        raw_df = load_raw_data(file_path=raw_path)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(cleaned_out_path), exist_ok=True)

        # --- Run Analytics Pipeline Pre-Checks ---
        val_before = execute_validation_pipeline(df=raw_df, config=config)
        rows_failed_before = val_before["failures_count"]

        # --- PHASE 4: Execute Vectorized Data Cleaning ---
        cleaned_df, cleaning_metrics = execute_cleaning_pipeline(df=raw_df, config=config)
        
        # --- Run Analytics Pipeline Post-Checks ---
        val_after = execute_validation_pipeline(df=cleaned_df, config=config)
        rows_failed_after = val_after["failures_count"]

        # Save Cleaned Data Asset
        cleaned_df.to_csv(cleaned_out_path, index=False)
        logger.info(f"Cleaned dataset output written securely to disk: {cleaned_out_path}")

        # Compile and write Phase 4 Logs
        cleaning_log_content = compile_cleaning_log(
            metrics=cleaning_metrics,
            validation_before=rows_failed_before,
            validation_after=rows_failed_after,
            output_rows=len(cleaned_df)
        )
        with open(os.path.join(output_dir, "cleaning_log.txt"), "w", encoding="utf-8") as f:
            f.write(cleaning_log_content)

        # Regenerate standard diagnostic audit steps
        completeness_data = analyze_completeness(raw_df)
        datatype_mappings = analyze_data_types(raw_df)
        structural_voids = scan_anomalies(raw_df, config=config)
        with open(os.path.join(output_dir, "data_quality_report.txt"), "w", encoding="utf-8") as f:
            f.write(generate_report_string(completeness_data, datatype_mappings, structural_voids))

        pii_metrics = scan_pii_metrics(df=raw_df, config=config)
        with open(os.path.join(output_dir, "pii_detection_report.txt"), "w", encoding="utf-8") as f:
            f.write(compile_pii_report(metrics=pii_metrics))

        with open(os.path.join(output_dir, "validation_results.txt"), "w", encoding="utf-8") as f:
            f.write(compile_validation_report(results=val_before, total_rows=len(raw_df)))

        logger.info("Phase 4 clean up routines complete.")
        print("\n[SUCCESS] Phase 4 Clean and Normalize layer finalized successfully!")
        print(f"Cleaned data snapshot generated at: '{cleaned_out_path}'")
        print(f"Log diagnostics written to: '{output_dir}/cleaning_log.txt'\n")
    except Exception as err:
        logger.exception(f"Functional Pipeline processing failed: {str(err)}")
    except Exception as ex:
        logger.exception(f"Unexpected operational crash inside core orchestrator process: {str(ex)}")
        
if __name__ == "__main__":
    run_pipeline()