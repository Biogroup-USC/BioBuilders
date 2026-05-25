"""
"""
import numpy as np

__all__ = (
    "calculate_centrifuge_diameter",
    "calculate_impeller_diameter",
    "calculate_packing_equivalent_diameter",
    "calculate_tank_dimensions",
)

def calculate_centrifuge_diameter(
        dp,         # Particle diameter [m]
        rho_p,      # Particle density  [kg/m3]
        rho_l,      # Liquid density    [kg/m3]
        mu,         # Liquid viscosity  [Pa*s]
        rpm,        # Rotational speed  [rpm]
        Q,          # Volumetric flow   [m3/s]
        H           # Height            [m]
):
    """

    Calculate the minimum centrifuge diameter required for separating a particle
    in a basket centrifuge based on a sigma value approach.

    This function uses Stokes' law for sedimentation and relates it to the sigma
    factor of a basket centrifuge to compute the required diameter.

    Parameters
    ----------
    dp : float
        Particle diameter [m].
    
    rho_p : float
        Density of the particle [kg/m3].
    
    rho_l : float
        Density of the liquid [kg/m3].
    
    mu : float
        Viscosity of the liquid [Pa*s].
    
    rpm : float
        Rotational speed of the centrifuge [rpm].
    
    Q : float
        Volumetric flow [m3/h].
    
    H : float
        Height of the basket [m].
    
    Notes
    -----
    The sigma is calculated using the following equation:
        Sigma = Q / (2 * Vg)
    where:
        Vg = (rho_p - rho_l) * (dp**2) * 9.81/(18 * mu)
    
    The diameter of the basket centrifuge is calculated using
    the next correlation:
        Sigma = (omega**2) * H * D**2 / (8 * g)
    where:
        omega = angular speed [rad/s].
        D = centrifuge diameter [m].

    """
    # Gravitational acceleration
    g = 9.81    # m/s^2

    # Convert Q to m^3/s
    Q_s = Q/3600

    # Check to avoid division by zero
    if mu <= 0 or dp <= 0 or rho_p <= rho_l:
        raise ValueError("Invalid physical parameters for sedimentation")

    # Settling velocity from Stokes' law
    Vg =  ((rho_p - rho_l) * (dp ** 2) * 9.81)/(18 * mu)

    # Calculate the required sigma for this separation
    Sigma = Q_s / (2*Vg)

    # Angular velocity [rad/s]
    omega = 2 * np.pi * rpm/60

    # Solve the diameter using sigma expression:
    # Sigma = (omega**2 * H * D**2) / (8 * g) => D = sqrt((8 * g * Sigma) / (H * omega**2))
    Diameter = np.sqrt((Sigma * 8 * 9.81)/(H * omega**2))

    return Diameter, Sigma

def calculate_impeller_diameter(
        V_reactor: float = None,
        impeller_react_diameter: float = 1/3,
        height_diameter: float = 1.,
):
    """

    This functions calculates vessel diameter using its volume, impeller/diameter and
    height/diameter proportions.

    Parameters
    ----------
    V_reactor : float
        Volume of the reactor [m^3].
    impeller_react_diameter : float
        impeller : diameter proportion [m/m].
    height_diameter : float
        height : diameter proportion [m/m].

    """
    impeller_diameter = (4 * V_reactor /((impeller_react_diameter**-1)**3 * height_diameter * np.pi))**(1/3)

    return impeller_diameter

def calculate_packing_equivalent_diameter(void_fraction, surface_area):
    """
    Calculate equivalent particle diameter (Sauter diameter) for packing.

    Parameters
    ----------
    void_fraction : float
        Bed void fraction (ε), dimensionless (0 < ε < 1)

    surface_area : float
        Specific surface area of packing (a), in m²/m³

    Returns
    -------
    dp : float
        Equivalent particle diameter (m)
    """
    if not (0 < void_fraction < 1):
        raise ValueError("void_fraction must be between 0 and 1")

    if surface_area <= 0:
        raise ValueError("surface_area must be positive")

    return 6 * (1 - void_fraction) / surface_area

def calculate_tank_dimensions(
        mass_flow,
        tau,
        density = 1000,
        design_factor = 1.2,
        height_diameter_ratio = 1.0
):
    """
    Calculate the required tanl volume, diameter and height based
    on residence time and a design factor.

    Parameter 
    ---------
    mass_flow: float
        Mass flow entering the vessel [kg/hr].

    tau: float
        Residence time [h].

    density: float, optional
        Fluid density [kg/m3]. Default is 1000 kg/m3.
    
    design_factor = float, optional
        Oversizing factor applied to the calculated volume. Default is 1.2.
    
    diameter_height_ratio: float, optional
        Diameter/height ratio (D/H) [m/m]. Default is 1.0.

    Notes
    -----
    The vessel volume is calculated as:
        V = (mass_flow / density) * tau * design_factor
    
    Assuming a cylindrical vessel adn using D/H ratio:
        D = (4 * V / (pi* ratio)) ^ (1/3)
        H = D * ratio
    
    Returns
    -------
    Volume: float
        Vessel volume [m3].
    
    Diameter: float
        Vessel diameter [m].
    
    Height: float
        Vessel height [m].
    """

    # Check inputs
    if mass_flow <= 0:
        raise ValueError("Mass flow must be positive")
    
    if tau <= 0:
        raise ValueError("Residence time must be positive")
    
    if density <= 0:
        raise ValueError("Density must be positive")
    
    if design_factor <= 0:
        raise ValueError("Design factor must be positive")
    
    if height_diameter_ratio <= 0:
        raise ValueError("Height/diameter ratio must be positive")
    
    # Required vessel volume [m3]
    volume = mass_flow / density * tau * design_factor

    # Diameter [m]
    diameter = (
        (4 * volume / (np.pi * height_diameter_ratio)) ** (1/3)
    )

    # Height [m]
    height = diameter * height_diameter_ratio

    return volume, diameter, height