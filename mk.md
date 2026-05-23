 #  Amortization App

    Streamlit app - Minimal Viable Product, user friendly, easy to learn.

    1.Data Architecture :
    User will input or mass upload the data. ( loan_id, loan_name, start month, principal, intrest rate, tenure(years),comments).

    the data is stored in two tables.

     tbl_Amortization Detail :  Stores the user entered value without any changes. 
                                Stores the KPI values calculated based on the Calc ( live event )
                                
     tbl_Amortization Calc : Calculates the payment, principal component and interest component in time series.
    
    UI :
    Input, Mass Download - Upload tab. --> User will input or mass upload the data. ( loan_id, loan_name, start month, principal, interest rate, tenure).
     Criteria: 
        * AFter input the fields should be empty.
        * If the user enters a loan id that already exists a warning should " The loan id already exists ". If the excel any duplicated it show them exception report.
        * User should be able to see the preview table (calculator while the input in form which will be stored in Calc tbale.) before they save.
        * Mass Download should download the existing load details ( loan_id, loan_name, start month, principal, intrest rate, tenure) 
        * Mass Upload should clear all tables start fresh from the new uploaded file data.

    Loan Inspector( Details per loan ) tab
        * A table view that shows the selected loans details (  payment, principal component and interest component in time series.)
        * KPI Metrics : Total Principal, Total Interest, Total Payment and Rate , Year
        * A chart with time in column showing payments ( Interest vs Principal)

    Loan Overview ( Summary Sheets.)

     * All Loans as line items (loan id, loan name(editable), start month(editable), principal(editable), intrest(editable), tenure (editable), PAYMENT, COMMNETS, editable)
     * Save button to save the edited changes to db and recalculate .