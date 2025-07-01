"""
"""

__all__ = (
    "calculate_rdvf_area"
)

Filtration_Data = {
    "Fast":{
        "Cake formation": 1,                # mm/s
        "Filtrate rate": 3,                 # L/(s*m2)
        "Cake resistance": 8e8,             # m/kg
    },
    "Medium":{
        "Cake formation": (0.12+1)/2,       # mm/s
        "Filtrate rate": (0.3+3)/2,         # L/(s*m2)
        "Cake resistance": 8e10,            # m/kg
    },
    "Slow":{
        "Cake formation": (1e-3+2e-2)/2,    # mm/s
        "Filtrate rate": (0.3+0.03)/2,      # L/(s*m2)
        "Cake resistance": (10e10+5e10)/2,  # m/kg
    }
}

def calculate_rdvf_area(
        Q: float,
        delta_P: float,
        mu: float,
        alpha: float,
        Cs: float,
        theta: float,
        Rm: float,
        submergence: float = 0.35,
             
):
    """
    """
    denominator = mu * (alpha*Cs*theta + Rm)

    if denominator <= 0:
        raise ValueError("Invalid denominator. Check the following parameters: mu, Rm and theta")
    
    A_effective = Q * denominator/delta_P

    if submergence <= 0:
        raise ValueError("Submergence must be between 0 and 1.")
    
    A_total = A_effective/submergence

    return A_total