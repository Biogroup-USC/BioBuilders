"""
"""
from math import pi
from typing import Literal

__all__ = (
    "calculate_agitator_power",
    "agitator_volumetric_power_determination",
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

def _estimate_volumetric_power(agitation_type: Literal["Mild","Medium","Severe","Violent"] = "Medium") -> float:
    """

    This function returns the volumetric power for estimating agitator
    consumption [kW/m3].

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
    
    Returns
    -------
    volumetric_power : float
        Volumetric power in kW/m3 of the agitator.

    """
    # Validate key
    if agitation_type not in VOLUMETRIC_POWER_BY_TYPE:
        raise ValueError("'{}' is not a valid agitation type. Valid keys: {}".format(agitation_type,list(VOLUMETRIC_POWER_BY_TYPE.keys())))
    
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

    This function calculates the agitation power in W using the approach of
    Piccinno et al., 2016 (http://dx.doi.org/10.1016/j.jclepro.2016.06.164).

    The agitation power is calculated following the next equation:
    `P_stirr [W] = Np * rho * N**3 * D_impeller**5 / efficiency`. The power number (Np) used is 0.79
    for axial flow and 3.44 for radial flow as Piccinno et al., 2016 indicates. Moreover,
    Np could be provided manually ignoring the default values extracted from Piccinno et al., 2016.

    Parameters
    ----------
    flow_type : str
        * ["Axial flow"] for Np = 0.79.
        * ["Radial flow"] for Np = 3.44.
    Np : float
        Power number for calculating agitation power. If this parameter is provided, default values
        for Axial or Radial flow will be ignored.
    N : float
        Rotational speed of agitator [rps].
    rho : float
        Density of the mixture [kg/m3].
    D_impeller : float
        Diameter of impeller [m].
    efficiency : float
        Efficiency of the agitator. Default is 0.90.
    
    Returns
    -------
    agitator_power : float
        Agitation power in W.

    """
    if N is None: 
        raise ValueError("A value of N must be provided.")
    
    if rho is None: 
        raise ValueError("A value of rho must be provided.")
    
    if D_impeller is None: 
        raise ValueError("A value of D_impeller must be provided.")

    # Validate arguments
    if N <= 0:
        raise ValueError("N (1/s) must be higher than 0.")
    
    if rho <= 0: 
        raise ValueError("rho (kg/m3) must be higher than 0.")
    
    if D_impeller <= 0: 
        raise ValueError("D_impeller must be higher than 0.")

    if not 0 < efficiency <= 1:
        raise ValueError("efficiency must be (0,1]")
    
    if flow_type not in ("Radial flow","Axial flow"): 
        raise ValueError("flow_type must be 'Radial flow' or 'Axial flow'")

    # Choose Np used
    if Np is not None:
        # Validate Np type
        if not isinstance(Np, (float, int)):
            raise TypeError("Np must be a float or an integer.")
        
        # Validate Np value
        if Np <= 0:
            raise ValueError("Np must be higher than 0.")
        
        Np_used = Np
    else:
        if flow_type == "Radial flow":
            Np_used = 3.44
        else:
            Np_used = 0.79
    
    # Calculate stirring power (W)
    agitator_power = Np_used * rho * (N**3) * (D_impeller **5) / efficiency

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

    This function calculates the agitation power in W using the approach of
    Zhou et al., 2017 (http://dx.doi.org/10.1021/acs.iecr.7b00360).

    The agitation power is calculated following the next equation:
    `P_stirr [W] = Np * rho * N**3 * D_impeller**5 / efficiency`. The power
    number (Np) is calculated following the next equation:
    `Np = alpha**2 * pi**2 * 1/2 * flow_number`. The flow number (NQ) used is 
    selected from Zhou et al., 2017 values depending on the impeller type.

    Parameters
    ----------
    impeller_type : str
        * Marine propeller. NQ = 0.50.
        * Four-bladed 45º. NQ = 0.87.
        * Six-bladed disk turbine. NQ = 1.30.
        * HE-3 high-efficiency impeller. NQ = 0.47.
    N : float
        Rotational speed of agitator [rps].
    rho : float
        Density of the mixture [kg/m3].
    alpha : float
        factor correlating fluid velocities generated by the agitation and
        impeller tip velocity. Default is 0.5.
    D_impeller : float
        Diameter of impeller [m].
    efficiency : float
        Efficiency of the agitator. Default is 0.90.

    Returns
    -------
    agitator_power : float
        Agitation power [W].

    """
    if N is None: 
        raise ValueError("A value of N must be provided.")
    
    if rho is None: 
        raise ValueError("A value of rho must be provided.")
    
    if D_impeller is None: 
        raise ValueError("A value of D_impeller must be provided.")
    
    if alpha is None:
        raise ValueError("alpha must be provided.")

    # Validate arguments
    if N <= 0:
        raise ValueError("N (1/s) must be higher than 0.")
    
    if rho <= 0: 
        raise ValueError("rho (kg/m3) must be higher than 0.")
    
    if D_impeller <= 0: 
        raise ValueError("D_impeller must be higher than 0.")

    if not 0 < efficiency <= 1:
        raise ValueError("efficiency must be (0,1]")
    
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be (0,1]")

    # Calculate flow number
    if impeller_type not in EMPIRICAL_FLOW_NUMBERS:
        raise ValueError("{} is not a valid impeller type for NQ correlation. Valid keys: {}".format(impeller_type,list(EMPIRICAL_FLOW_NUMBERS.keys())))
    
    flow_number = EMPIRICAL_FLOW_NUMBERS[impeller_type]
    power_number = (alpha**2) * (pi**2) * 1/2 * flow_number

    # Calculate stirring power (W)
    agitator_power = power_number * (D_impeller**5) * (N**3) * rho / efficiency

    return agitator_power

def _get_power_number(Np,Np_impeller_type):
    """

    This function decides to use either the power number provided or
    from Sinnott-based default values depending on impeller.

    Parameters
    ----------
    Np : float
        Power number to calculate agitation power.
    Np_impeller_type : str
        * Rushton (1/5).
        * Hub-mounted flat-blade (1/5).
        * Rushton (1/8).
        * Hub-mounted flat-blade (1/8).
        * Hub-mounted curved-blade (1/8).
        * Pitched blade (1/8).

    Returns
    -------
    power_number : float
        Power number (dimensionless)
        
    """
    if Np is not None:
        if not isinstance(Np,(float, int)):
            raise TypeError("Np must be a float or an integer.")
        
        if Np <= 0:
            raise ValueError("Np must be higher than 0.")

        power_number = Np
    else:
        if Np_impeller_type not in NP_TYPE_CORRELATION:
                
            valid_keys = list(NP_TYPE_CORRELATION.keys())

            raise ValueError("{} is not a valid impeller type for Np correlation. Select: {}".format(Np_impeller_type, valid_keys))
        power_number = NP_TYPE_CORRELATION[Np_impeller_type]
    return power_number

def agitator_volumetric_power_determination(
    method: Literal[
        "Piccinno method",
        "Zhou method",
        "Sinnott heuristics",
        "Agitation power equation"
    ] = "Agitation power equation",
    Np: float = None,
    Np_impeller_type: str = "Rushton (1/5)",
    flow_type: Literal["Axial flow", "Radial flow"] = "Radial flow",
    rps: float = None,
    mixture_rho: float = None,
    D_impeller: float = None,
    efficiency: float = 0.90,
    NQ_impeller_type: str = "Six-bladed disk turbine",
    alpha: float = 0.50,
    agitation_type: str = "Medium",
    volume: float = None
):
    """

    This function calculates the volumetric agitation power of a stirred tank
    assuming a cylindrical geometry.

    The agitation power is calculated following one of the methods explained below:

    * Agitation power equation: solve the agitation power equation
    (`P_stirr = Np * mixture_rho * rps**3 * D_impeller**5 / efficiency`) 
    using the value of Np provided or from Sinnott-based default values depending 
    on Np_impeller_type.

    * Piccinno method: apply the approach of Piccinno et al., 2016 (http://dx.doi.org/10.1016/j.jclepro.2016.06.164).
    The power number used depends on the flow_type: 0.79 for "Axial flow" and 3.44 for "Radial flow".

    * Zhou method: apply the approach of Zhou et al., 2017 (http://dx.doi.org/10.1021/acs.iecr.7b00360).
    the Np is calculated from `Np = alpha**2 * pi**2 * 1/2 * flow_number`. The flow number (NQ) used is
    selected from Zhou et al., 2017 values depending on NQ_impeller_type.

    * Sinnott heuristics: estimate the volumetric power consumption using heuristics from 
    Towler, Gavin P., and R. K. Sinnott. 2022. Chemical Engineering Design : Principles, Practice 
    and Economics of Plant and Process Design. Chapter 10.
    
    The agitation power obtained is in W (besides Sinnott heuristics which return kW/m3). Therefore, it is
    converted to kW/m3 using the stirred tank volume (volume).

    Parameters
    ----------
    method : str
        - Agitation power equation.
        - Piccinno method.
        - Zhou method.
        - Sinnott heuristics.
    Np : float
        Power number.
    Np_impeller_type : str
        - Rushton (1/5).
        - Hub-mounted flat-blade (1/5).
        - Rushton (1/8).
        - Hub-mounted flat-blade (1/8).
        - Hub-mounted curved-blade (1/8).
        - Pitched blade (1/8).
    flow_type : str
        - Axial for Np = 0.79.
        - Radial for Np = 3.44.
    NQ_impeller_type : str
        - Marine propeller. NQ = 0.50.
        - Four-bladed 45º. NQ = 0.87.
        - Six-bladed disk turbine. NQ = 1.30.
        - HE-3 high-efficiency impeller. NQ = 0.47.
    agitation_type : str
        - Mild.
        - Medium.
        - Severe.
        - Violent.
    rps : float
        Revolutions per second [s^-1].
    mixture_rho : float
        Density of the mixture [kg/m^3].
    D_impeller : float.
        Diameter of the impeller [m].
    efficiency : float
        The fraction of mechanical power that is transmitted to the fluid.
    alpha : float
        factor correlating fluid velocities generated by the agitation and
        impeller tip velocity. Default is 0.5.
    volume : float
        Volume of agitated tank used to determine volumetric power.

    Returns
    -------
    volumetric_power : float
        Volumetric power in kW/m3 of the agitator.

    """

    # Apply the method selected
    if method == "Agitation power equation":

        power_number = _get_power_number(Np,Np_impeller_type)

        power = _calculate_agitator_power_piccinno(
            Np = power_number,
            N = rps,
            rho = mixture_rho,
            D_impeller = D_impeller,
            efficiency = efficiency,
        )
    elif method == "Piccinno method":

        power = _calculate_agitator_power_piccinno(
            flow_type = flow_type,
            N = rps,
            rho = mixture_rho,
            D_impeller = D_impeller,
            efficiency = efficiency,
        )
    elif method == "Zhou method":
        
        power = _calculate_agitator_power_zhou(
            impeller_type = NQ_impeller_type,
            N = rps,
            rho = mixture_rho,
            alpha = alpha,
            D_impeller = D_impeller,
            efficiency = efficiency,
        )
    elif method == "Sinnot heuristics":
        
        volumetric_power = _estimate_volumetric_power(agitation_type)
        
        return volumetric_power  
    else:
        raise ValueError(
            "Select a valid method:\n"
            "* Agitation power equation\n"
            "* Piccinno method\n"
            "* Zhou method\n"
            "* Sinnot heuristics"
        )

    # Calculate volumetric power kW/m3
    if volume is None or volume <= 0:
        raise ValueError("Volume of agitated tank must be provided or higher than 0.")

    volumetric_power = power/(volume * 1000)

    return volumetric_power