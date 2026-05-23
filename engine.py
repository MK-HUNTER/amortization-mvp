import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_amortization_schedule(loan_id, principal, annual_rate, term_years, start_date):
    """Generates a full monthly schedule and high-level KPIs based on term in years."""
    term_months = int(term_years * 12)
    monthly_rate = (annual_rate / 100) / 12
    
    if monthly_rate > 0:
        monthly_payment = (principal * monthly_rate) / (1 - (1 + monthly_rate)**(-term_months))
    else:
        monthly_payment = principal / term_months
    
    rows = []
    current_balance = principal
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    for i in range(1, term_months + 1):
        interest_payment = current_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        
        if i == term_months:
            principal_payment = current_balance
            monthly_payment = principal_payment + interest_payment
            
        opening_balance = current_balance
        current_balance -= principal_payment
        payment_date = start_dt + relativedelta(months=i-1)
        
        rows.append({
            "loan_id": loan_id,
            "month_index": i,
            "date": payment_date.strftime('%Y-%m-%d'),
            "opening_bal": round(opening_balance, 2),
            "payment": round(monthly_payment, 2),
            "principal_paid": round(principal_payment, 2),
            "interest_paid": round(interest_payment, 2),
            "closing_bal": round(max(0, current_balance), 2)
        })
        
    df_schedule = pd.DataFrame(rows)
    total_paid = df_schedule['payment'].sum()
    total_interest = total_paid - principal
    
    return df_schedule, round(total_paid, 2), round(total_interest, 2)