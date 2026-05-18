import os 
from loguru import logger
from profiler import (
    load_raw_data,
    analyze_completeness, 
    analyze_data_types,
    scan_anomalies,
    generate_report_string)

def run_pipeline():
    logger.add("logs/pipeline_run.log", rotation="10 MB", level="INFO")
    logger.info("Executing Phase 1 Pure Functional Data Profiler...")
    raw_path = "data/raw/customers_raw.csv"
    output_dir = "reports"
    
    report_target_path = os.path.join(output_dir, "data_quality_report.txt")
    
    try:
        raw_dataframe = load_raw_data(file_path=raw_path)
        
        completeness_metrics = analyze_completeness(raw_dataframe)
        datatype_mappings    = analyze_data_types(raw_dataframe)
        structural_anomalies = scan_anomalies(raw_dataframe)
        
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

        print(f"\n[SUCCESS] Phase 1 functional step complete. Audit report safe at: {report_target_path}\n")
    except Exception as err:
        logger.exception(f"Functional Pipeline processing failed: {str(err)}")
        
if __name__ == "__main__":
    run_pipeline()