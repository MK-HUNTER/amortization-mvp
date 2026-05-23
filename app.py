import streamlit as st
import pandas as pd
import io
from database import init_db, save_loan, get_all_loans, get_schedule, delete_loan_data, reset_db
from engine import calculate_amortization_schedule

st.set_page_config(page_title="Amortization MVP", layout="wide")
init_db()

# --- STEP 1: INITIALIZE DEFAULT VALUES IN STATE ---
if "form_loan_id" not in st.session_state:
    st.session_state.form_loan_id = ""
if "form_loan_name" not in st.session_state:
    st.session_state.form_loan_name = ""
if "form_principal" not in st.session_state:
    st.session_state.form_principal = 00.0
if "form_rate" not in st.session_state:
    st.session_state.form_rate = 0.0
if "form_term_years" not in st.session_state:
    st.session_state.form_term_years = 00.0 

# --- STEP 2: STAGE DATA AND SAFELY CLEAR FIELDS ---
def clear_and_stage_form_fields():
    st.session_state.staged_save = {
        "loan_id": str(st.session_state.form_loan_id).strip(),
        "loan_name": str(st.session_state.form_loan_name),
        "principal": float(st.session_state.form_principal),
        "rate": float(st.session_state.form_rate),
        "term_years": float(st.session_state.form_term_years)
    }
    st.session_state.form_loan_id = ""
    st.session_state.form_loan_name = ""
    st.session_state.form_principal = 0.0
    st.session_state.form_rate = 0.0
    st.session_state.form_term_years = 1.0

tab1, tab2, tab3 = st.tabs(["Data Entry", "Loan Inspector", "Global Overview"])

