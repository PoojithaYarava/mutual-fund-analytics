import pandas as pd
from sqlalchemy import create_engine

DB_URL = "sqlite:///D:/mutual-fund-analytics/data/processed/mf_analytics.db"

def recommend_funds(risk_appetite: str):
    """
    Inputs: Low, Moderate, High, Very High
    Outputs: Top 3 matching fund recommendations by Sharpe Ratio
    """
    engine = create_engine(DB_URL)
    
    query = """
        SELECT f.amfi_code, f.scheme_name, f.category, f.risk_category, p.sharpe_ratio
        FROM dim_fund f
        LEFT JOIN fact_performance p ON f.amfi_code = p.amfi_code
        WHERE LOWER(f.risk_category) = LOWER(?)
        ORDER BY p.sharpe_ratio DESC
        LIMIT 3;
    """
    
    df = pd.read_sql_query(query, engine, params=(risk_appetite,))
    return df

if __name__ == "__main__":
    print("\n--- Bluestock Rule-Based Fund Recommendation Test ---")
    for level in ['Low', 'Moderate', 'High', 'Very High']:
        print(f"\nTarget Risk Appetite Profile: {level}")
        suggestions = recommend_funds(level)
        if suggestions.empty:
            print(" No records matched this specific constraint metric inside the mock frame.")
        else:
            print(suggestions[['scheme_name', 'category', 'sharpe_ratio']].to_string(index=False))