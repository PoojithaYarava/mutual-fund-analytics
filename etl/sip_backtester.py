import os
import sqlite3
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

def run_sip_backtest_simulation():
    print("--- Starting Day 12: Historical NAV Backtesting & SIP Simulation Engine ---")
    engine = create_engine(DB_URL)
    
    # Extract all clean transaction day NAV historical facts
    query = "SELECT amfi_code, nav_date, nav_value FROM fact_nav ORDER BY amfi_code, nav_date;"
    df_nav = pd.read_sql(query, engine)
    
    # Ensure correct datetime formats for timeline segmentation
    df_nav['nav_date'] = pd.to_datetime(df_nav['nav_date'])
    df_nav['year_month'] = df_nav['nav_date'].dt.to_period('M')
    
    # Identify the first available trading day price vector for each month (SIP date)
    sip_triggers = df_nav.sort_values('nav_date').groupby(['amfi_code', 'year_month']).first().reset_index()
    
    sip_amount = 5000.0
    backtest_results = []
    
    # Group and simulate timeline progressions per mutual fund scheme
    for amfi_code, group in sip_triggers.groupby('amfi_code'):
        total_invested = 0.0
        accumulated_units = 0.0
        
        for _, row in group.iterrows():
            current_nav = float(row['nav_value'])
            if current_nav > 0:
                units_bought = sip_amount / current_nav
                accumulated_units += units_bought
                total_invested += sip_amount
        
        # Pull down the latest terminal NAV price point to check final valuation metrics
        latest_nav_row = df_nav[df_nav['amfi_code'] == amfi_code].sort_values('nav_date', ascending=False).iloc[0]
        latest_nav = float(latest_nav_row['nav_value'])
        latest_date = latest_nav_row['nav_date'].strftime('%Y-%m-%d')
        
        current_value = accumulated_units * latest_nav
        absolute_return_pct = ((current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
        
        backtest_results.append({
            'amfi_code': amfi_code,
            'total_invested_inr': total_invested,
            'accumulated_units': round(accumulated_units, 4),
            'final_evaluation_date': latest_date,
            'terminal_value_inr': round(current_value, 2),
            'absolute_sip_return_pct': round(absolute_return_pct, 2)
        })
        
    df_backtest = pd.DataFrame(backtest_results)
    
    # Save the backtest results to the SQLite Database as an analytical report table
    df_backtest.to_sql('report_sip_backtest_simulation', engine, if_exists='replace', index=False)
    print(" Loaded backtested simulation matrices into table: report_sip_backtest_simulation")
    
    # Export flat sheet for management review
    output_path = os.path.join(PROCESSED_DIR, "fund_sip_backtest_summary.csv")
    df_backtest.to_csv(output_path, index=False)
    print(f" Saved simulation ledger summary directly to: {output_path}")
    print("--- Day 12 Backtesting Pipeline Run Complete ---")

if __name__ == "__main__":
    run_sip_backtest_simulation()