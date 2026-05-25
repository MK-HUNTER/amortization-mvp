import streamlit as st
import pandas as pd
import io
import sqlite3
from database import init_db, save_loan, get_all_loans, get_schedule, delete_loan_data, reset_db
from engine import calculate_amortization_schedule

st.set_page_config(page_title="Amortization MVP", layout="wide")
init_db()

# Helper to provide connection access safely within app runtime environment
def get_app_connection():
    return sqlite3.connect("loan_manager.db")

# --- STEP 1: INITIALIZE DEFAULT VALUES IN STATE ---
if "form_loan_id" not in st.session_state:
    st.session_state.form_loan_id = "1001"
if "form_loan_name" not in st.session_state:
    st.session_state.form_loan_name = "Test"
if "form_principal" not in st.session_state:
    st.session_state.form_principal = 100000.0
if "form_rate" not in st.session_state:
    st.session_state.form_rate = 10.0
if "form_term_years" not in st.session_state:
    st.session_state.form_term_years = 10.0 
if "form_balloon_years" not in st.session_state:
    st.session_state.form_balloon_years = 0.0  # 0.0 means no balloon payout window exists

# --- STEP 2: STAGE DATA AND SAFELY CLEAR FIELDS ---
def clear_and_stage_form_fields():
    st.session_state.staged_save = {
        "loan_id": str(st.session_state.form_loan_id).strip(),
        "loan_name": str(st.session_state.form_loan_name),
        "principal": float(st.session_state.form_principal),
        "rate": float(st.session_state.form_rate),
        "term_years": float(st.session_state.form_term_years),
        "balloon_years": float(st.session_state.form_balloon_years)
    }
    st.session_state.form_loan_id = ""
    st.session_state.form_loan_name = ""
    st.session_state.form_principal = 0.0
    st.session_state.form_rate = 0.0
    st.session_state.form_term_years = 1.0
    st.session_state.form_balloon_years = 0.0

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
    term_years = col1.number_input("Amortization Term (Years)", min_value=0.1, step=1.0, key="form_term_years")
    balloon_years = col1.number_input("Balloon Period (Years, Optional - 0 to disable)", min_value=0.0, step=1.0, key="form_balloon_years", help="If specified, the loan will require a lump-sum payoff at the end of this period.")
    sdate = col2.date_input("Start Date").strftime('%Y-%m-%d')

    # Guard check for balloon duration logic errors
    if balloon_years > term_years:
        st.error("⚠️ Balloon Period cannot be longer than the base Amortization Term!")
        is_invalid_balloon = True
    else:
        is_invalid_balloon = False

    existing_loans = get_all_loans()
    is_duplicate = False
    
    if lid.strip() and not existing_loans.empty:
        if lid.strip() in existing_loans['loan_id'].values.astype(str):
            is_duplicate = True

    if is_duplicate:
        st.warning(f"⚠️ Loan ID '{lid}' already exists! Please use a unique ID.")

    preview_df = None
    t_paid, t_int = 0.0, 0.0
    if lid.strip() and princ > 0 and term_years > 0 and not is_duplicate and not is_invalid_balloon:
        preview_df, t_paid, t_int = calculate_amortization_schedule(lid, princ, rate, term_years, sdate, balloon_years)

    with top_col2:
        st.write("##") 
        save_clicked = st.button(
            "Save Loan", 
            type="primary", 
            use_container_width=True, 
            disabled=is_duplicate or not lid.strip() or is_invalid_balloon,
            on_click=clear_and_stage_form_fields if (not is_duplicate and lid.strip() and not is_invalid_balloon) else None
        )

    if save_clicked and "staged_save" in st.session_state:
        staged = st.session_state.staged_save
        if staged["loan_id"]:
            final_sched_df, calc_paid, calc_int = calculate_amortization_schedule(
                staged["loan_id"], staged["principal"], staged["rate"], staged["term_years"], sdate, staged["balloon_years"]
            )
            
            detail_data = pd.DataFrame([{
                "loan_id": staged["loan_id"], 
                "loan_name": staged["loan_name"], 
                "principal": staged["principal"],
                "rate": staged["rate"], 
                "term_months": int(staged["term_years"] * 12), 
                "balloon_years": float(staged["balloon_years"]),
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
        st.info("Enter parameters to see a live calculation timeline preview.")

    st.divider()
    
    st.subheader("Mass Management (Upload & Download)")
    m_col1, m_col2 = st.columns([1, 2])
    
    with m_col1:
        current_records = get_all_loans()
        if current_records.empty:
            template_df = pd.DataFrame(columns=["loan_id", "loan_name", "principal", "rate", "term_years", "balloon_years", "start_date"])
        else:
            template_df = current_records.copy()
            template_df["term_years"] = template_df["term_months"] / 12
            if "balloon_years" not in template_df.columns:
                template_df["balloon_years"] = 0.0
            template_df = template_df[["loan_id", "loan_name", "principal", "rate", "term_years", "balloon_years", "start_date"]]
            
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
                            u_balloon_years = float(row.get('balloon_years', 0.0))
                            u_sdate = pd.to_datetime(row['start_date']).strftime('%Y-%m-%d')
                            
                            sched_df, t_paid, t_int = calculate_amortization_schedule(u_id, u_princ, u_rate, u_term_years, u_sdate, u_balloon_years)
                            
                            detail_data = pd.DataFrame([{
                                "loan_id": u_id, "loan_name": u_name, "principal": u_princ,
                                "rate": u_rate, "term_months": int(u_term_years * 12),
                                "balloon_years": u_balloon_years,
                                "start_date": u_sdate,
                                "total_interest": t_int, "total_paid": t_paid
                            }])
                            save_loan(detail_data, sched_df)
                            
                        st.success("Fresh mass import processing run successfully completed!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error reading file structure: {str(e)}")

# --- TAB 2: LOAN INSPECTOR (EXCEL BALANCED RECALCULATION ENGINE) ---
with tab2:
    loans = get_all_loans()
    if not loans.empty:
        loans['id_name'] = loans['loan_id'].astype(str) + " - " + loans['loan_name'].astype(str)
        
        selected_display = st.selectbox("Select Loan to Inspect", loans['id_name'].unique())
        selected_id = loans[loans['id_name'] == selected_display]['loan_id'].values[0]
        loan_info = loans[loans['loan_id'] == selected_id].iloc[0]
        
        # Summary Metric Blocks
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Principal", f"${loan_info['principal']:,.2f}")
        c2.metric("Total Interest", f"${loan_info['total_interest']:,.2f}")
        c3.metric("Total Paid", f"${loan_info['total_paid']:,.2f}")
        c4.metric("Rate", f"{loan_info['rate']}%")

        raw_sched = get_schedule(selected_id)
        
        if not raw_sched.empty:
            if 'override_closing_bal' not in raw_sched.columns:
                raw_sched['override_closing_bal'] = 0.0

            raw_sched['original_closing_bal'] = raw_sched['closing_bal']

            # --- LIVE EXCEL-MATCHING CASCADING ENGINE ---
            processed_rows = raw_sched.copy()
            annual_rate = float(loan_info['rate']) / 100.0
            monthly_rate = annual_rate / 12.0
            total_months = len(processed_rows)
            
            balloon_years_val = float(loan_info['balloon_years']) if 'balloon_years' in loan_info else 0.0
            balloon_cutoff_month = int(balloon_years_val * 12) if balloon_years_val > 0 else 0

            # Step A: Get baseline initial fixed payment parameter
            if monthly_rate > 0:
                base_fixed_payment = (float(loan_info['principal']) * monthly_rate) / (1 - (1 + monthly_rate) ** (-total_months))
            else:
                base_fixed_payment = float(loan_info['principal']) / total_months

            is_loan_terminated = False

            for idx in range(len(processed_rows)):
                current_month_num = idx + 1
                
                if is_loan_terminated:
                    processed_rows.loc[idx, 'opening_bal'] = 0.0
                    processed_rows.loc[idx, 'payment'] = 0.0
                    processed_rows.loc[idx, 'principal_paid'] = 0.0
                    processed_rows.loc[idx, 'interest_paid'] = 0.0
                    processed_rows.loc[idx, 'closing_bal'] = 0.0
                    continue

                if idx > 0:
                    processed_rows.loc[idx, 'opening_bal'] = processed_rows.loc[idx - 1, 'closing_bal']
                
                current_opening = processed_rows.loc[idx, 'opening_bal']
                current_interest = round(current_opening * monthly_rate, 2)
                processed_rows.loc[idx, 'interest_paid'] = current_interest
                
                # Check for Balloon Cutoff Month (Matches Excel exactly)
                if balloon_cutoff_month > 0 and current_month_num == balloon_cutoff_month:
                    processed_rows.loc[idx, 'principal_paid'] = round(current_opening, 2)
                    processed_rows.loc[idx, 'payment'] = round(current_interest + current_opening, 2)
                    processed_rows.loc[idx, 'closing_bal'] = 0.0
                    is_loan_terminated = True
                    continue
                
                # Standard Month: Payment stays consistent with baseline setup
                processed_rows.loc[idx, 'payment'] = round(base_fixed_payment, 2)
                processed_rows.loc[idx, 'principal_paid'] = round(processed_rows.loc[idx, 'payment'] - current_interest, 2)
                std_closing = round(current_opening - processed_rows.loc[idx, 'principal_paid'], 2)
                
                # Check for Manual User Row Overrides
                curr_override = processed_rows.loc[idx, 'override_closing_bal']
                if curr_override > 0:
                    processed_rows.loc[idx, 'closing_bal'] = round(curr_override, 2)
                    adjusted_principal = round(current_opening - curr_override, 2)
                    processed_rows.loc[idx, 'principal_paid'] = adjusted_principal
                    processed_rows.loc[idx, 'payment'] = round(adjusted_principal + current_interest, 2)
                else:
                    final_calculated_bal = round(max(0.0, std_closing), 2)
                    processed_rows.loc[idx, 'closing_bal'] = final_calculated_bal
                    if final_calculated_bal <= 0.0:
                        is_loan_terminated = True

            datetime_series = pd.to_datetime(processed_rows['date'])
            st.divider()
            
            # View Controls
            chart_top_1, chart_top_2 = st.columns([2, 2])
            with chart_top_1:
                st.subheader("Payment Composition Breakdown")
            with chart_top_2:
                timeline_view = st.radio(
                    "Timeline Display Granularity",
                    ["Monthly view", "Quarterly view", "Yearly view"],
                    horizontal=True,
                    label_visibility="collapsed"
                )

            cutoff_index = balloon_cutoff_month if balloon_cutoff_month > 0 else total_months
            visible_display_rows = processed_rows.head(cutoff_index).copy()

            if timeline_view == "Yearly view":
                visible_display_rows['Year'] = datetime_series.dt.strftime('%Y')
                yearly_grouped = visible_display_rows.groupby('Year').agg({
                    'opening_bal': 'first', 'payment': 'sum', 'principal_paid': 'sum',
                    'interest_paid': 'sum', 'closing_bal': 'last', 'original_closing_bal': 'last'
                }).reset_index()
                st.bar_chart(yearly_grouped, x="Year", y=["principal_paid", "interest_paid"], use_container_width=True)
                st.dataframe(yearly_grouped, use_container_width=True, hide_index=True)
                
            elif timeline_view == "Quarterly view":
                visible_display_rows['Quarter'] = datetime_series.dt.to_period('Q').astype(str)
                quarterly_grouped = visible_display_rows.groupby('Quarter').agg({
                    'opening_bal': 'first', 'payment': 'sum', 'principal_paid': 'sum',
                    'interest_paid': 'sum', 'closing_bal': 'last', 'original_closing_bal': 'last'
                }).reset_index()
                st.bar_chart(quarterly_grouped, x="Quarter", y=["principal_paid", "interest_paid"], use_container_width=True)
                st.dataframe(quarterly_grouped, use_container_width=True, hide_index=True)
                
            else:
                st.bar_chart(visible_display_rows, x="date", y=["principal_paid", "interest_paid"], use_container_width=True)
                
                edit_header_col, edit_action_col = st.columns([3, 1])
                with edit_header_col:
                    st.subheader("Editable Monthly Amortization Schedule Ledger")
                    st.caption("💡 Adjust manual balance shifts in **'override_closing_bal'**. Click Save to finalize.")
                
                display_cols = [
                    "month_index", "date", "opening_bal", "payment", 
                    "principal_paid", "interest_paid", "original_closing_bal", 
                    "override_closing_bal", "closing_bal"
                ]
                
                edited_monthly_df = st.data_editor(
                    visible_display_rows[display_cols],
                    key=f"monthly_editor_{selected_id}",
                    disabled=["month_index", "date", "opening_bal", "payment", "principal_paid", "interest_paid", "original_closing_bal", "closing_bal"],
                    hide_index=True,
                    use_container_width=True
                )
                
                with edit_action_col:
                    st.write("##")
                    has_changes = not edited_monthly_df["override_closing_bal"].equals(raw_sched.loc[edited_monthly_df.index, "override_closing_bal"])
                    
                    if st.button("💾 Save Balance Modifications", type="primary", use_container_width=True, disabled=not has_changes):
                        conn = get_app_connection()
                        cursor = conn.cursor()
                        try:
                            for _, row in edited_monthly_df.iterrows():
                                cursor.execute('''
                                    UPDATE tbl_amortization_calc 
                                    SET override_closing_bal = ? 
                                    WHERE loan_id = ? AND month_index = ?
                                ''', (float(row['override_closing_bal']), selected_id, int(row['month_index'])))
                            conn.commit()
                            st.success("Changes permanently saved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")
                        finally:
                            conn.close()
    else:
        st.info("No loans found. Add one in the Data Entry tab.")

# --- TAB 3: GLOBAL OVERVIEW ---
with tab3:
    st.header("Master Editor")
    current_loans = get_all_loans()
    
    if not current_loans.empty:
        # Avoid column matching exceptions if balloon_years hasn't populated old records
        if "balloon_years" not in current_loans.columns:
            current_loans["balloon_years"] = 0.0
            
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
                balloon_val_years = float(row.get('balloon_years', 0.0))
                
                new_sched, t_paid, t_int = calculate_amortization_schedule(
                    row['loan_id'], row['principal'], row['rate'], 
                    term_val_years, row['start_date'], balloon_val_years
                )
                row['total_paid'] = t_paid
                row['total_interest'] = t_int
                
                detail_row = pd.DataFrame([row])
                save_loan(detail_row, new_sched)
            st.success("All loans recalculated and synced successfully!")
            st.rerun()
    else:
        st.info("Nothing to edit yet.")