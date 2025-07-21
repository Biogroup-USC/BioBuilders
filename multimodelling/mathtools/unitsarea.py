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

Filtration_Media_Resistence = {
    "PI&PPS": 4e8,                          # https://doi.org/10.1016/j.powtec.2012.05.003            
    "PI": 4.5e8,                            # https://doi.org/10.1016/j.powtec.2012.05.003
    "PTFE": 2.3e8,                          # https://doi.org/10.1016/j.powtec.2012.05.003
}

def cakeweight_cakethickness_correlation(
        cakeweight: float,
        cakethickness: float
):
    """
    """
    # Slope and intercept of the correlation
    m = (20-10)/(1.50-0.75)                 # Reference: Perry's Chemical Engineering Handbook 9th Edition 18-89
    intercept = 0                           # Reference: Perry's Chemical Engineering Handbook 9th Edition 18-89

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
    m = 0.50                                # Perry's Chemical Engineering Handbook 9th Edition 18-90
    intercept = 6                           # Perry's Chemical Engineering Handbook 9th Edition 18-90

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
        mf_fil: float,
        rho_fil: float,
        delta_P: float,
        mu: float,
        alpha: float,
        Cs: float,
        theta: float,
        Rm: float|str,
        submergence: float = 0.35,
             
):
    """

    Calculate the filtration area required for a rotatory drum vacuum
    filter given the filtrate rate (Q), pressure difference 
    (delta_P), viscosidad (mu), Filtrate volume per m2 (theta), medium 
    resistence (Rm) and cake resistence (alpha). The equation used is 
    the following:

    Q/area = delta_P/(mu*(Rm + alpha * Cs * theta))

    Parameters
    ----------
    Q : float
    
    delta_P : float

    mu : float

    alpha : float

    Cs : float

    theta : float

    Rm : float|str
    
    submergence : float

    """
    if isinstance(Rm, str) and Rm in Filtration_Media_Resistence:
        Rm_val = Filtration_Media_Resistence[Rm]
    elif isinstance(Rm, (int, float)):
        Rm_val = Rm
    else:
        raise ValueError("Rm must be either a float or one of the following str: {}".format(Filtration_Media_Resistence.keys()))

    # Conversion from mass flow (kg/h) to volumetric flow (m3/s)
    if rho_fil <= 0:
        raise ValueError("La densidad del filtrado (rho_f) debe ser mayor que 0.")
    Q = mf_fil / rho_fil / 3600

    denominator = mu * (alpha * Cs * theta + Rm_val)
    if denominator <= 0:
        raise ValueError("Invalid denominator. Check the following parameters: mu, Rm and theta")

    A_effective = Q * denominator/delta_P

    if submergence <= 0:
        raise ValueError("Submergence must be between 0 and 1.")
    
    A_total = A_effective/submergence

    return A_total

print(calculate_rdvf_area(631.4,1000,50000,0.001,8e10,100,calculate_theta_from_rate(0.001,2.67,0.4,1000,100),"PI"))