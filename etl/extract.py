import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_DIR = "D:/mutual-fund-analytics/data/raw"
PROCESSED_DATA_DIR = "D:/mutual-fund-analytics/data/processed"
API_CACHE_DIR = os.path.join(RAW_DATA_DIR, "api")

os.makedirs(API_CACHE_DIR, exist_ok=True)

def get_nav_history(scheme_code):
    """
    Fetches historical daily NAV for a specific mutual fund scheme code from mfapi.in
    Caches results locally under data/raw/api/ to ensure repeatability.
    """
    cache_path = os.path.join(API_CACHE_DIR, f"{scheme_code}.csv")
    
    # If already cached locally, read from disk
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)
    
    # Otherwise, request from api.mfapi.in
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            nav_data = data.get("data", [])
            
            if not nav_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(nav_data)
            df["scheme_code"] = scheme_code
            
            #Standardize columns
            df = df.rename(columns={"nav": "nav_values"})
            
            #save to cache
            df.to_csv(cache_path, index=False)
            print(f" Successfully fetched and cached scheme: {scheme_code}")
            return df
        else:
            print(f" Warning: Failed to fetch scheme {scheme_code}. Status: {response.status_code}")
            return pd.DataFrame()
   
    except Exception as e:
        print(f" Error connecting to API for scheme {scheme_code}: {e}")
        return pd.DataFrame()
def run_extraction():
    print("--- Starting Day 1 Data Ingestion Pipeline ---")
    
    #Look at the 10 CSVs inside raw directory
    all_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith('.csv')]
    print(f"Found {len(all_files)} raw CSV data files in landing zone.")
    
    #create an ingestion metadata profile log
    profile_records = []
    
    for file in all_files:
        file_path = os.path.join(RAW_DATA_DIR, file)
        try:
            df = pd.read_csv(file_path, low_memory=False)
            profile_records.append({
                "file_name": file,
                "rows": len(df),
                "columns": len(df.columns),
                "timestamp": datetime.now().strftime("%y-%m-%d %H:%M:%S")
            }) 
        except Exception as e:
            print(f"Error reading file {file}: {e}")
    
    # Mocking execution for sample scheme codes (e.g., 40 schemes can be looped here)
    # Let's test with a prominent Indian Mutual Fund scheme code (e.g., 119551 = HDFC Top 100)
    test_schemes = ["119551"] 
    print("Initializing API consumption engine...")
    for scheme in test_schemes:
        get_nav_history(scheme)
        
    # Generate standalone artifact summary profile
    profile_df = pd.DataFrame(profile_records)
    summary_path = os.path.join(PROCESSED_DATA_DIR, "landing_profile.csv")
    profile_df.to_csv(summary_path, index=False)
    print(f" Ingestion profiles compiled and saved to: {summary_path}")
    print("--- Day 1 Pipeline Complete ---")

if __name__ == "__main__":
    run_extraction()       
    
         
        
