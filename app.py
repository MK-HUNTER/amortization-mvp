import streamlit as st
import pandas as pd
from engine import generate_amortization_schedule
from database import init_db, save_loan_to_db

st.set_page_config(page_title="Smart Amortization Hub", layout="wide")
init_db()

st.title("🏦 Smart Amortization Hub")

# --- SIDEBAR: MANUAL INPUTS ---
with st.sidebar:
    st.header("New Loan Scenario")
    name = st.text_input("Loan Label", "New Loan")
    p = st.number_input("Principal ($)", min_value=1000, value=250000, step=5000)
    r = st.number_input("Annual Interest Rate (%)",min_value=0, value=0, step=1) / 100
    n = st.number_input("Tenure (Years)", 1, 50, 30)
    
    if st.button("💾 Save Current to Archive"):
        current_df = generate_amortization_schedule(p, r, n)
        save_loan_to_db(name, p, r, n, current_df)
        st.success(f"Archived {name}!")

# --- MAIN TABBED INTERFACE ---
tab_calc, tab_batch, tab_archive = st.tabs(["🧮 Calculator", "📁 Batch Upload", "📦 Archived Loans"])

with tab_calc:
    st.subheader(f"Schedule for: {name}")
    df = generate_amortization_schedule(p, r, n)
    
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly Payment", f"${df['Total Payment'].iloc[0]:,.2f}")
    c2.metric("Total Interest", f"${df['Interest Component'].sum():,.2f}")
    c3.metric("Total Cost", f"${(p + df['Interest Component'].sum()):,.2f}")
    
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab_batch:
    st.subheader("Excel Batch Ingestion")
    uploaded_file = st.file_uploader("Upload Excel (Headers: Name, Principal, Rate, Years)", type=["xlsx"])
    
    if uploaded_file:
        batch_df = pd.read_excel(uploaded_file)
        st.write("Preview of Upload:")
        st.dataframe(batch_df)
        
        if st.button("🚀 Process & Archive Batch"):
            for _, row in batch_df.iterrows():
                # Process each row through the engine
                s_df = generate_amortization_schedule(row['Principal'], row['Rate']/100, row['Years'])
                save_loan_to_db(row['Name'], row['Principal'], row['Rate']/100, row['Years'], s_df)
            st.success("Batch processed successfully!")

with tab_archive:
    st.subheader("Local database: loans.db")
    import sqlite3
    with sqlite3.connect("loans.db") as conn:
        archive_list = pd.read_sql("SELECT * FROM loan_metadata ORDER BY created_at DESC", conn)
        st.dataframe(archive_list, use_container_width=True)