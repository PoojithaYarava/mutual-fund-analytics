import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"
SCHEMA_PATH = "D:/mutual-fund-analytics/sql/schema.sql"
RAW_DIR = "D:/mutual-fund-analytics/data/raw"


def clean_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def clean_text_frame(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].map(clean_text)
    return df


def clean_date_column(df, col_name):
    if col_name in df.columns:
        df[col_name] = pd.to_datetime(df[col_name], errors="coerce")
        df[col_name] = df[col_name].dt.strftime("%Y-%m-%d")
    return df


def clean_numeric_column(df, col_name):
    if col_name in df.columns:
        df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
    return df


def init_database():
    print("--- Initializing Star Schema Database Framework ---")
    db_path = "D:/mutual-fund-analytics/data/processed/mf_analytics.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    tables_to_drop = [
        "fact_investor_churn_analysis",
        "report_investor_cohorts",
        "fact_portfolio_hhi",
        "fact_risk_var_cvar",
        "fact_performance_analytics",
        "report_benchmark_correlation_metrics",
        "report_sip_backtest_simulation",
        "report_sip_velocity",
        "report_investor_ledger",
        "report_nav_trends",
        "fact_portfolio_concentration",
        "bridge_benchmark",
        "fact_portfolio_holdings",
        "fact_industry_folios",
        "fact_category_inflows",
        "fact_sip",
        "fact_aum",
        "fact_transactions",
        "fact_nav",
        "dim_investor",
        "dim_fund",
    ]
    for table in tables_to_drop:
        conn.execute(f"DROP TABLE IF EXISTS {table};")
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.close()
    print("Relational schema layout and fast indices verified successfully.")


def write_table(engine, table_name, df):
    df.to_sql(table_name, engine, if_exists="append", index=False)
    print(f" Loaded {len(df)} records into {table_name}")


