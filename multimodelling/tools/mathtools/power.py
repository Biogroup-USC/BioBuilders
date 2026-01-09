"""
"""
from math import pi

__all__ = (
    "calculate_agitator_power",
)

def calculate_agitator_power(
        Np: float = 3.44,           # Assumption in http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
        N: float = None,
        rho: float = None,
        V_reactor: float = None,
        D_impeller: float = None,
        H_per_D: float = 1.0,
        D_over_T: float = 1/3,      # Assumption in http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
        efficiency: float = 0.90,
        is_rpm: bool = True,
        is_kW: bool = True,
        return_volumetric: bool = True,
):
    """

    This function calculates power or volumetric power of an agitator
    for a tank with certain volume which contains a liquid with certain
    density.

    Power (or volumetric power) is calculated using the correlation in
    Piccinno et al. (http://dx.doi.org/10.1016/j.jclepro.2016.06.164):
    ``E [J] = (Np * rho * N^3 * d^5 * t)/efficiency`` which was adapted
    to obtain ``E [J/s] = (Np * rho * N^3 * d^5 * t) / efficiency``.

    Parameters
    ----------
    Np : float
        Power number of impeller that can be calculated with the following
        equation: ``Np = K * Re^b * Fr^c`` from Sinnot and Towler eq. 10.18
        of chapter 10.11.
    N : float
        Impeller rotational speed. Piccinno's correlation uses this parameter
        in s^-1. However, it could be provided in rpm if it is then indicated.
    rho : float
        Density of the mixture [kg/m^3].
    V_reactor : float
        Working volume of the reactor or mixing tank [m^3].
    D_impeller : float
        Impeller diameter [m]. If this parameter is unknown, it is calculated using
        height-diameter and diameter-turbine proportions which have default values.
    efficiency : float
        Agitator capacity to translate the energy provided to the fluid. Default to 0.90.
    is_rpm : bool
        Is the N provided in rpm instead of s^-1? Default to True.
    is_kW : bool
        Is the result given in kW? Default to True.
    return_volumetric : bool
        Is the result given in kW/m^3? Default to True.
        
    """
    # Basic validations
    if Np <= 0: raise ValueError("Np must be > 0")
    if rho <= 0: raise ValueError("rho must be > 0")
    if not 0. < efficiency <= 1.: raise ("Efficiency must be between 0 and 1")
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
    power = Np * (D_impeller**5 * Ns**3 * rho) / efficiency
    if is_kW:
        power = power/1000
    return power/V_reactor if return_volumetric else power