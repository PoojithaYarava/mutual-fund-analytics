-- ====================================================================
-- MUTUAL FUND ANALYTICS PLATFORM - FULL STAR SCHEMA
-- ====================================================================

-- 1. DIMENSION: dim_fund
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code TEXT PRIMARY KEY,
    scheme_name TEXT NOT NULL,
    fund_house TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT,
    plan TEXT,
    launch_date DATE,
    benchmark TEXT,
    expense_ratio_pct REAL,
    exit_load_pct REAL,
    min_sip_amount REAL,
    min_lumpsum_amount REAL,
    fund_manager TEXT,
    risk_category TEXT,
    sebi_category_code TEXT
);

-- 2. DIMENSION: dim_investor
-- Extracted from the distinct demographics inside the transaction tracking ledger
CREATE TABLE IF NOT EXISTS dim_investor (
    investor_id INTEGER PRIMARY KEY,
    age_group TEXT,
    gender TEXT,
    annual_income_lakh REAL,
    state TEXT,
    city TEXT,
    city_tier TEXT,
    kyc_status TEXT
);

-- 3. FACT: fact_nav
CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code TEXT NOT NULL,
    nav_date DATE NOT NULL,
    nav_value REAL NOT NULL,
    nav_imputed INTEGER DEFAULT 0,
    UNIQUE(amfi_code, nav_date),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- 4. FACT: fact_aum
CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of_date DATE NOT NULL,
    fund_house TEXT NOT NULL,
    aum_lakh_crore REAL,
    aum_crore REAL,
    num_schemes INTEGER
);

-- 5. FACT: fact_sip
CREATE TABLE IF NOT EXISTS fact_sip (
    sip_id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_period TEXT NOT NULL,
    sip_inflow_crore REAL,
    active_sip_accounts_crore REAL,
    new_sip_accounts_lakh REAL,
    sip_aum_lakh_crore REAL,
    yoy_growth_pct REAL
);

-- 6. FACT: fact_transactions
CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id INTEGER NOT NULL,
    transaction_date DATE NOT NULL,
    amfi_code TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount_inr REAL NOT NULL,
    payment_mode TEXT,
    FOREIGN KEY (investor_id) REFERENCES dim_investor(investor_id),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- 7. FACT: fact_category_inflows
CREATE TABLE IF NOT EXISTS fact_category_inflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_period TEXT NOT NULL,
    category TEXT NOT NULL,
    net_inflow_crore REAL
);

-- 8. FACT: fact_industry_folios
CREATE TABLE IF NOT EXISTS fact_industry_folios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_period TEXT NOT NULL,
    total_folios_crore REAL,
    equity_folios_crore REAL,
    debt_folios_crore REAL,
    hybrid_folios_crore REAL,
    others_folios_crore REAL
);

-- 9. FACT: fact_portfolio_holdings
CREATE TABLE IF NOT EXISTS fact_portfolio_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code TEXT NOT NULL,
    stock_symbol TEXT,
    stock_name TEXT,
    sector TEXT,
    weight_pct REAL,
    market_value_cr REAL,
    current_price_inr REAL,
    portfolio_date DATE,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- 10. LOOKUP / BRIDGE: bridge_benchmark
CREATE TABLE IF NOT EXISTS bridge_benchmark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date DATE NOT NULL,
    index_name TEXT NOT NULL,
    close_value REAL NOT NULL,
    UNIQUE(index_name, trade_date)
);

-- ====================================================================
-- PERFORMANCE TUNING INDEXES
-- ====================================================================
CREATE INDEX IF NOT EXISTS idx_nav_lookup ON fact_nav(amfi_code, nav_date);
CREATE INDEX IF NOT EXISTS idx_benchmark_lookup ON bridge_benchmark(index_name, trade_date);
CREATE INDEX IF NOT EXISTS idx_txn_lookup ON fact_transactions(amfi_code, transaction_date);
CREATE INDEX IF NOT EXISTS idx_portfolio_lookup ON fact_portfolio_holdings(amfi_code, sector);
