import os
import sqlite3
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
RAW_DIR = "D:/mutual-fund-analytics/data/raw"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

BENCHMARK_ALIASES = {
    "NIFTY 50 TRI": "NIFTY50",
    "NIFTY 100 TRI": "NIFTY100",
    "NIFTY MIDCAP 150 TRI": "NIFTY_MIDCAP150",
    "NIFTY MIDCAP 50 TRI": "NIFTY_MIDCAP150",
    "BSE 250 SMALLCAP TRI": "BSE_SMALLCAP",
    "NIFTY 500 TRI": "NIFTY500",
    "CRISIL LIQUID FUND AI INDEX": "CRISIL_LIQUID",
    "CRISIL DYNAMIC GILT INDEX": "CRISIL_GILT",
    "CRISIL SHORT TERM BOND INDEX": "CRISIL_GILT",
}


def normalize_benchmark_name(name):
    if pd.isna(name):
        return None

    normalized = str(name).upper().strip()
    for token, benchmark_key in BENCHMARK_ALIASES.items():
        if token in normalized:
            return benchmark_key
    return None

def run_benchmark_correlation_engine():
    print("--- Starting Day 13: Benchmark Index Beta Correlation Engine ---")
    engine = create_engine(DB_URL)
    
    # 1. Fetch historical data streams
    df_nav = pd.read_sql("SELECT amfi_code, nav_date, nav_value FROM fact_nav;", engine)
    df_funds = pd.read_sql("SELECT amfi_code, benchmark FROM dim_fund;", engine)
    df_funds["benchmark_key"] = df_funds["benchmark"].map(normalize_benchmark_name)
    
    benchmark_file = os.path.join(RAW_DIR, "10_benchmark_indices.csv")
    if not os.path.exists(benchmark_file):
        print(f"Error: Missing master index file at {benchmark_file}")
        return
    df_benchmarks = pd.read_csv(benchmark_file)
    
    # Standardize names and formats
    df_nav['nav_date'] = pd.to_datetime(df_nav['nav_date'])
    df_benchmarks['date'] = pd.to_datetime(df_benchmarks['date'])
    df_benchmarks = df_benchmarks.rename(columns={'date': 'nav_date', 'index_name': 'benchmark_key'})
    
    # 2. Compute daily returns for variance profiles
    df_nav = df_nav.sort_values(['amfi_code', 'nav_date'])
    df_nav['fund_daily_return'] = df_nav.groupby('amfi_code')['nav_value'].pct_change()
    
    df_benchmarks = df_benchmarks.sort_values(['benchmark_key', 'nav_date'])
    df_benchmarks['bench_daily_return'] = df_benchmarks.groupby('benchmark_key')['close_value'].pct_change()
    
    # Merge mappings
    df_fund_master = pd.merge(df_nav, df_funds, on='amfi_code')
    df_merged = pd.merge(df_fund_master, df_benchmarks, on=['benchmark_key', 'nav_date']).dropna()
    
    correlation_metrics = []
    
    # 3. Process statistical metrics per fund group
    print("Evaluating covariance weights and alpha tracking scales...")
    for amfi_code, group in df_merged.groupby('amfi_code'):
        if len(group) < 30: # Ensure statistical relevance minimum
            continue
            
        fund_ret = group['fund_daily_return'].values
        bench_ret = group['bench_daily_return'].values
        
        # Calculate statistical Beta: Covariance(Fund, Bench) / Variance(Bench)
        covariance_matrix = np.cov(fund_ret, bench_ret)
        covariance = covariance_matrix[0, 1]
        market_variance = covariance_matrix[1, 1]
        
        beta = covariance / market_variance if market_variance != 0 else 1.0
        
        # Calculate Active Return: Mean Fund Return - Mean Benchmark Return (Annualized proxy)
        active_return_daily = np.mean(fund_ret) - np.mean(bench_ret)
        annualized_active_return = active_return_daily * 252 * 100 # 252 active trading days per year
        
        # Calculate Tracking Error: Standard Deviation of excess returns
        excess_returns = fund_ret - bench_ret
        tracking_error_ann = np.std(excess_returns, ddof=1) * np.sqrt(252) * 100
        
        correlation_metrics.append({
            'amfi_code': amfi_code,
            'computed_statistical_beta': round(float(beta), 4),
            'annualized_active_return_pct': round(float(annualized_active_return), 2),
            'annualized_tracking_error_pct': round(float(tracking_error_ann), 4)
        })
        
    df_metrics = pd.DataFrame(
        correlation_metrics,
        columns=[
            "amfi_code",
            "computed_statistical_beta",
            "annualized_active_return_pct",
            "annualized_tracking_error_pct",
        ],
    )
    
    # Save back to database reporting layer
    df_metrics.to_sql('report_benchmark_correlation_metrics', engine, if_exists='append', index=False)
    print(" Loaded index tracking metrics into table: report_benchmark_correlation_metrics")
    
    # Save audit file
    output_path = os.path.join(PROCESSED_DIR, "benchmark_correlation_audit.csv")
    df_metrics.to_csv(output_path, index=False)
    
    print(f" Saved analytics asset sheet successfully at: {output_path}")
    print("--- Day 13 Correlation Mapping Pipeline Run Complete ---")

if __name__ == "__main__":
    run_benchmark_correlation_engine()
