import os
import pandas as pd
from sqlalchemy import create_engine

# Setup paths
DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
RAW_DIR = "D:/mutual-fund-analytics/data/raw"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

def run_performance_analytics():
    print("--- Starting Day 4: Risk & Performance Analytics Engine ---")
    engine = create_engine(DB_URL)
    
    # Load performance dataset
    perf_file = os.path.join(RAW_DIR, "07_scheme_performance.csv")
    if not os.path.exists(perf_file):
        print(f"Error: Source file not found at {perf_file}")
        return
        
    df = pd.read_csv(perf_file)
    print(f"Successfully loaded {len(df)} mutual fund performance tracks for evaluation.")
    
    # 1. Advanced Metrics Engineering: Rank schemes within their specific category based on Sharpe Ratio
    df['category_sharpe_rank'] = df.groupby('category')['sharpe_ratio'].rank(ascending=False, method='min')
    
    # 2. Risk-Performance Clustering/Tiering Logic
    # Criteria: Define an 'Outperformer' if Alpha > 1.0 and Sharpe Ratio >= 0.85
    def classify_performance_tier(row):
        if row['alpha'] > 1.0 and row['sharpe_ratio'] >= 0.85:
            return 'Tier 1: High Alpha - Optimal Risk-Adjusted'
        elif row['alpha'] >= 0.0 and row['sharpe_ratio'] >= 0.70:
            return 'Tier 2: Steady Performer - Stable Risk-Adjusted'
        elif row['beta'] > 1.2 and row['std_dev_ann_pct'] > 18:
            return 'Tier 3: Aggressive - High Volatility Segment'
        else:
            return 'Tier 4: Underperformer / Defensive Segment'
            
    df['performance_tier'] = df.apply(classify_performance_tier, axis=1)
    
    # 3. Compute Risk Premium Metric (Excess Return per unit of systematic risk proxy)
    # Simple proxy: Alpha to Beta ratio to evaluate manager selection efficiency
    df['manager_efficiency_index'] = (df['alpha'] / df['beta']).round(4)
    
    # Select columns to load into the analytical table
    analytics_cols = [
        'amfi_code', 'scheme_name', 'category', 'return_3yr_pct', 'benchmark_3yr_pct',
        'alpha', 'beta', 'sharpe_ratio', 'sortino_ratio', 'std_dev_ann_pct', 
        'category_sharpe_rank', 'performance_tier', 'manager_efficiency_index', 'risk_grade'
    ]
    df_analytics_fact = df[analytics_cols]
    
    # 4. Load into the SQLite Database Warehouse as a new Analytical Fact table
    df_analytics_fact.to_sql('fact_performance_analytics', engine, if_exists='append', index=False)
    print(" Saved processed analytics calculations into table: fact_performance_analytics")
    
    # 5. Generate an executive category-level risk summary matrix
    summary_matrix = df.groupby('category').agg(
        avg_alpha=('alpha', 'mean'),
        avg_beta=('beta', 'mean'),
        avg_sharpe=('sharpe_ratio', 'mean'),
        avg_sortino=('sortino_ratio', 'mean'),
        avg_volatility=('std_dev_ann_pct', 'mean'),
        total_schemes=('amfi_code', 'count')
    ).reset_index().round(2)
    
    summary_path = os.path.join(PROCESSED_DIR, "executive_risk_summary.csv")
    summary_matrix.to_csv(summary_path, index=False)
    print(f" Executive category risk matrix logged successfully at: {summary_path}")
    print("--- Day 4 Risk Pipeline Run Complete ---")

if __name__ == "__main__":
    run_performance_analytics()
