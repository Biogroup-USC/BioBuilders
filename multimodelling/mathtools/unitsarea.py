"""
"""

__all__ = (
    "calculate_rdvf_area"
)

Filtration_Data = {                         # Reference: Rules of the Thumb in Engineering Practice: page 168 / DOI: 10.1002/9783527611119.
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

def cakeweight_cakethickness_correlation(
        cakeweight: float,
        cakethickness: float
):
    """
    """
    # Slope and intercept of the correlation
    m = (20-10)/(1.50-0.75)     # Reference: Perry's Chemical Engineering Handbook 9th Edition 18-89
    intercept = 0               # Reference: Perry's Chemical Engineering Handbook 9th Edition 18-89

    if cakeweight:
        cake_thickness = cakeweight/m
        return cake_thickness
    elif cakethickness:
        cake_weight = m * cakethickness
        return cake_weight
    else:
        raise ValueError("A value for either cakeweight or cakethickness must be provided")

def cakeweight_formtime_correlation(
        cakeweight: float,
        formtime: float
):
    """
    """
    # Slope and intercept of the correlation
    m = 0.50        # Perry's Chemical Engineering Handbook 9th Edition 18-90
    intercept = 6   # Perry's Chemical Engineering Handbook 9th Edition 18-90

    if cakeweight:
        cake_form_time = (cakeweight - intercept)/m
        return cake_form_time
    elif formtime:
        cake_weight = m * formtime + intercept
        return cake_weight
    else:
        raise ValueError("A value for either cakeweight or formtime must be provided")

def calculate_theta_from_thickness(
        L: float,
        epsilon: float,
        rho_s: float,
        Cs: float
):
    """
    """
    if not (0 < epsilon < 1): 
        raise ValueError("Porosity (epsilon) must remain between 0 and 1.")
    return (1-epsilon) * rho_s * L / Cs

def calculate_theta_from_rate(
        v_cake: float,
        omega: float,
        epsilon: float,
        rho_s: float,
        Cs: float,
        submergence: float = 0.35      
):
    """
    """
    if omega <= 0:
        raise ValueError("Angular velocity must be > 0.")
    t_sub = submergence / omega
    L = v_cake * t_sub
    return calculate_theta_from_thickness(L,epsilon,rho_s,Cs)

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

    Calculate the filtration area required for a rotatory drum vacuum
    filter given the filtrate rate (Q), pressure difference (delta_P),
    viscosidad (mu), Filtrate volume per m2 (theta), medium resistence (Rm) 
    and cake resistence (alpha). The equation used is the following:

    Q = delta_P/(mu*(Rm + alpha * Cs * theta))

    Parameters
    ----------
    Q : float
    
    delta_P : float

    mu : float

    alpha : float

    Cs : float

    theta : float

    Rm : float
    
    submergence : float

    """
    denominator = mu * (alpha*Cs*theta + Rm)

    if denominator <= 0:
        raise ValueError("Invalid denominator. Check the following parameters: mu, Rm and theta")
    
    A_effective = Q * denominator/delta_P

    if submergence <= 0:
        raise ValueError("Submergence must be between 0 and 1.")
    
    A_total = A_effective/submergence

    return A_total