# --- TAB 1: DATA ENTRY & MAINTENANCE ---
with tab1:
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.header("Add New Loan")
    
    col1, col2 = st.columns(2)
    lid = col1.text_input("Loan ID (Unique)", key="form_loan_id")
    lname = col2.text_input("Loan Name", key="form_loan_name")
    princ = col1.number_input("Principal ($)", min_value=0.0, step=1000.0, key="form_principal")
    rate = col2.number_input("Annual Interest Rate (%)", min_value=0.0, step=0.1, key="form_rate")
    term_years = col1.number_input("Term (Years)", min_value=0.1, step=1.0, key="form_term_years")
    sdate = col2.date_input("Start Date").strftime('%Y-%m-%d')

    existing_loans = get_all_loans()
    is_duplicate = False
    
    if lid.strip() and not existing_loans.empty:
        if lid.strip() in existing_loans['loan_id'].values.astype(str):
            is_duplicate = True

    if is_duplicate:
        st.warning(f"⚠️ Loan ID '{lid}' already exists! Please use a unique ID.")

    preview_df = None
    t_paid, t_int = 0.0, 0.0
    if lid.strip() and princ > 0 and term_years > 0 and not is_duplicate:
        preview_df, t_paid, t_int = calculate_amortization_schedule(lid, princ, rate, term_years, sdate)

    with top_col2:
        st.write("##") 
        save_clicked = st.button(
            "Save Loan", 
            type="primary", 
            use_container_width=True, 
            disabled=is_duplicate or not lid.strip(),
            on_click=clear_and_stage_form_fields if (not is_duplicate and lid.strip()) else None
        )

    if save_clicked and "staged_save" in st.session_state:
        staged = st.session_state.staged_save
        if staged["loan_id"]:
            final_sched_df, calc_paid, calc_int = calculate_amortization_schedule(
                staged["loan_id"], staged["principal"], staged["rate"], staged["term_years"], sdate
            )
            
            detail_data = pd.DataFrame([{
                "loan_id": staged["loan_id"], 
                "loan_name": staged["loan_name"], 
                "principal": staged["principal"],
                "rate": staged["rate"], 
                "term_months": int(staged["term_years"] * 12), 
                "start_date": sdate,
                "total_interest": calc_int, 
                "total_paid": calc_paid
            }])
            
            save_loan(detail_data, final_sched_df)
            st.success(f"Loan '{staged['loan_id']}' saved successfully!")
            
        del st.session_state.staged_save
        st.rerun()

    st.subheader("Live Preview (First 5 Months)")
    if preview_df is not None:
        st.dataframe(preview_df.head(5), use_container_width=True, hide_index=True)
    elif is_duplicate:
        st.info("💡 Live preview hidden because the selected Loan ID is a duplicate.")
    else:
        st.info("Enter Principal, Rate, and Term parameters above to see a live preview.")

    st.divider()
    
    st.subheader("Mass Management (Upload & Download)")
    m_col1, m_col2 = st.columns([1, 2])
    
    with m_col1:
        current_records = get_all_loans()
        if current_records.empty:
            template_df = pd.DataFrame(columns=["loan_id", "loan_name", "principal", "rate", "term_years", "start_date"])
        else:
            template_df = current_records.copy()
            template_df["term_years"] = template_df["term_months"] / 12
            template_df = template_df[["loan_id", "loan_name", "principal", "rate", "term_years", "start_date"]]
            
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            template_df.to_excel(writer, index=False, sheet_name='Loans')
        
        st.write("##") 
        st.download_button(
            label="📥 Download Template / Data (Excel)",
            data=buffer.getvalue(),
            file_name="loan_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        if st.button("🗑️ Reset Database (Clear All)", use_container_width=True, type="primary"):
            reset_db()
            st.warning("Database cleared and initialized to fresh state.")
            st.rerun()

    with m_col2:
        uploaded_file = st.file_uploader("Upload Mass Loan Excel File", type=["xlsx"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.button("🚀 Commit Uploaded Data to DB", use_container_width=True, type="primary"):
                try:
                    uploaded_df = pd.read_excel(uploaded_file)
                    required_cols = ["loan_id", "loan_name", "principal", "rate", "term_years", "start_date"]
                    
                    if not all(col in uploaded_df.columns for col in required_cols):
                        st.error(f"Invalid format. File must contain columns: {', '.join(required_cols)}")
                    elif uploaded_df['loan_id'].duplicated().any():
                        st.error("Upload failed: Duplicate loan_id values found within the uploaded file.")
                    else:
                        reset_db()
                        for _, row in uploaded_df.iterrows():
                            u_id = str(row['loan_id']).strip()
                            u_name = str(row['loan_name'])
                            u_princ = float(row['principal'])
                            u_rate = float(row['rate'])
                            u_term_years = float(row['term_years'])
                            u_sdate = pd.to_datetime(row['start_date']).strftime('%Y-%m-%d')
                            
                            sched_df, t_paid, t_int = calculate_amortization_schedule(u_id, u_princ, u_rate, u_term_years, u_sdate)
                            
                            detail_data = pd.DataFrame([{
                                "loan_id": u_id, "loan_name": u_name, "principal": u_princ,
                                "rate": u_rate, "term_months": int(u_term_years * 12),
                                "start_date": u_sdate,
                                "total_interest": t_int, "total_paid": t_paid
                            }])
                            save_loan(detail_data, sched_df)
                            
                        st.success("Fresh upload completed successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error reading file structure: {str(e)}")

# --- TAB 2: LOAN INSPECTOR (UPDATED FOR INTEGRATED CHART & TABLE AGGREGATION) ---
with tab2:
    loans = get_all_loans()
    if not loans.empty:
        loans['id_name'] = loans['loan_id'].astype(str) + " - " + loans['loan_name'].astype(str)
        
        selected_display = st.selectbox("Select Loan to Inspect", loans['id_name'].unique())
        selected_id = loans[loans['id_name'] == selected_display]['loan_id'].values[0]
        loan_info = loans[loans['loan_id'] == selected_id].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Principal", f"${loan_info['principal']:,.2f}")
        c2.metric("Total Interest", f"${loan_info['total_interest']:,.2f}")
        c3.metric("Total Paid", f"${loan_info['total_paid']:,.2f}")
        c4.metric("Rate", f"{loan_info['rate']}%")

        full_sched = get_schedule(selected_id)
        
        st.divider()
        
        # Display Controls Toggle
        chart_top_1, chart_top_2 = st.columns([3, 1])
        with chart_top_1:
            st.subheader("Payment Composition Breakdown")
        with chart_top_2:
            timeline_view = st.radio(
                "Timeline Display Granularity",
                ["Monthly view", "Yearly view"],
                horizontal=True,
                label_visibility="collapsed"
            )

        # Dynamic Content Generation Block based on Granularity Toggle
        if timeline_view == "Yearly view" and not full_sched.empty:
            full_sched['Year'] = pd.to_datetime(full_sched['date']).dt.strftime('%Y')
            
            # Aggregate calculations to build unique structural yearly logs
            yearly_grouped = full_sched.groupby('Year').agg({
                'opening_bal': 'first',         # Bal at the start of that year
                'payment': 'sum',               # Sum payments inside that year
                'principal_paid': 'sum',        # Sum principal payments inside that year
                'interest_paid': 'sum',         # Sum interest payments inside that year
                'closing_bal': 'last'           # Ending balance at the close of that year
            }).reset_index()
            
            # Render chart and clean total tables matching the same yearly logic
            st.bar_chart(yearly_grouped, x="Year", y=["principal_paid", "interest_paid"], use_container_width=True)
            
            st.subheader("Yearly Schedule Summary Reference")
            st.dataframe(yearly_grouped, use_container_width=True, hide_index=True)
        else:
            # Default Monthly presentation paths
            st.bar_chart(full_sched, x="date", y=["principal_paid", "interest_paid"], use_container_width=True)
            
            st.subheader("Full Monthly Schedule Log")
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
                term_val_years = float(row['term_months'] / 12)
                
                new_sched, t_paid, t_int = calculate_amortization_schedule(
                    row['loan_id'], row['principal'], row['rate'], 
                    term_val_years, row['start_date']
                )
                row['total_paid'] = t_paid
                row['total_interest'] = t_int
                
                detail_row = pd.DataFrame([row])
                save_loan(detail_row, new_sched)
            st.success("All loans recalculated and synced successfully!")
            st.rerun()
    else:
        st.info("Nothing to edit yet.")