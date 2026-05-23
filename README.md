# Loan Manager Application

## 🛠️ Installation & Getting Started

### 1. Prerequisites
Ensure you have **Python 3.9 to 3.12** installed on your workstation.

---

### 2. Clone and Initialize Dependencies

Navigate to your project folder and install the required libraries using pip:

```bash
pip install streamlit pandas python-dateutil xlsxwriter openpyxl
```

---

### 3. Launching the App

Run the following command to start the local development server:

```bash
streamlit run app.py
```

The application will automatically launch in your default browser at:

```text
http://localhost:8501
```

---

# 🗄️ Database Schema Design

The application stores and manages data inside the SQLite database:

```text
loan_manager.db
```

The database contains two linked tables.

---

## 1. tbl_amortization_detail

Stores master loan information and high-level calculated KPIs.

| Column Name | Data Type | Description |
|---|---|---|
| loan_id | TEXT (Primary Key) | Unique loan tracking identifier |
| loan_name | TEXT | Descriptive loan name |
| principal | REAL | Original loan amount |
| rate | REAL | Annual interest rate percentage |
| term_months | INTEGER | Loan duration in months |
| start_date | TEXT | Loan start date (`YYYY-MM-DD`) |
| total_interest | REAL | Total calculated interest over the loan |
| total_paid | REAL | Total repayment amount (Principal + Interest) |

---

## 2. tbl_amortization_calc

Stores the complete amortization schedule for each loan.

| Column Name | Data Type | Description |
|---|---|---|
| loan_id | TEXT (Foreign Key) | Links to `tbl_amortization_detail` |
| month_index | INTEGER | Sequential payment month number |
| date | TEXT | Scheduled payment date |
| opening_bal | REAL | Outstanding balance before payment |
| payment | REAL | Fixed monthly EMI/payment |
| principal_paid | REAL | Principal component paid |
| interest_paid | REAL | Interest component paid |
| closing_bal | REAL | Remaining balance after payment |

---

# 📥 Bulk Upload Data Template

When using the **Mass Management Upload** feature, ensure the Excel sheet headers exactly match the following structure:

| loan_id | loan_name | principal | rate | term_years | start_date |
|---|---|---|---|---|---|
| 2001 | Commercial-Alpha | 500000 | 7.5 | 15 | 2026-06-01 |
| 2002 | Equipment-B | 45000 | 4.25 | 5 | 2026-07-15 |

---

# ⚠️ Note on Mass Uploading

The bulk upload process follows strict transactional safety controls:

- Existing calculation logs are cleared before processing
- A fresh rebuild cycle is triggered for all uploaded records
- Loan IDs are validated for uniqueness
- Full amortization schedules are generated automatically
- All records are processed within a single transactional execution flow

This ensures data consistency and prevents duplicate or partial schedule generation.

---

# 🚀 Features

- Loan amortization schedule generation
- EMI and interest calculations
- SQLite-based persistent storage
- Bulk Excel upload support
- Streamlit-powered interactive UI
- Export support using Excel writers
- Dynamic repayment schedule tracking

---

# 📦 Tech Stack

- Python
- Streamlit
- Pandas
- SQLite
- OpenPyXL
- XlsxWriter
- python-dateutil

---

# ▶️ Example Workflow

1. Create or upload loan records
2. System validates input data
3. Amortization schedules are generated
4. Calculations are stored in SQLite
5. Users can review schedules and export reports

---

# 📄 License

This project is intended for educational and internal business use.
