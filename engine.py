import pandas as pd
import streamlit as st

@st.cache_data
def generate_amortization_schedule(principal, annual_rate, years):
    periods = int(years * 4)
    monthly_rate = annual_rate / 4
    
    if monthly_rate > 0:
        pmt = principal * (monthly_rate * (1 + monthly_rate)**periods) / ((1 + monthly_rate)**periods - 1)
    else:
        pmt = principal / periods

    schedule = []
    remaining_balance = principal

    for i in range(1, periods + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = pmt - interest_payment
        opening_balance = remaining_balance
        remaining_balance -= principal_payment
        
        if i == periods: remaining_balance = 0

        schedule.append({
            "Period": i,
            "Opening Balance": round(opening_balance, 2),
            "Total Payment": round(pmt, 2),
            "Interest Component": round(interest_payment, 2),
            "Principal Component": round(principal_payment, 2),
            "Closing Balance": round(max(0, remaining_balance), 2)
        })
    return pd.DataFrame(schedule)