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
        tau,        # Residence time    [s]
):
    """

    Calculate the minimun centrifuge diameter required for separating a particle.

    This function calculates the minimum diameter of the centrifuge within a given 
    residence time, based on the law of Stokes adapted to use the centrifugal aceleration
    instead of the gravity.

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
    
    tau : float
        Residence time of the particle in the centrifuge
    
    Notes
    -----
    Based on the differential equations:
        dr/dt = k * r => r(t) = r0 * exp(k * t)
    with:
        k = (dp^2) * (rho_p - rho_l) * (omega^2) / (18*mu)
    and:
        D  = 2 * r(tau)
        
    """
    # Calculate k
    omega = 2 * np.pi * rpm / 60                # rad/s
    k = (dp**2 * (rho_p - rho_l) * omega**2) / (18 * mu)

    # initial radio (close to the axis)
    r0 = 1e-8

    # Radial positio at t = tau
    r_final = r0 * np.exp(k * tau)

    # Diameter
    D = r_final * 2

    return D