def run_production_etl():
    print("\n--- Initializing Comprehensive Production ETL Pipeline ---")
    engine = create_engine(DB_URL)

    # 1. fund master -> dim_fund
    fund_file = os.path.join(RAW_DIR, "01_fund_master.csv")
    if os.path.exists(fund_file):
        df = pd.read_csv(fund_file, low_memory=False)
        df = clean_text_frame(
            df,
            [
                "amfi_code",
                "fund_house",
                "scheme_name",
                "category",
                "sub_category",
                "plan",
                "benchmark",
                "fund_manager",
                "risk_category",
                "sebi_category_code",
            ],
        )
        df = clean_date_column(df, "launch_date")
        for col in [
            "expense_ratio_pct",
            "exit_load_pct",
            "min_sip_amount",
            "min_lumpsum_amount",
        ]:
            df = clean_numeric_column(df, col)
        df = df.drop_duplicates(subset=["amfi_code"]).reset_index(drop=True)
        write_table(engine, "dim_fund", df)

    # 2. investor transactions -> dim_investor + fact_transactions
    txn_file = os.path.join(RAW_DIR, "08_investor_transactions.csv")
    if os.path.exists(txn_file):
        df_all_txns = pd.read_csv(txn_file, low_memory=False)
        df_all_txns = clean_text_frame(
            df_all_txns,
            [
                "investor_id",
                "amfi_code",
                "transaction_type",
                "state",
                "city",
                "city_tier",
                "age_group",
                "gender",
                "payment_mode",
                "kyc_status",
            ],
        )
        df_all_txns = clean_date_column(df_all_txns, "transaction_date")
        df_all_txns = clean_numeric_column(df_all_txns, "amount_inr")
        df_all_txns = clean_numeric_column(df_all_txns, "annual_income_lakh")
        df_all_txns["transaction_type"] = df_all_txns["transaction_type"].str.upper()
        df_all_txns["payment_mode"] = df_all_txns["payment_mode"].str.title()
        df_all_txns["kyc_status"] = df_all_txns["kyc_status"].str.title()
        df_all_txns = df_all_txns.dropna(subset=["investor_id", "amfi_code", "transaction_date", "amount_inr"])
        df_all_txns = df_all_txns[df_all_txns["amount_inr"] > 0]
        df_all_txns = df_all_txns.drop_duplicates().reset_index(drop=True)

        investor_cols = [
            "investor_id",
            "age_group",
            "gender",
            "annual_income_lakh",
            "state",
            "city",
            "city_tier",
            "kyc_status",
        ]
        df_investors = (
            df_all_txns[investor_cols]
            .drop_duplicates(subset=["investor_id"])
            .sort_values("investor_id")
            .reset_index(drop=True)
        )
        write_table(engine, "dim_investor", df_investors)

        fact_txn_cols = [
            "investor_id",
            "transaction_date",
            "amfi_code",
            "transaction_type",
            "amount_inr",
            "payment_mode",
        ]
        df_txns = df_all_txns[fact_txn_cols].copy()
        df_txns["amount_inr"] = df_txns["amount_inr"].round(2)
        write_table(engine, "fact_transactions", df_txns)

    # 3. NAV history -> fact_nav
    nav_file = os.path.join(RAW_DIR, "02_nav_history.csv")
    if os.path.exists(nav_file):
        df = pd.read_csv(nav_file, low_memory=False)
        df = clean_text_frame(df, ["amfi_code"])
        df = clean_date_column(df, "date")
        df = clean_numeric_column(df, "nav")
        df = df.rename(columns={"date": "nav_date", "nav": "nav_value"})
        df = df.dropna(subset=["amfi_code", "nav_date", "nav_value"])
        df = df[df["nav_value"] > 0]
        df = df.drop_duplicates(subset=["amfi_code", "nav_date"]).sort_values(["amfi_code", "nav_date"])
        df["nav_imputed"] = 0
        write_table(engine, "fact_nav", df)

    # 4. AUM history -> fact_aum
    aum_file = os.path.join(RAW_DIR, "03_aum_by_fund_house.csv")
    if os.path.exists(aum_file):
        df = pd.read_csv(aum_file, low_memory=False)
        df = clean_text_frame(df, ["fund_house"])
        df = df.rename(columns={"date": "as_of_date"})
        df = clean_date_column(df, "as_of_date")
        for col in ["aum_lakh_crore", "aum_crore", "num_schemes"]:
            df = clean_numeric_column(df, col)
        df = df.dropna(subset=["as_of_date", "fund_house"]).drop_duplicates()
        write_table(engine, "fact_aum", df)

    # 5. SIP inflows -> fact_sip
    sip_file = os.path.join(RAW_DIR, "04_monthly_sip_inflows.csv")
    if os.path.exists(sip_file):
        df = pd.read_csv(sip_file, low_memory=False)
        df = df.rename(columns={"month": "month_period"})
        df = clean_text_frame(df, ["month_period"])
        for col in [
            "sip_inflow_crore",
            "active_sip_accounts_crore",
            "new_sip_accounts_lakh",
            "sip_aum_lakh_crore",
            "yoy_growth_pct",
        ]:
            df = clean_numeric_column(df, col)
        df["yoy_growth_pct"] = df["yoy_growth_pct"].round(2)
        df = df.dropna(subset=["month_period"]).drop_duplicates(subset=["month_period"]).sort_values("month_period")
        write_table(engine, "fact_sip", df)

    # 6. Category inflows -> fact_category_inflows
    cat_file = os.path.join(RAW_DIR, "05_category_inflows.csv")
    if os.path.exists(cat_file):
        df = pd.read_csv(cat_file, low_memory=False).rename(columns={"month": "month_period"})
        df = clean_text_frame(df, ["month_period", "category"])
        df = clean_numeric_column(df, "net_inflow_crore")
        df = df.dropna(subset=["month_period", "category"]).drop_duplicates()
        write_table(engine, "fact_category_inflows", df)

    # 7. Industry folios -> fact_industry_folios
    folio_file = os.path.join(RAW_DIR, "06_industry_folio_count.csv")
    if os.path.exists(folio_file):
        df = pd.read_csv(folio_file, low_memory=False).rename(columns={"month": "month_period"})
        df = clean_text_frame(df, ["month_period"])
        for col in [
            "total_folios_crore",
            "equity_folios_crore",
            "debt_folios_crore",
            "hybrid_folios_crore",
            "others_folios_crore",
        ]:
            df = clean_numeric_column(df, col)
        df = df.dropna(subset=["month_period"]).drop_duplicates(subset=["month_period"]).sort_values("month_period")
        write_table(engine, "fact_industry_folios", df)

    # 8. Portfolio holdings -> fact_portfolio_holdings
    port_file = os.path.join(RAW_DIR, "09_portfolio_holdings.csv")
    if os.path.exists(port_file):
        df = pd.read_csv(port_file, low_memory=False)
        df = clean_text_frame(df, ["amfi_code", "stock_symbol", "stock_name", "sector"])
        df = clean_date_column(df, "portfolio_date")
        for col in ["weight_pct", "market_value_cr", "current_price_inr"]:
            df = clean_numeric_column(df, col)
        df = df.dropna(subset=["amfi_code", "sector", "weight_pct"]).drop_duplicates()
        df = df[df["weight_pct"] >= 0]
        write_table(engine, "fact_portfolio_holdings", df)

    # 9. Benchmark indices -> bridge_benchmark
    bench_file = os.path.join(RAW_DIR, "10_benchmark_indices.csv")
    if os.path.exists(bench_file):
        df = pd.read_csv(bench_file, low_memory=False)
        df = clean_text_frame(df, ["index_name"])
        df = clean_date_column(df, "date")
        df = clean_numeric_column(df, "close_value")
        df = df.rename(columns={"date": "trade_date"})
        df = df.dropna(subset=["trade_date", "index_name", "close_value"])
        df = df.drop_duplicates(subset=["index_name", "trade_date"]).sort_values(["index_name", "trade_date"])
        write_table(engine, "bridge_benchmark", df)

    print("\n--- Success: Full Relational Star Schema Database Pipeline Run Complete ---")


if __name__ == "__main__":
    init_database()
    run_production_etl()
