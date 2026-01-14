"""
"""
import numpy as np

__all__ = (
    "calculate_centrifuge_diameter"
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

def calculate_impeller_diameter():
    """
    """
    