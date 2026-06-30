import os
import sqlite3
import pandas as pd

try:
    from sqlalchemy import create_engine
except ImportError:
    create_engine = None

# Setup paths
DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

def run_advanced_aggregations():
    print("--- Starting Day 5: Advanced SQL & Window Functions Aggregations Engine ---")
    if create_engine is not None:
        engine = create_engine(DB_URL)
    else:
        engine = sqlite3.connect(DB_URL.replace("sqlite:///", ""))
    
    # 1. WINDOW FUNCTION 1: 30-Day Rolling Moving Average for historical fund NAVs
    print("Computing rolling price indicators via SQL window partitions...")
    query_nav_moving_avg = """
    SELECT 
        amfi_code,
        nav_date,
        nav_value,
        AVG(nav_value) OVER (
            PARTITION BY amfi_code 
            ORDER BY nav_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) as nav_30day_moving_avg
    FROM fact_nav;
    """
    df_nav_trends = pd.read_sql(query_nav_moving_avg, engine)
    df_nav_trends.to_sql('report_nav_trends', engine, if_exists='append', index=False)
    print(f" Loaded {len(df_nav_trends)} records into trend layer: report_nav_trends")

    # 2. WINDOW FUNCTION 2: Running cumulative transaction allocations per unique investor
    print("Calculating historical investor running total streams...")
    query_investor_cum_sum = """
    WITH ordered_txns AS (
        SELECT
            ROW_NUMBER() OVER (
                PARTITION BY investor_id
                ORDER BY transaction_date, amfi_code, transaction_type, amount_inr
            ) AS txn_seq,
            investor_id,
            transaction_date,
            amfi_code,
            transaction_type,
            amount_inr
        FROM fact_transactions
    )
    SELECT
        txn_seq AS txn_id,
        investor_id,
        transaction_date,
        amfi_code,
        transaction_type,
        amount_inr,
        SUM(CASE WHEN transaction_type = 'Redemption' THEN -amount_inr ELSE amount_inr END) OVER (
            PARTITION BY investor_id
            ORDER BY transaction_date, txn_seq
        ) AS cumulative_net_investment_inr
    FROM ordered_txns;
    """
    df_investor_ledger = pd.read_sql(query_investor_cum_sum, engine)
    df_investor_ledger.to_sql('report_investor_ledger', engine, if_exists='append', index=False)
    print(f" Loaded {len(df_investor_ledger)} lines into ledger layer: report_investor_ledger")

    # 3. WINDOW FUNCTION 3: Month-on-Month Growth Deltas for Systematic Inflows using LAG()
    print("Parsing historic industry growth velocity scales...")
    query_sip_mom_growth = """
    SELECT 
        month_period,
        sip_inflow_crore,
        LAG(sip_inflow_crore, 1) OVER (ORDER BY month_period) as previous_month_inflow_crore,
        ROUND((sip_inflow_crore - LAG(sip_inflow_crore, 1) OVER (ORDER BY month_period)) / 
              LAG(sip_inflow_crore, 1) OVER (ORDER BY month_period) * 100, 2) as computed_mom_growth_pct
    FROM fact_sip;
    """
    df_sip_velocity = pd.read_sql(query_sip_mom_growth, engine)
    df_sip_velocity.to_sql('report_sip_velocity', engine, if_exists='append', index=False)
    print(f" Loaded {len(df_sip_velocity)} intervals into scale layer: report_sip_velocity")

    # 6. Save a local flat snapshot report for business audit reviews
    audit_report_path = os.path.join(PROCESSED_DIR, "industry_sip_velocity_report.csv")
    df_sip_velocity.to_csv(audit_report_path, index=False)
    print(f" Exported flat business metrics audit ledger to: {audit_report_path}")
    print("--- Day 5 Aggregations & Metrics Generation Run Complete ---")

if __name__ == "__main__":
    run_advanced_aggregations()
