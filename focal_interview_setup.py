from sqlalchemy import create_engine
import pandas as pd

# Connection
engine = create_engine("mysql+pymysql://root@127.0.0.1/interview_db")

def run_query(sql):
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)

print("✅ Connected successfully!")

# Row counts
print("\n--- Row Counts ---")
for table in ['stores', 'products', 'out_of_stocks', 'action_tasks',
              'product_inventory_levels', 'product_inventory_history',
              'product_sales_records']:
    count = run_query(f"SELECT COUNT(*) AS row_count FROM {table}")
    print(f"{table}: {count['row_count'][0]} rows")