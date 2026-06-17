import os
import unittest
import sqlite3
import pandas as pd

class TestMutualFundWarehouse(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Establish a read-only database connection for testing."""
        cls.db_path = "D:/mutual-fund-analytics/data/processed/mf_analytics.db"
        if not os.path.exists(cls.db_path):
            raise FileNotFoundError(f"Database file missing for validation: {cls.db_path}")
        cls.conn = sqlite3.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Safely close database connections after running test assertions."""
        cls.conn.close()

    def test_table_existence(self):
        """INVARIANT CHECK: Verify all critical dimensions and facts exist in the schema."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'dim_fund', 'dim_investor', 'fact_nav', 'fact_transactions', 
            'fact_performance_analytics', 'report_nav_trends', 'report_sip_velocity'
        ]
        for table in expected_tables:
            with self.subTest(table=table):
                self.assertIn(table, tables, f"💥 Data Warehouse Error: Missing required table '{table}'")

    def test_fund_primary_key_uniqueness(self):
        """INVARIANT CHECK: Ensure amfi_code remains unique inside the primary master dimension."""
        df = pd.read_sql("SELECT amfi_code FROM dim_fund", self.conn)
        total_rows = len(df)
        unique_rows = df['amfi_code'].nunique()
        self.assertEqual(total_rows, unique_rows, "💥 Integrity Error: Duplicate amfi_code values found in dim_fund!")

    def test_referential_integrity_transactions(self):
        """INVARIANT CHECK: Verify foreign key alignments (No orphaned transaction records)."""
        # Ensure every fund referenced in transactions actually exists inside the fund master dimension
        query = """
        SELECT t.amfi_code 
        FROM fact_transactions t
        LEFT JOIN dim_fund f ON t.amfi_code = f.amfi_code
        WHERE f.amfi_code IS NULL;
        """
        orphaned_records = pd.read_sql(query, self.conn)
        self.assertEqual(len(orphaned_records), 0, f"💥 Referential Integrity Broken: Found {len(orphaned_records)} orphaned transaction entries.")

    def test_financial_domain_boundaries(self):
        """INVARIANT CHECK: Ensure critical numerical ranges conform to business boundary equations."""
        # 1. Assert that historical NAV values always satisfy the mathematical condition: nav_value > 0
        df_nav = pd.read_sql("SELECT nav_value FROM fact_nav WHERE nav_value <= 0", self.conn)
        self.assertEqual(len(df_nav), 0, "💥 Value Outlier: Found historical asset lines where nav_value <= 0")
        
        # 2. Assert that physical transaction allocations always satisfy: amount_inr > 0
        df_txn = pd.read_sql("SELECT amount_inr FROM fact_transactions WHERE amount_inr <= 0", self.conn)
        self.assertEqual(len(df_txn), 0, "💥 Value Outlier: Found transaction entries where amount_inr <= 0")

if __name__ == '__main__':
    print("\n" + "="*60)
    print(" LAUNCHING PRODUCTION RECOGNITION & DATA WAREHOUSE TESTING SUITE")
    print("="*60 + "\n")
    unittest.main()
