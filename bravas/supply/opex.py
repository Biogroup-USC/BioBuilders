import json
import pandas as pd
import math

__all__ = ('load_json',
           'raw_material_cost',
           'labor_cost',
           'opex',
           'export_opex',)

hours_year = 5856

def load_json(file):
    """
    """
    with open(file) as f:
        return json.load(f)

def raw_material_cost(system, prices):
    """
    """
    total = 0

    for s in system.feeds:
        if s.ID in prices:
            total += s.F_mass * hours_year * prices[s.ID]
            
    return total

def labor_cost(process_type, salary = 38366):
    """
    """
    table = {
        "fluid_continuous": 15,
        "fluids_batch": 16,
        "gas": 5,
        "solid_fluids": 15
    }

    workers = table.get(process_type, 15)

    direct = workers * salary
    indirect = math.ceil(0.15 * direct)

    return direct + indirect, direct, indirect

def opex(system, capex_results, prices, process_type, energy_balance = None):
    """
    """
    raw = raw_material_cost(system, prices)

    labor_total, direct, indirect = labor_cost(process_type)

    CF = capex_results["CF"]

    # Exploitation costs
    maintenance = 0.02 * CF
    insurance = 0.01 * CF
    taxes = 0.01 * CF
    lab = 0.10 * labor_total
    
    exploitation = raw + labor_total + maintenance + insurance + taxes + lab

    # Management costs
    admin = 0.15 * exploitation
    commercial = 0.02 * exploitation
    research = 0.02 * CF

    management = admin + commercial + research

    # Amortization
    amortization = capex_results["CAPEX"] / 20

    # Total OPEX
    OPEX = exploitation + management + amortization

    # Get the results
    results = {
        "Raw materials": raw,
        "Labor": labor_total,
        "Maintenance": maintenance,
        "Insurance": insurance,
        "Taxes": taxes,
        "Lab": lab,
        "Exploitation": exploitation,
        "Management": management,
        "Amortization": amortization,
        "OPEX": OPEX
    }

    df_util = pd.DataFrame()
    
    return results, df_util

def export_opex(results, df_util, filename = "opex.xlsx"):
    """
    """
    df = pd.DataFrame(list(results.items()), columns = ["Concept", "€/year"])

    with pd.ExcelWriter(filename) as writer:
        df.to_excel(writer, sheet_name = "Summary", index = False)
        df_util.to_excel(writer, sheet_name = "Utilities", index = False)

    print(f"OPEX exported to {filename}")