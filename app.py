import streamlit as st
import pandas as pd
import io
from database import init_db, save_loan, get_all_loans, get_schedule, delete_loan_data, reset_db
from engine import calculate_amortization_schedule

st.set_page_config(page_title="Amortization MVP", layout="wide")
init_db()


tab1, tab2, tab3 = st.tabs(["Data Entry", "Loan Inspector", "Global Overview"])

# --- TAB 1: DATA ENTRY & MAINTENANCE ---
with tab1:
    # Header layout
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.header("Add New Loan")
    
    # Input Layout
    col1, col2 = st.columns(2)
    lid = col1.text_input("Loan ID (Unique)", value="1001")
    lname = col2.text_input("Loan Name", value="Test")
    princ = col1.number_input("Principal ($)", min_value=0.0, value=100000.0, step=1000.0)
    rate = col2.number_input("Annual Interest Rate (%)", min_value=0.0, value=10.0, step=0.1)
    term = col1.number_input("Term (Months)", min_value=1, value=240, step=1)
    sdate = col2.date_input("Start Date").strftime('%Y-%m-%d')

    # --- LIVE VALIDATION ENGINE ---
    existing_loans = get_all_loans()
    is_duplicate = False
    
    # Check for duplicates immediately as they type
    if lid.strip() and not existing_loans.empty:
        if lid.strip() in existing_loans['loan_id'].values.astype(str):
            is_duplicate = True

    # Display warning right below inputs if it's a duplicate
    if is_duplicate:
        st.warning(f"⚠️ Loan ID '{lid}' already exists! Please use a unique ID.")

    # Calculate live preview ONLY if the ID is valid and unique
    preview_df = None
    t_paid, t_int = 0.0, 0.0
    if lid.strip() and princ > 0 and term > 0 and not is_duplicate:
        preview_df, t_paid, t_int = calculate_amortization_schedule(lid, princ, rate, term, sdate)

    # Place Save Button in the top right column action area
    with top_col2:
        st.write("##") # Align vertically with header
        # The button is physically greyed out and unclickable if is_duplicate is True
        save_clicked = st.button(
            "Save Loan", 
            type="primary", 
            use_container_width=True, 
            disabled=is_duplicate or not lid.strip()
        )

    # Process Save Action (Only runs if the button isn't disabled)
    if save_clicked and not is_duplicate:
        detail_data = pd.DataFrame([{
            "loan_id": lid, "loan_name": lname, "principal": princ,
            "rate": rate, "term_months": term, "start_date": sdate,
            "total_interest": t_int, "total_paid": t_paid
        }])
        save_loan(detail_data, preview_df)
        st.success(f"Loan '{lid}' saved successfully!")
        st.rerun()

    # Live Preview Section 
    st.subheader("Live Preview (First 5 Months)")
    if preview_df is not None:
        st.dataframe(preview_df.head(5), use_container_width=True, hide_index=True)
    elif is_duplicate:
        st.info("💡 Live preview hidden because the Loan ID is a duplicate.")
    else:
        st.info("Enter Principal, Rate, and Term parameters above to see a live preview.")

    st.divider()
    
    # Mass Management Section
    st.subheader("Mass Management (Upload & Download)")
    m_col1, m_col2, m_col3 = st.columns([1, 1, 2])
    
    # 1. Mass Download Template
    with m_col1:
        current_records = get_all_loans()
        if current_records.empty:
            template_df = pd.DataFrame(columns=["loan_id", "loan_name", "principal", "rate", "term_months", "start_date"])
        else:
            template_df = current_records[["loan_id", "loan_name", "principal", "rate", "term_months", "start_date"]]
            
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            template_df.to_excel(writer, index=False, sheet_name='Loans')
        
        st.download_button(
            label="📥 Download Template / Data (Excel)",
            data=buffer.getvalue(),
            file_name="loan_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # 2. Reset Database Button
    with m_col2:
        if st.button("🗑️ Reset Database (Clear All)", use_container_width=True):
            reset_db()
            st.warning("Database cleared and initialized to fresh state.")
            st.rerun()

    # 3. Mass Upload Area
    with m_col3:
        uploaded_file = st.file_uploader("Upload Mass Loan Excel File", type=["xlsx"])
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_excel(uploaded_file)
                required_cols = ["loan_id", "loan_name", "principal", "rate", "term_months", "start_date"]
                
                if not all(col in uploaded_df.columns for col in required_cols):
                    st.error(f"Invalid format. File must contain columns: {', '.join(required_cols)}")
                elif uploaded_df['loan_id'].duplicated().any():
                    st.error("Upload failed: Duplicate loan_id values found within the uploaded file.")
                else:
                    reset_db()
                    for _, row in uploaded_df.iterrows():
                        u_id = str(row['loan_id'])
                        u_name = str(row['loan_name'])
                        u_princ = float(row['principal'])
                        u_rate = float(row['rate'])
                        u_term = int(row['term_months'])
                        u_sdate = pd.to_datetime(row['start_date']).strftime('%Y-%m-%d')
                        
                        sched_df, t_paid, t_int = calculate_amortization_schedule(u_id, u_princ, u_rate, u_term, u_sdate)
                        
                        detail_data = pd.DataFrame([{
                            "loan_id": u_id, "loan_name": u_name, "principal": u_princ,
                            "rate": u_rate, "term_months": u_term, "start_date": u_sdate,
                            "total_interest": t_int, "total_paid": t_paid
                        }])
                        save_loan(detail_data, sched_df)
                        
                    st.success("Fresh upload completed successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading file structure: {str(e)}")


# --- TAB 2: LOAN INSPECTOR ---
with tab2:
    loans = get_all_loans()
    if not loans.empty:
        selected_name = st.selectbox("Select Loan", loans['loan_name'].unique())
        selected_id = loans[loans['loan_name'] == selected_name]['loan_id'].values[0]
        loan_info = loans[loans['loan_id'] == selected_id].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Principal", f"${loan_info['principal']:,.2f}")
        c2.metric("Total Interest", f"${loan_info['total_interest']:,.2f}")
        c3.metric("Total Paid", f"${loan_info['total_paid']:,.2f}")
        c4.metric("Rate", f"{loan_info['rate']}%")

        full_sched = get_schedule(selected_id)
        
        st.subheader("Payment Composition")
        st.bar_chart(full_sched, x="date", y=["principal_paid", "interest_paid"])
        
        st.subheader("Full Schedule")
        st.dataframe(full_sched, use_container_width=True, hide_index=True)
    else:
        st.info("No loans found. Add one in the Data Entry tab.")


# --- TAB 3: GLOBAL OVERVIEW ---
with tab3:
    st.header("Master Editor")
    current_loans = get_all_loans()
    
    if not current_loans.empty:
        edited_df = st.data_editor(
            current_loans, 
            key="main_editor", 
            disabled=["loan_id", "total_interest", "total_paid"],
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Sync Changes & Recalculate"):
            for index, row in edited_df.iterrows():
                delete_loan_data(row['loan_id'])
                new_sched, t_paid, t_int = calculate_amortization_schedule(
                    row['loan_id'], row['principal'], row['rate'], 
                    int(row['term_months']), row['start_date']
                )
                row['total_paid'] = t_paid
                row['total_interest'] = t_int
                
                detail_row = pd.DataFrame([row])
                save_loan(detail_row, new_sched)
            st.success("All loans recalculated and synced!")
            st.rerun()
    else:
        st.info("Nothing to edit yet.")