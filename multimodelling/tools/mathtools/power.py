"""
"""
from math import pi

__all__ = (

)

def calculate_agitator_power(
        Np: float = 0.79,           # Assumption in http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
        N: float = None,
        rho: float = None,
        V_reactor: float = None,
        D_impeller: float = None,
        H_per_D: float = 1.0,
        D_over_T: float = 1/3,      # Assumption in http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
        is_rpm: bool = True,
        is_kW: bool = True,
        return_volumetric: bool = True,
):
    """
    """
    # Basic validations
    if Np <= 0: raise ValueError("Np must be > 0")
    if rho <= 0: raise ValueError("rho must be > 0")
    if H_per_D <= 0: raise ValueError("H_per_D must be > 0")
    if D_impeller is None and V_reactor is None:
        raise ValueError("Provide D_impeller or V_reactor")
    if return_volumetric and (V_reactor is None or V_reactor <= 0):
        raise ValueError("For P/V provide V_reactor > 0")

    # Convert rpm to rps
    Ns = N/60.0 if is_rpm else N
    if Ns <= 0: raise ValueError("N (in s^-1) must be > 0")

    # Calculate the diameter of the impeller
    if D_impeller is None:
        T = (4.0 * V_reactor / (pi * H_per_D))**(1.0/3.0)
        D_impeller = D_over_T * T
    if D_impeller <= 0:
        raise ValueError("D_impeller must be > 0")

    # Calculate the power of the agitator
    power = Np * (D_impeller**5 * Ns**3 * rho)
    if is_kW:
        power = power/1000
    return power/V_reactor if return_volumetric else power