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
    
    try:
        raw_dataframe = load_raw_data(file_path=raw_path)
        
        completeness_metrics = analyze_completeness(raw_dataframe)
        datatype_mappings    = analyze_data_types(raw_dataframe)
        structural_anomalies = scan_anomalies(raw_dataframe, config=config)
        
        # Combine parameters into text template layout
        final_report_content = generate_report_string(
            completeness=completeness_metrics,
            data_types=datatype_mappings,
            anomalies=structural_anomalies
        )
        
        # File I/O Side Effect isolated cleanly at finalization stage
        os.makedirs(output_dir, exist_ok=True)
        with open(report_target_path, "w", encoding="utf-8") as file:
            file.write(final_report_content)

# --- PHASE 2: Production-Grade Vectorized PII Scanning ---
        pii_metrics: Dict[str, Any] = scan_pii_metrics(df=raw_dataframe, config=config)
        pii_report: str = compile_pii_report(metrics=pii_metrics)
        with open(os.path.join(output_dir, "pii_detection_report.txt"), "w", encoding="utf-8") as f:
            f.write(pii_report)

        # 4. Phase 3: Vectorized Data Contract Validation
        validation_results: Dict[str, Any] = execute_validation_pipeline(df=raw_dataframe, config=config)
        v_report: str = compile_validation_report(results=validation_results, total_rows=len(raw_dataframe))
        with open(os.path.join(output_dir, "validation_results.txt"), "w", encoding="utf-8") as f:
            f.write(v_report)

        logger.info("Phases 1, 2, and 3 executed successfully.")
        print("\n[SUCCESS] Phase 3 Data Contract Validation layer complete!")
        print(f"Check output_reports/validation_results.txt to see the data issues captured at runtime.\n") 
    except Exception as err:
        logger.exception(f"Functional Pipeline processing failed: {str(err)}")
    except Exception as ex:
        logger.exception(f"Unexpected operational crash inside core orchestrator process: {str(ex)}")
        
if __name__ == "__main__":
    run_pipeline()