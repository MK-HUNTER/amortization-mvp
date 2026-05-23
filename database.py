import sqlite3
import pandas as pd

DB_NAME = "loan_manager.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        # Detail Table
        conn.execute('''CREATE TABLE IF NOT EXISTS tbl_amortization_detail 
                     (loan_id TEXT PRIMARY KEY, loan_name TEXT, principal REAL, 
                      rate REAL, term_months INTEGER, start_date TEXT, 
                      total_interest REAL, total_paid REAL)''')
        # Calculation Table
        conn.execute('''CREATE TABLE IF NOT EXISTS tbl_amortization_calc
                     (loan_id TEXT, month_index INTEGER, date TEXT, 
                      opening_bal REAL, payment REAL, principal_paid REAL, 
                      interest_paid REAL, closing_bal REAL,
                      FOREIGN KEY(loan_id) REFERENCES tbl_amortization_detail(loan_id))''')

def save_loan(loan_detail, schedule_df):
    with get_connection() as conn:
        loan_detail.to_sql('tbl_amortization_detail', conn, if_exists='append', index=False)
        schedule_df.to_sql('tbl_amortization_calc', conn, if_exists='append', index=False)

def delete_loan_data(loan_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM tbl_amortization_calc WHERE loan_id = ?", (str(loan_id),))
        conn.execute("DELETE FROM tbl_amortization_detail WHERE loan_id = ?", (str(loan_id),))

def get_all_loans():
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM tbl_amortization_detail", conn)

def get_schedule(loan_id):
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM tbl_amortization_calc WHERE loan_id = ?", 
                          conn, params=(str(loan_id),))

def reset_db():
    with get_connection() as conn:
        conn.execute("DROP TABLE IF EXISTS tbl_amortization_calc")
        conn.execute("DROP TABLE IF EXISTS tbl_amortization_detail")
    init_db()