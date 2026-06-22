import os
import sys
import subprocess

def execute_pipeline_module(script_relative_path):
    """Executes a pipeline script as an isolated process and manages return code health."""
    base_dir = "D:/mutual-fund-analytics"
    full_script_path = os.path.join(base_dir, script_relative_path)
    script_name = os.path.basename(full_script_path)
    
    print("\n" + "="*60)
    print(f" CORE ORCHESTRATOR: Launching Component System -> {script_name}")
    print("="*60)
    
    if not os.path.exists(full_script_path):
        print(f"❌ Configuration Error: Script not found at target path: {full_script_path}")
        return False
        
    # Trigger script via active virtual environment Python execution token
    process = subprocess.run([sys.executable, full_script_path], capture_output=False, text=True)
    
    if process.returncode != 0:
        print(f"💥 Critical Failure: Execution broke inside component process: {script_name}")
        return False
        
    print(f"✅ Module Completed Successfully: {script_name}")
    return True

def run_master_orchestration():
    print("🚀="*30)
    print("   MUTUAL FUND ANALYTICS PLATFORM - FULL PRODUCTION PIPELINE RUNNER")
    print("🚀="*30)
    
    # Define strict sequential dependency execution chain
    pipeline_execution_chain = [
        "etl/extract.py",              
        "etl/etl_pipeline.py",         
        "etl/eda_and_quality.py",      
        "etl/risk_analytics.py",       
        "etl/aggregations_metrics.py",
        "etl/portfolio_concentration.py",
        "etl/sip_backtester.py",
        "tests/test_warehouse.py" 
    ]
    
    for step_number, script_path in enumerate(pipeline_execution_chain, start=1):
        print(f"\n[STEP {step_number}/{len(pipeline_execution_chain)}] Processing Pipeline Node...")
        success = execute_pipeline_module(script_path)
        
        if not success:
            print("\n🚨 PIPELINE TERMINATED: Sequence broken due to downstream compilation error. Review system logs. 🚨")
            sys.exit(1)
            
    print("\n🎉="*30)
    print("   SUCCESS: COMPLETE MULTI-STAGE ANALYTICS WAREHOUSE DEPLOYED")
    print("🎉="*30)

if __name__ == "__main__":
    run_master_orchestration()