import os
import sqlite3
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

def run_advanced_analytics_engine():
    print("--- Starting Day 6: Advanced Analytics & Risk Engineering Engine ---")
    engine = create_engine(DB_URL)
    
    # ----------------------------------------------------
    # 1. Historical VaR (95%) & CVaR Calculations
    # ----------------------------------------------------
    print("Calculating Historical VaR (95%) and Conditional VaR (CVaR)...")
    df_nav = pd.read_sql("SELECT amfi_code, nav_date, nav_value FROM fact_nav;", engine)
    if df_nav.empty:
        print("No NAV history found. Skipping VaR/CVaR calculations.")
        return

    df_nav['nav_date'] = pd.to_datetime(df_nav['nav_date'])
    df_nav = df_nav.sort_values(['amfi_code', 'nav_date'])
    df_nav['daily_return'] = df_nav.groupby('amfi_code')['nav_value'].pct_change()
    
    var_metrics = []
    for amfi_code, group in df_nav.dropna().groupby('amfi_code'):
        returns = group['daily_return'].values
        if len(returns) < 30: continue
        
        # 5th percentile for 95% confidence VaR
        var_95 = np.percentile(returns, 5)
        # CVaR is the mean of returns below the VaR threshold
        cvar_95 = returns[returns <= var_95].mean()
        
        var_metrics.append({
            'amfi_code': amfi_code,
            'var_95_pct': round(float(var_95) * 100, 4),
            'cvar_95_pct': round(float(cvar_95) * 100, 4)
        })
    df_var = pd.DataFrame(var_metrics)
    df_var.to_sql('fact_risk_var_cvar', engine, if_exists='append', index=False)

    # ----------------------------------------------------
    # 2. Sector & Portfolio Concentration Risk (HHI)
    # ----------------------------------------------------
    print("Computing Herfindahl-Hirschman Index (HHI) for Portfolio Concentration...")
    # Accessing the portfolio holdings data schema
    try:
        df_holdings = pd.read_sql("SELECT amfi_code, sector, weight_pct FROM fact_portfolio_holdings;", engine)
        if not df_holdings.empty:
            # HHI = Sum of squared weights per fund.
            df_hhi = df_holdings.groupby('amfi_code').apply(
                lambda x: np.sum((x['weight_pct']) ** 2)
            ).reset_index(name='portfolio_hhi_score')
            df_hhi.to_sql('fact_portfolio_hhi', engine, if_exists='append', index=False)
        else:
            print("No holdings rows found, skipping HHI computation block.")
    except Exception:
        print("fact_portfolio_holdings table missing or unreadable, skipping HHI computation block.")

    # ----------------------------------------------------
    # 3. Investor Cohort & Churn Analytics
    # ----------------------------------------------------
    print("Processing Investor Demographics, Cohorts, and Churn Risk (>35 Day Gaps)...")
    df_tx = pd.read_sql("SELECT investor_id, amfi_code, transaction_date, amount_inr, transaction_type FROM fact_transactions;", engine)
    if df_tx.empty:
        print("No transaction data found. Skipping cohort and churn analytics.")
        print("--- Day 6 Complete ---")
        return

    df_tx['transaction_date'] = pd.to_datetime(df_tx['transaction_date'])
    
    # Cohort Analysis: Group by first transaction year
    df_tx['tx_year'] = df_tx['transaction_date'].dt.year
    df_first_tx = df_tx.groupby('investor_id')['tx_year'].min().reset_index(name='cohort_year')
    df_tx = df_tx.merge(df_first_tx, on='investor_id')
    
    df_cohort = df_tx.groupby('cohort_year').agg(
        total_invested=('amount_inr', 'sum'),
        average_ticket_size=('amount_inr', 'mean'),
        unique_investors=('investor_id', 'nunique')
    ).reset_index()

    # Power BI occasionally guesses integer year columns as dates when reading from SQLite.
    # Export a clean flat file with explicit types so the dashboard can import it safely.
    df_cohort['cohort_year'] = pd.to_numeric(df_cohort['cohort_year'], errors='coerce').astype('Int64').astype(str)
    df_cohort['cohort_label'] = 'Cohort ' + df_cohort['cohort_year'].astype(str)
    df_cohort['total_invested'] = pd.to_numeric(df_cohort['total_invested'], errors='coerce').round(2)
    df_cohort['average_ticket_size'] = pd.to_numeric(df_cohort['average_ticket_size'], errors='coerce').round(2)
    df_cohort['unique_investors'] = pd.to_numeric(df_cohort['unique_investors'], errors='coerce').astype('Int64')
    df_cohort.to_sql('report_investor_cohorts', engine, if_exists='append', index=False)
    df_cohort.to_csv(os.path.join(PROCESSED_DIR, 'report_investor_cohorts.csv'), index=False)

    # Churn Risk: SIP Continuation Analysis (gaps > 35 days)
    df_sip = df_tx[df_tx['transaction_type'].str.upper() == 'SIP'].sort_values(['investor_id', 'transaction_date'])
    if not df_sip.empty:
        df_sip['prev_date'] = df_sip.groupby('investor_id')['transaction_date'].shift(1)
        df_sip['days_gap'] = (df_sip['transaction_date'] - df_sip['prev_date']).dt.days

        # Flag investors with structural execution lapses.
        df_churn = df_sip.groupby('investor_id')['days_gap'].max().reset_index()
        df_churn['churn_risk_status'] = np.where(df_churn['days_gap'].fillna(0) > 35, 'At-Risk', 'Active')
        df_churn.to_sql('fact_investor_churn_analysis', engine, if_exists='append', index=False)
        df_churn.to_csv(os.path.join(PROCESSED_DIR, 'fact_investor_churn_analysis.csv'), index=False)
    else:
        print("No SIP rows found, skipping churn analysis.")

    print("Advanced risk metrics and behavioral analytical frames successfully computed.")
    print("--- Day 6 Complete ---")

if __name__ == "__main__":
    run_advanced_analytics_engine()
