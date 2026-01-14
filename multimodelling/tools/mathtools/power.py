"""
"""
from math import pi
from typing import Literal

__all__ = (
    "calculate_agitator_power",
)

# From Towler, Gavin P., and R. K. Sinnott. 2022. Chemical Engineering Design : 
# Principles, Practice and Economics of Plant and Process Design. Chapter 10.
# Figure 10.77.
NP_TYPE_CORRELATION = {           
    "Rushton (1/5)": (4.5 + 5.0)/2,                     # Rushton turbine (w/D = 1/5)
    "Hub-mounted flat-blade (1/5)": 4.0,                # Hub-mounted flat-blade turbine (w/D = 1/5)
    "Rushton (1/8)": (2.5 + 3.0)/2,                     # Rushton turbine (w/D = 1/8)
    "Hub-mounted flat-blade (1/8)": (2.6 + 2.7)/2,      # Hub-mounted flat-blade turbine (w/D = 1/8)
    "Hub-mounted curved-blade (1/8)": (2.2 + 2.6)/2,    # Hub-mounted curved-blade turbine (w/D = 1/8)
    "Pitched blade (1/8)": 2.4,                         # Pitched blade turbine (w/D = 1/8)
}

# From Towler, Gavin P., and R. K. Sinnott. 2022. Chemical Engineering Design : 
# Principles, Practice and Economics of Plant and Process Design. Chapter 10.
# Table 10.16.
VOLUMETRIC_POWER_BY_TYPE = {
    "Mild": (0.03 + 0.10)/2, 
    "Medium": (1.0 + 1.5)/2,
    "Severe": (1.5 + 2.0)/2,
    "Violent": 2.25,
}

# Empirical flow numbers from http://dx.doi.org/10.1021/acs.iecr.7b00360
EMPIRICAL_FLOW_NUMBERS = {
    "Marine propeller": 0.50,
    "Four-bladed 45º": 0.87,
    "Six-bladed disk turbine": 1.30,
    "HE-3 high-efficency impeller": 0.47,
}

def calculate_agitator_power(
        impeller_type: str = None,
        Np: float = 3.44,               # Assumption in http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
        N: float = None,
        rho: float = None,
        V_reactor: float = None,
        D_impeller: float = None,
        H_per_D: float = 1.0,
        D_over_T: float = 1/3,          # Assumption in http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
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
    impeller_type : str
        Type of impeller to estimate Np using Sinnot correlations. If no
        impeller type is provided, Np parameter is being used as an estimated
        value. Note that for this correlation turbulent flow is assumed.
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
    # Validations
    if rho <= 0: raise ValueError("rho must be > 0")
    if not 0. < efficiency <= 1.: raise ValueError("Efficiency must be between 0 and 1")
    if H_per_D <= 0: raise ValueError("H_per_D must be > 0")
    if D_impeller is None and V_reactor is None:
        raise ValueError("Provide D_impeller or V_reactor")
    if return_volumetric and (V_reactor is None or V_reactor <= 0):
        raise ValueError("For P/V provide V_reactor > 0")
    
    # Use Np from Sinnot correlations or just use a given value
    if isinstance(impeller_type,str):
        if impeller_type not in NP_TYPE_CORRELATION:
            raise ValueError(f"'{impeller_type}' is not a valid type. Use one of the impellers"
                             "mentioned in the documentation of this function")
        np = NP_TYPE_CORRELATION[impeller_type]
    else:
        np = Np

    # Convert rpm to rps
    Ns = N/60.0 if is_rpm else N
    if Ns <= 0: raise ValueError("N (in s^-1 or in min^-1) must be > 0")

    # Calculate the diameter of the impeller
    if D_impeller is None:
        D_reactor = (4.0 * V_reactor / (pi * H_per_D))**(1.0/3.0)
        D_impeller = D_reactor * D_over_T
    if D_impeller <= 0:
        raise ValueError("D_impeller must be > 0")

    # Calculate the power of the agitator
    power = np * (D_impeller**5 * Ns**3 * rho) / efficiency
    if is_kW:
        power = power/1000
    return power/V_reactor if return_volumetric else power

def _estimate_volumetric_power(agitation_type: str = "Medium"):
    """

    This function returns the volumetric power for estimating agitator
    consumption.

    Volumetric power is selected depending on agitation conditions. The
    values used for each condition come from Towler, Gavin P., and 
    R. K. Sinnott. 2022. Chemical Engineering Design : Principles, Practice 
    and Economics of Plant and Process Design. Chapter 10.

    parameters
    ----------
    agitation_type : str
        * "Mild": blending, mixing and homogeneous reactions.
        * "Medium": Heat transfer and liquid-liquid mixing.
        * "Severe": Slurry suspension, gas absorption and emulsions.
        * "Violent": Fine slurry suspension. 

    """
    volumetric_power = VOLUMETRIC_POWER_BY_TYPE[agitation_type]
    return volumetric_power

def _calculate_agitator_power_piccinno(
        flow_type: Literal["Axial flow", "Radial flow"] = "Radial flow",
        Np: float = None, 
        N: float = None,
        rho: float = None,
        D_impeller: float = None,
        efficiency: float = 0.90,
):
    """
    """
    # Choose Np used
    if Np is not None:
        # Validate Np type
        if not isinstance(Np, float):
            return TypeError("Np must be a float.")
        power_number = Np
    else:
        if flow_type == "Radial flow":
            power_number = 3.44
        else:
            power_number = 0.79
    
    # Calculate stirring power (W)
    agitator_power = power_number * rho * (N**3) * (D_impeller **5) / efficiency

    return agitator_power

def _calculate_agitator_power_zhou(
    impeller_type: str = None,
    N: float = None,
    rho: float = None,
    alpha: float = None,
    D_impeller: float = None,
    efficiency: float = 0.90,
):
    """
    """
    # Calculate flow number
    flow_number = EMPIRICAL_FLOW_NUMBERS[impeller_type]
    power_number = (alpha**2) * (pi**2) * 1/2 * flow_number

    # Calculate stirring power (W)
    agitator_power = power_number * (D_impeller**5) * (N**3) * rho / efficiency

    return agitator_power

def agitator_volumetric_power_determination(
    method: Literal["Piccinno method","Strict Zhou method","Sinnot heuristics","Approximate Zhou method"] = None,
    Np: float = None,
    impeller_type: str = "Rushton (1/5)",
):
    """
    """

    # Apply the method selected
    if method == "Piccinno method":
        if Np is not None:
            power = _calculate_agitator_power_piccinno(
                Np = Np,
                N = rps,
                rho = mixture_rho,
                D_impeller = D_impeller,
                efficiency = efficiency,
            )
        else:
            power = _calculate_agitator_power_piccinno(
                flow_type = flow_type,
                N = rps,
                rho = mixture_rho,
                D_impeller = D_impeller,
                efficiency = efficiency,
            )
    elif method == "Strict Zhou method":
        power = _calculate_agitator_power_zhou(
            impeller_type = NQ_impeller_type,
            N = rps,
            alpha = alpha,
            D_impeller = D_impeller,
            efficiency = efficiency,
        )
    elif method == "Approximate Zhou method":
        power_number = NP_TYPE_CORRELATION[impeller_type]
        power = power_number * (D_impeller**5) * (N**3) * rho / efficiency
    else:
        volumetric_power = _estimate_volumetric_power(Agitation_type)
        return volumetric_power