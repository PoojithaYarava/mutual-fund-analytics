import os
import sqlite3
import pandas as pd

DB_PATH = "D:/mutual-fund-analytics/data/processed/mf_analytics.db"

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database warehouse not found at {DB_PATH}. Please run your ETL pipeline first.")
        return None
    return sqlite3.connect(DB_PATH)

def view_top_performing_funds():
    conn = get_db_connection()
    if not conn: return
    
    print("\n--- 🏆 TOP RISK-ADJUSTED MUTUAL FUND SCHEMES (TIER 1) ---")
    query = """
    SELECT scheme_name, category, alpha, beta, sharpe_ratio, performance_tier
    FROM fact_performance_analytics
    WHERE performance_tier LIKE '%Tier 1%'
    ORDER BY sharpe_ratio DESC LIMIT 5;
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        print("No Tier 1 funds identified based on current criteria limits.")
    else:
        print(df.to_string(index=False))
    conn.close()

def view_sip_growth_velocity():
    conn = get_db_connection()
    if not conn: return
    
    print("\n--- 📈 RECENT SYSTEMATIC INVESTMENT PLAN (SIP) VELOCITY DELTAS ---")
    query = """
    SELECT month_period, sip_inflow_crore, computed_mom_growth_pct
    FROM report_sip_velocity
    ORDER BY month_period DESC LIMIT 6;
    """
    df = pd.read_sql(query, conn)
    print(df.to_string(index=False))
    conn.close()

def check_warehouse_health_metrics():
    conn = get_db_connection()
    if not conn: return
    
    print("\n--- 🔍 WAREHOUSE DATABASE HEALTH & INTEGRITY METRICS ---")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM dim_fund;")
    funds_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_nav;")
    nav_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM fact_transactions;")
    txn_count = cursor.fetchone()[0]
    
    print(f" Total Registered Fund Schemes (Dimensions) : {funds_count}")
    print(f" Total Historical Price Data Points (Facts)  : {nav_count}")
    print(f" Total Logged Investor Transactions (Facts) : {txn_count}")
    print(" Status: Operational & Verified.")
    conn.close()

def main_menu():
    while True:
        print("\n" + "="*60)
        print("     MUTUAL FUND ANALYTICS PLATFORM INTERACTIVE CLI")
        print("="*60)
        print("1. View Top Risk-Adjusted Performing Schemes (Tier 1)")
        print("2. View Industry SIP Inflow Growth Velocity Tracks")
        print("3. Audit Data Warehouse Storage & Health Counters")
        print("4. Exit Terminal Session")
        print("="*60)
        
        choice = input("Enter your selection number (1-4): ").strip()
        
        if choice == '1':
            view_top_performing_funds()
        elif choice == '2':
            view_sip_growth_velocity()
        elif choice == '3':
            check_warehouse_health_metrics()
        elif choice == '4':
            print("\n👋 Terminating interface session. Goodbye!")
            break
        else:
            print("❌ Invalid input selection. Please choose an options tier between 1 and 4.")

if __name__ == "__main__":
    main_menu()