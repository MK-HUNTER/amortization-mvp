import pandas as pd
import streamlit as st

@st.cache_data
def generate_amortization_schedule(principal, annual_rate, years):
    """
    Generates a monthly amortization schedule.
    annual_rate is expected as a decimal (e.g., 0.05 for 5%).
    """
    periods = years * 12
    monthly_rate = annual_rate / 12
    
    # Calculate Monthly Payment (PMT)
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
        
        # Guard against floating point errors on the final payment
        if i == periods:
            remaining_balance = 0

        schedule.append({
            "Period": i,
            "Opening Balance": round(opening_balance, 2),
            "Total Payment": round(pmt, 2),
            "Interest Component": round(interest_payment, 2),
            "Principal Component": round(principal_payment, 2),
            "Closing Balance": round(max(0, remaining_balance), 2)
        })

    return pd.DataFrame(schedule)

generate_amortization_schedule(100000, 10, 20);