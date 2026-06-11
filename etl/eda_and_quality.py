import os
import pandas as pd
import numpy as np
try:
    # Use non-interactive backend for environments without display (CI, headless servers).
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except Exception as e:
    plt = None
    sns = None
    PLOTTING_AVAILABLE = False
    print(
        "Warning: plotting dependencies are unavailable, so visual generation will be skipped. "
        f"Original error: {e}"
    )
try:
    from sqlalchemy import create_engine
except ImportError:
    create_engine = None

# Setup paths
DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
DB_PATH = DB_URL.replace("sqlite:///", "")
FIG_DIR = "D:/mutual-fund-analytics/docs/eda_figures"
PROCESSED_DIR = "D:/mutual-fund-analytics/data/processed"

os.makedirs(FIG_DIR, exist_ok=True)
if create_engine is not None:
    engine = create_engine(DB_URL)
else:
    import sqlite3
    engine = sqlite3.connect(DB_PATH)

def run_data_quality_checks():
    print("--- Starting Data Quality Assessment Engine ---")
    
    # 1. Check NAV table health
    df_nav = pd.read_sql("SELECT * FROM fact_nav", engine)
    total_nav_rows = len(df_nav)
    missing_navs = df_nav['nav_value'].isnull().sum()
    invalid_navs = (df_nav['nav_value'] <= 0).sum()
    
    # 2. Check Transactions table health
    df_txn = pd.read_sql("SELECT * FROM fact_transactions", engine)
    total_txns = len(df_txn)
    invalid_amounts = (df_txn['amount_inr'] <= 0).sum()
    
    # Compile a Data Quality Report DataFrame
    dq_summary = pd.DataFrame([
        {"Metric": "Total NAV Records Analyzed", "Value": total_nav_rows, "Status": "Pass"},
        {"Metric": "Missing/Null NAV values", "Value": missing_navs, "Status": "Pass" if missing_navs == 0 else "Fail"},
        {"Metric": "Anomalous NAV values (<= 0)", "Value": invalid_navs, "Status": "Pass" if invalid_navs == 0 else "Flag Outliers"},
        {"Metric": "Total Transaction Log Ledger Count", "Value": total_txns, "Status": "Pass"},
        {"Metric": "Anomalous Transaction Amounts (<= 0)", "Value": invalid_amounts, "Status": "Pass" if invalid_amounts == 0 else "Flag Outliers"}
    ])
    
    dq_report_path = os.path.join(PROCESSED_DIR, "data_quality_report.csv")
    dq_summary.to_csv(dq_report_path, index=False)
    print(f" Data Quality Audit logged successfully at: {dq_report_path}")

def generate_analytical_visuals():
    print("\n--- Constructing Trend Visualizations ---")
    if not PLOTTING_AVAILABLE:
        print(" Skipping visual generation because matplotlib/seaborn is not installed.")
        return

    sns.set_theme(style="whitegrid")
    
    # Plot 1: Monthly SIP Inflow Milestone & Account Base Growth
    df_sip = pd.read_sql("SELECT * FROM fact_sip", engine)
    if not df_sip.empty:
        fig, ax1 = plt.subplots(figsize=(10, 5))
        
        # Inflows line plot
        color = '#005b96'
        ax1.set_xlabel('Month / Period')
        ax1.set_ylabel('SIP Inflow (in Crore ₹)', color=color)
        sns.lineplot(data=df_sip, x='month_period', y='sip_inflow_crore', marker='o', color=color, ax=ax1, linewidth=2.5)
        ax1.tick_params(axis='y', labelcolor=color)
        plt.xticks(rotation=45)
        
        # Overlay twin axis for total active accounts
        ax2 = ax1.twinx()
        color = '#03c03c'
        ax2.set_ylabel('Active SIP Accounts (in Crore)', color=color)
        sns.lineplot(data=df_sip, x='month_period', y='active_sip_accounts_crore', marker='s', color=color, ax=ax2, linewidth=2)
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title('Indian Mutual Fund Industry: Systematic Investment Plan (SIP) Growth Curve')
        fig.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, "sip_growth_milestone.png"), dpi=150)
        plt.close()
        print(" Generated Chart 1: sip_growth_milestone.png")

    # Plot 2: Industry Folio Multiplier Evaluation (13.26 Cr to 26.12 Cr Benchmark check)
    df_folios = pd.read_sql("SELECT * FROM fact_industry_folios", engine)
    if not df_folios.empty:
        plt.figure(figsize=(10, 5))
        # Reshape to long format for clean grouped bar charting via seaborn
        df_long = pd.melt(df_folios, id_vars=['month_period'], 
                          value_vars=['equity_folios_crore', 'debt_folios_crore', 'hybrid_folios_crore'],
                          var_name='Asset_Class', value_name='Folios_Crore')
        
        sns.barplot(data=df_long, x='month_period', y='Folios_Crore', hue='Asset_Class', palette='viridis')
        plt.title('Growth and Distribution of Retail Mutual Fund Folios Across Asset Classes')
        plt.ylabel('Folio Registry Base (Crores)')
        plt.xlabel('Period')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, "folio_distribution_trends.png"), dpi=150)
        plt.close()
        print(" Generated Chart 2: folio_distribution_trends.png")

    # Plot 3: Sector Asset Distribution Exposure Map
    df_holdings = pd.read_sql("""
        SELECT sector, SUM(market_value_cr) as total_value 
        FROM fact_portfolio_holdings 
        GROUP BY sector ORDER BY total_value DESC LIMIT 8
    """, engine)
    
    if not df_holdings.empty:
        plt.figure(figsize=(8, 5))
        sns.barplot(data=df_holdings, x='total_value', y='sector', palette='magma')
        plt.title('Top Concentrated Sector Allocations Across Portfolio Component Holdings')
        plt.xlabel('Total Market Capitalization Value (Crore ₹)')
        plt.ylabel('Economic Sector')
        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, "portfolio_sector_exposure.png"), dpi=150)
        plt.close()
        print(" Generated Chart 3: portfolio_sector_exposure.png")

    print(f" Success: Visual templates saved inside asset folder: {FIG_DIR}")

if __name__ == "__main__":
    run_data_quality_checks()
    generate_analytical_visuals()
