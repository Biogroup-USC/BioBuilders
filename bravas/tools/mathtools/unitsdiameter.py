"""
"""
import numpy as np

__all__ = (
    "calculate_centrifuge_diameter",
    "calculate_impeller_diameter",
    "calculate_packing_equivalent_diameter",
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