import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_amortization_schedule(loan_id, principal, annual_rate, term_years, start_date_str, balloon_years=0.0):
    """
    Computes a standard amortization schedule where the monthly payment stays fixed.
    At the balloon cutoff month, the payment absorbs the entire remaining balance + interest.
    """
    monthly_rate = (annual_rate / 100.0) / 12.0
    total_months = int(term_years * 12)
    balloon_cutoff_month = int(balloon_years * 12) if balloon_years > 0 else 0
    
    # Calculate the strict FIXED monthly payment based on the base term
    if monthly_rate > 0:
        fixed_payment = (principal * monthly_rate) / (1 - (1 + monthly_rate) ** (-total_months))
    else:
        fixed_payment = principal / total_months
        
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    records = []
    current_balance = principal
    cumulative_interest = 0.0
    cumulative_paid = 0.0
    
    for i in range(1, total_months + 1):
        opening_bal = current_balance
        interest_paid = round(opening_bal * monthly_rate, 2)
        
        # Determine payment and principal using strict fixed rules
        if balloon_cutoff_month > 0 and i == balloon_cutoff_month:
            # Excel Logic: Payment = Current Interest + Previous Month Closing Bal (opening_bal)
            principal_paid = round(opening_bal, 2)
            payment = round(interest_paid + opening_bal, 2)
            closing_bal = 0.0
        else:
            payment = round(fixed_payment, 2)
            principal_paid = round(payment - interest_paid, 2)
            
            # Handle natural loan payoff end anomalies
            if i == total_months or (opening_bal - principal_paid) < 0:
                principal_paid = round(opening_bal, 2)
                payment = round(principal_paid + interest_paid, 2)
                closing_bal = 0.0
            else:
                closing_bal = round(opening_bal - principal_paid, 2)
                
        current_date_str = (start_date + relativedelta(months=i-1)).strftime('%Y-%m-%d')
        
        records.append({
            "loan_id": loan_id,
            "month_index": i,
            "date": current_date_str,
            "opening_bal": opening_bal,
            "payment": payment,
            "principal_paid": principal_paid,
            "interest_paid": interest_paid,
            "closing_bal": closing_bal,
            "override_closing_bal": 0.0
        })
        
        cumulative_interest += interest_paid
        cumulative_paid += payment
        current_balance = closing_bal
        
        # For rows past the balloon or natural payoff, zero them out completely
        if current_balance <= 0:
            for j in range(i + 1, total_months + 1):
                next_date = (start_date + relativedelta(months=j-1)).strftime('%Y-%m-%d')
                records.append({
                    "loan_id": loan_id, "month_index": j, "date": next_date,
                    "opening_bal": 0.0, "payment": 0.0, "principal_paid": 0.0,
                    "interest_paid": 0.0, "closing_bal": 0.0, "override_closing_bal": 0.0
                })
            break
            
    df = pd.DataFrame(records)
    return df, round(cumulative_paid, 2), round(cumulative_interest, 2)