import pandas as pd
import numpy as np
import numpy_financial as npf

__all__ = ('loan_table',
           'cash_flow',
           'VAN_TIR',
           'export_economic',
           )

def loan_table(CAPEX, i=0.06, n=20):
    """
    """
    R = CAPEX * (i*(1+i)**n) / ((1+i)**n-1)

    debt = CAPEX
    rows = []

    for year in range(n+1):
        if year == 0:
            rows.append([year, "-", "-", "-", debt])
        else:
            interest = debt * i
            principal = R - interest
            debt -= principal

            rows.append([year, R, interest, principal, max(debt,0)])
    
    df = pd.DataFrame(rows, columns = ["Year", "R", "Interest", "Principal", "Debt"])
    return df

def cash_flow(opex, income, CAPEX, loan_df, inflation = 0.02, tax = 0.3, n = 20):
    """
    """
    rows = []
    cum = -CAPEX

    for year in range(n+1):
        if year == 0:
            rows.append([year, "-", "-", "-", "-", "-", "-", "-", -CAPEX, cum])
        else:
            income *= (1+inflation)
            opex *= (1+inflation)

            interest = loan_df.loc[year, "Interest"]

            BAIT = income - opex - interest
            taxes = abs(BAIT * tax)
            BN = BAIT - taxes
            
            FN = BN + (CAPEX/n)

            cum += FN
            
            rows.append([year, income, opex, interest, CAPEX/n, BAIT, taxes, BN, FN, cum])
    
    df = pd.DataFrame(rows, columns = [
        "Year", "Income", "OPEX", "Interest", "Amortization", 
        "BAIT", "Taxes", "Net Profit", "Cash Flow", "Cumulative"])

    return df

def VAN_TIR(df, CAPEX, d = 0.1):
    """
    """
    flows = df["Cash Flow"].iloc[1:]

    VAN = sum([f/(1+d)**i for i, f in enumerate(flows,1)]) - CAPEX

    TIR = npf.irr([-CAPEX] + list(flows))

    return VAN, TIR

def export_economic(loan, cashflow, VAN, TIR, filename = "economic.xlsx"):
    """
    """
    with pd.ExcelWriter(filename) as writer:
        loan.to_excel(writer, sheet_name = "Loan", index = False)
        cashflow.to_excel(writer, sheet_name = "CashFlow", index = False)

        df = pd.DataFrame({
            "Metric": ["VAN", "TIR"],
            "Value": [VAN, TIR]
        })
        df.to_excel(writer, sheet_name = "Indicators", index = False)
    
    print("Economic analysis exported")