import os
import pandas as pd
from sqlalchemy import create_engine

# Setup paths
DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
RAW_DIR = "D:/mutual-fund-analytics/data/raw"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

def run_portfolio_concentration_analytics():
    print("--- Starting Day 10: Portfolio Concentration & Sector Exposure Engine ---")
    engine = create_engine(DB_URL)
    
    # Load underlying portfolio holdings data
    holdings_file = os.path.join(RAW_DIR, "09_portfolio_holdings.csv")
    if not os.path.exists(holdings_file):
        print(f"Error: Source file not found at {holdings_file}")
        return
        
    df_holdings = pd.read_csv(holdings_file)
    print(f"Successfully loaded {len(df_holdings)} individual asset holding lines for evaluation.")
    
    # Sort data for precision tracking
    df_holdings = df_holdings.sort_values(['amfi_code', 'weight_pct'], ascending=[True, False])
    
    # 1. CONCENTRATION METRICS: Calculate Top 5 and Top 10 holding concentrations per fund
    print("Computing Top 5 and Top 10 individual stock concentration benchmarks...")
    
    df_holdings['stock_rank'] = df_holdings.groupby('amfi_code').cumcount() + 1
    
    top5_sum = df_holdings[df_holdings['stock_rank'] <= 5].groupby('amfi_code')['weight_pct'].sum().reset_index(name='top_5_concentration_pct')
    top10_sum = df_holdings[df_holdings['stock_rank'] <= 10].groupby('amfi_code')['weight_pct'].sum().reset_index(name='top_10_concentration_pct')
    
    concentration_metrics = pd.merge(top5_sum, top10_sum, on='amfi_code')
    
    # 2. SECTOR ALLOCATION EXPOSURES: Group weights by sectors per fund to locate risk
    print("Aggregating macro sector exposures per fund category allocation...")
    sector_exposure = df_holdings.groupby(['amfi_code', 'sector'])['weight_pct'].sum().reset_index()
    
    # Pick the primary dominant sector per fund scheme to help identify style tilt
    dominant_sector = sector_exposure.sort_values(['amfi_code', 'weight_pct'], ascending=[True, False]).groupby('amfi_code').first().reset_index()
    dominant_sector = dominant_sector.rename(columns={'sector': 'dominant_sector', 'weight_pct': 'dominant_sector_exposure_pct'})
    
    # Merge concentrations and dominant styles together
    df_portfolio_facts = pd.merge(concentration_metrics, dominant_sector, on='amfi_code')
    
    # 3. Load results into the SQLite Database Warehouse as an Analytical Fact table
    df_portfolio_facts.to_sql('fact_portfolio_concentration', engine, if_exists='replace', index=False)
    print(" Saved processed analytics calculations into table: fact_portfolio_concentration")
    
    # 4. Generate an industry-wide sector density footprint to guide allocation strategy
    sector_density = df_holdings.groupby('sector')['market_value_cr'].sum().reset_index()
    sector_density['allocation_density_pct'] = ((sector_density['market_value_cr'] / sector_density['market_value_cr'].sum()) * 100).round(2)
    sector_density = sector_density.sort_values('allocation_density_pct', ascending=False)
    
    density_path = os.path.join(PROCESSED_DIR, "macro_sector_density_report.csv")
    sector_density.to_csv(density_path, index=False)
    print(f" Executive sector density matrix logged successfully at: {density_path}")
    print("--- Day 10 Portfolio Concentration Pipeline Run Complete ---")

if __name__ == "__main__":
    run_portfolio_concentration_analytics()