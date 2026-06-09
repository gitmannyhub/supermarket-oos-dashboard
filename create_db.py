import sqlite3
import pymysql
import pandas as pd

# MySQL Connection
mysql_conn = pymysql.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    database="interview_db"
)

# SQLite Connection
sqlite_conn = sqlite3.connect("supermarket_oos.db")

# Tables to Export
tables = [
    "stores",
    "products",
    "out_of_stocks",
    "action_tasks",
    "product_inventory_levels",
    "product_inventory_history",
    "product_sales_records"
]

print("Exporting MySQL tables to SQLite...")

for table in tables:
    print(f"  Exporting {table}...")
    df = pd.read_sql(f"SELECT * FROM {table}", mysql_conn)
    df.to_sql(table, sqlite_conn, if_exists="replace", index=False)
    print(f"  ✅ {table} -- {len(df)} rows exported")

sqlite_conn.commit()
sqlite_conn.close()
mysql_conn.close()

print("\n✅ Done! supermarket_oos.db created successfully.")