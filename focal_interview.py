from sqlalchemy import create_engine
import pandas as pd

# Connection -- already set up ✅
engine = create_engine("mysql+pymysql://root@127.0.0.1/interview_db")

def run_query(sql):
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)

# -----------------------------------------------
# MYSQL
# -----------------------------------------------

sql = """

"""

df = run_query(sql)
print(df)