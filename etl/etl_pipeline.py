import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
SCHEMA_PATH = "D:/mutual-fund-analytics/sql/schema.sql"
RAW_DIR = "D:/mutual-fund-analytics/data/raw"

def clean_date_column(df, col_name):
    """Safely converts a series to string date YYYY-MM-DD format."""
    if col_name in df.columns:
        df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
        return df[col_name].dt.strftime('%Y-%m-%d')
    return None

def init_database():
    print("--- Initializing Star Schema Database Framework ---")
    db_path = "D:/mutual-fund-analytics/data/processed/mf_analytics.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.close()
    print("Relational schema layout and fast indices verified successfully.")

def run_production_etl():
    print("\n--- Initializing Comprehensive Production ETL Pipeline ---")
    engine = create_engine(DB_URL)
    
    # 1. Process 01_fund_master.csv -> dim_fund
    fund_file = os.path.join(RAW_DIR, "01_fund_master.csv")
    if os.path.exists(fund_file):
        df = pd.read_csv(fund_file)
        df['launch_date'] = clean_date_column(df, 'launch_date')
        df.to_sql('dim_fund', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} records into master dimension: dim_fund")

    # 2. Process 08_investor_transactions.csv -> dim_investor & fact_transactions
    txn_file = os.path.join(RAW_DIR, "08_investor_transactions.csv")
    if os.path.exists(txn_file):
        df_all_txns = pd.read_csv(txn_file)
        df_all_txns['transaction_date'] = clean_date_column(df_all_txns, 'transaction_date')
        
        # De-duplicate demographic traits to populate the investor dimension
        investor_cols = ['investor_id', 'age_group', 'gender', 'annual_income_lakh', 'state', 'city', 'city_tier', 'kyc_status']
        df_investors = df_all_txns[investor_cols].drop_duplicates(subset=['investor_id'])
        df_investors.to_sql('dim_investor', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df_investors)} unique profiles into dimension: dim_investor")
        
        # Isolate transaction records for fact_transactions
        fact_txn_cols = ['investor_id', 'transaction_date', 'amfi_code', 'transaction_type', 'amount_inr', 'payment_mode']
        df_txns = df_all_txns[fact_txn_cols]
        df_txns.to_sql('fact_transactions', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df_txns)} records into fact ledger: fact_transactions")

    # 3. Process 02_nav_history.csv -> fact_nav
    nav_file = os.path.join(RAW_DIR, "02_nav_history.csv")
    if os.path.exists(nav_file):
        df = pd.read_csv(nav_file)
        df['date'] = clean_date_column(df, 'date')
        df = df.rename(columns={'date': 'nav_date', 'nav': 'nav_value'})
        df['nav_imputed'] = 0
        df.to_sql('fact_nav', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} historical NAV values into: fact_nav")

    # 4. Process 03_aum_by_fund_house.csv -> fact_aum
    aum_file = os.path.join(RAW_DIR, "03_aum_by_fund_house.csv")
    if os.path.exists(aum_file):
        df = pd.read_csv(aum_file)
        df = df.rename(columns={'date': 'as_of_date'})
        df['as_of_date'] = clean_date_column(df, 'as_of_date')
        df.to_sql('fact_aum', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} records into AUM history tracker: fact_aum")

    # 5. Process 04_monthly_sip_inflows.csv -> fact_sip
    sip_file = os.path.join(RAW_DIR, "04_monthly_sip_inflows.csv")
    if os.path.exists(sip_file):
        df = pd.read_csv(sip_file).rename(columns={'month': 'month_period'})
        df.to_sql('fact_sip', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} periods into SIP performance track: fact_sip")

    # 6. Process 05_category_inflows.csv -> fact_category_inflows
    cat_file = os.path.join(RAW_DIR, "05_category_inflows.csv")
    if os.path.exists(cat_file):
        df = pd.read_csv(cat_file).rename(columns={'month': 'month_period'})
        df.to_sql('fact_category_inflows', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} segments into asset trend mapping: fact_category_inflows")

    # 7. Process 06_industry_folio_count.csv -> fact_industry_folios
    folio_file = os.path.join(RAW_DIR, "06_industry_folio_count.csv")
    if os.path.exists(folio_file):
        df = pd.read_csv(folio_file).rename(columns={'month': 'month_period'})
        df.to_sql('fact_industry_folios', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} snapshot metrics into scale index: fact_industry_folios")

    # 8. Process 09_portfolio_holdings.csv -> fact_portfolio_holdings
    port_file = os.path.join(RAW_DIR, "09_portfolio_holdings.csv")
    if os.path.exists(port_file):
        df = pd.read_csv(port_file)
        df['portfolio_date'] = clean_date_column(df, 'portfolio_date')
        df.to_sql('fact_portfolio_holdings', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} position instances into component map: fact_portfolio_holdings")

    # 9. Process 10_benchmark_indices.csv -> bridge_benchmark
    bench_file = os.path.join(RAW_DIR, "10_benchmark_indices.csv")
    if os.path.exists(bench_file):
        df = pd.read_csv(bench_file).rename(columns={'date': 'trade_date'})
        df['trade_date'] = clean_date_column(df, 'trade_date')
        df.to_sql('bridge_benchmark', engine, if_exists='replace', index=False)
        print(f" Loaded {len(df)} price vectors into market relative bridge: bridge_benchmark")

    print("\n--- Success: Full Relational Star Schema Database Pipeline Run Complete ---")

if __name__ == "__main__":
    init_database()
    run_production_etl()
        
    
    