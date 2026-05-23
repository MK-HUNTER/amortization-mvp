import sqlite3
import pandas as pd

DB_NAME = "loans.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Metadata Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loan_metadata (
                loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_name TEXT,
                principal REAL,
                annual_rate REAL,
                tenure_years INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Schedules Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS amortization_schedules (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER,
                period INTEGER,
                opening_balance REAL,
                payment REAL,
                interest_paid REAL,
                principal_paid REAL,
                closing_balance REAL,
                FOREIGN KEY (loan_id) REFERENCES loan_metadata (loan_id)
            )
        ''')
        conn.commit()

def save_loan_to_db(name, p, r, n, df):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO loan_metadata (loan_name, principal, annual_rate, tenure_years) VALUES (?, ?, ?, ?)",
            (name, p, r, n)
        )
        loan_id = cursor.lastrowid
        df['loan_id'] = loan_id
        # Map DataFrame columns to SQL table names
        df.rename(columns={
            "Opening Balance": "opening_balance",
            "Total Payment": "payment",
            "Interest Component": "interest_paid",
            "Principal Component": "principal_paid",
            "Closing Balance": "closing_balance",
            "Period": "period"
        }).to_sql('amortization_schedules', conn, if_exists='append', index=False)