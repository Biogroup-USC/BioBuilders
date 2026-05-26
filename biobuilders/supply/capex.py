import pandas as pd

__all__ = ('get_equipment_costs',
           'calculate_capex',
           'export_capex_excel',)

def get_equipment_costs(system):
    """
    """
    data = []

    for u in system.units:
        if hasattr(u, 'baseline_purchase_costs') and u.baseline_purchase_costs:
            for k, v in u.baseline_purchase_costs.items():
                Ceq = v
                Ceqf = u.purchase_costs.get(k, v)

                data.append({
                    "Unit": u.ID,
                    "Equipment": k,
                    "Ceq (€)": Ceq,
                    "Ceqf (€)": Ceqf
                })
        
    df = pd.DataFrame(data)
    return df

def calculate_capex(system, process_type = "fluids", plant_lifetime = 20):
    """
    """
    df_eq = get_equipment_costs(system)

    Ceq = df_eq["Ceq (€)"].sum()
    Ceqf = df_eq["Ceqf (€)"].sum()

    # Factors
    if process_type == "fluids":
        factors = {
            "fFER": 0.4,
            "fPIP": 0.7,
            "fINST": 0.2,
            "fELEC": 0.1,
            "fUTIL": 0.5,
            "fOS": 0.2,
            "fBUILD": 0.2,
            "fSP": 0.1,
            "fDEC": 1,
            "fCONT": 0.4,
            "fWC": 0.7
        }
    else:
        factors = {
            "fFER": 0.5,
            "fPIP": 0.2,
            "fINST": 0.1,
            "fELEC": 0.1,
            "fUTIL": 0.2,
            "fOS": 0.2,
            "fBUILD": 0.3,
            "fSP": 0.1,
            "fDEC": 0.8,
            "fCONT": 0.3,
            "fWC": 0.6
        }
    
    # Direct costs
    CD = (
        factors["fFER"] * Ceq +
        factors["fPIP"] * Ceqf +
        factors["fINST"] * Ceq +
        factors["fELEC"] * Ceq + 
        factors["fUTIL"] * Ceq +
        factors["fOS"] * Ceq +
        factors["fBUILD"] * Ceq + 
        factors["fSP"] * Ceq
    )

    # Indirect costs
    CI = (
        factors["fDEC"] * Ceq +
        factors["fCONT"] * Ceq
    )

    # Fixed costs
    CF = CD + CI

    # Working capital
    WC = factors["fWC"] * Ceq

    # CAPEX
    CAPEX = CF + WC
    CAPEX_year = CAPEX / plant_lifetime

    # Export the results
    results = {
        "Ceq": Ceq,
        "Ceqf": Ceqf,
        "CD": CD,
        "CI": CI,
        "CF": CF,
        "WC": WC,
        "CAPEX": CAPEX,
        "Annual CAPEX": CAPEX_year
    }
    return results, df_eq

def export_capex_excel(results, df_eq, filename = "capex.xlxs"):
    """
    """
    df_summary = pd.DataFrame(list(results.items()), columns = ["Concept", "€"])

    with pd.ExcelWriter(filename) as writer:
        df_summary.to_excel(writer, sheet_name = "Summary", index = False)
        df_eq.to_excel(writer, sheet_name = "Equipment", index = False)
    
    print(f"CAPEX exported to {filename}")