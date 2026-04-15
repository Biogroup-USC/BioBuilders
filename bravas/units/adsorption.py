import biosteam as bst
from biosteam.units.design_tools import PressureVessel
from numba import njit
import numpy as np
from scipy.integrate import solve_ivp

# Code copied from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
@njit(cache=True)
def fixed_step_odeint(f, x0, step, tf, args):
    M = int(tf/step)
    N = len(x0)
    ts = np.linspace(0, tf, M)
    xs = np.zeros((M, N))
    xs[0] = x0
    for i in range(1, M):
        dx_dt = f(ts[i], x0, *args)
        x0 += dx_dt * step
        xs[i] = x0 
    return (ts, xs)

@njit
def equilibrium_loading_Langmuir_isotherm_gas(
    pi,     # Partial pressure [Pa]
    Kp,     # Adsorption equilibrium constant [1/Pa]
    q_max,  # Maximum equilibrium loading [mol/kg]
):
    return pi * Kp * q_max / (1 + Kp * pi)  # mol/kg

# Code copied from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
@njit(cache=True)
def estimate_equilibrium_bed_length(
        C,  # Solute concentration in the feed [kg / m3]
        u,  # Superficial velocity [m / h]
        cycle_time,  # Cycle time [h]
        rho_adsorbent,  # Bulk density of the bed [kg / m3]
        q0,  # Equilibrium loading [g / kg]
    ):
    q_capacity = q0 * rho_adsorbent / 1000 # kg / m3
    L = C * u * cycle_time / q_capacity  # m
    return L

@njit
def dPdt(
    t,
    p,
    N_slices,
    Da,
    dz,
    isotherm_model,
    isotherm_args,
    beta_q0_rho_RT_over_p0,
    p0,
    q0,
):
    PL = p[:N_slices]
    qt = p[N_slices:]

    # Dimensional partial pressure
    pi_ = PL * p0
    for i in range(len(pi_)):
        if pi_[i] < 0.0:
            pi_[i] = 0.0
    
    # Dimensionless equilibrium loading
    qe = isotherm_model(pi_, *isotherm_args) / q0
    for i in range(len(qe)):
        if qe[i] > 1.0:
            qe[i] = 1.0
        elif qe[i] < 0.0:
            qe[i] = 0.0
    
    dPL_dz = PL.copy()
    dPL_dz[1:] = (PL[1:] - PL[:-1]) / dz
    dPL_dz[0] = (PL[0] - 1.0) / dz

    dq_dt = Da * (qe - qt)
    dPL_dt = -dPL_dz - beta_q0_rho_RT_over_p0 * dq_dt

    dp_dt = p.copy()
    dp_dt[:N_slices] = dPL_dt
    dp_dt[N_slices:] = dq_dt
    return dp_dt

def adsorption_bed_pressure_drop_gas(
        dp,       # particle diameter [m]
        rho,      # gas density [kg/m3]
        mu,       # gas viscosity [Pa*s]
        epsilon,  # bed void fraction [-]
        u,        # superficial velocity [m/s]
        L,        # bed length [m]
    ):
    one_minus_eps = 1.0 - epsilon
    eps3 = epsilon**3
    
    dP = (
        150.0 * mu * u * one_minus_eps**2 * L / (dp**2 * eps3)
        + 1.75 * rho * u**2 * one_minus_eps * L / (dp * eps3)
    )
    return dP

class GasAdsorptionColumn(PressureVessel, bst.Unit):
    """
    """
    auxiliary_unit_names = (
        'pump', 'heat_exchanger', 'regeneration_pump'
    )

    _N_ins = 3
    _N_outs = 3

    _units = {
        'Pressure drop': 'Pa',
        **PressureVessel._units
    }

    absorbent_cost = {

    }

    _default_equipment_lifetime = {

    }

    isotherm_models = {
        'langmuir': equilibrium_loading_Langmuir_isotherm_gas,
    }

    # Pa*m3/mol/K
    R_cte = 8.314462

    def _init(
        self,
        outlet_conc: float = None,
        cycle_time: float = None,
        k: float = None,
        isotherm_args: tuple = None,
        isotherm_model: str = None,
        k_regeneration = None,
        regeneration_isotherm_args = None,
        regeneration_isotherm_model = None,
        LUB_forced = None,
        void_fraction = None,
        rho_adsorbent = None,
        superficial_velocity = None,
        P = None,
        p_final_scaled = None,
        N_slices = int(50),
        regeneration_fluid = None,
        adsorbate = None,
        vessel_material = 'Stainless steel 316',
        vessel_type = 'Vertical',
        adsorbent = None,
        N_columns = 3,
        particle_diameter = None
    ):
        if N_columns not in (2,3):
            raise ValueError('only 2 or 3 columns are valid configurations')

        if adsorbate is None:
            raise ValueError('An adsorbate must be specified')
        
        if not isinstance(adsorbate, str):
            raise ValueError('adsorbate must be a string')

        if regeneration_fluid:
            regeneration_pump = self.auxiliary('regeneration_pump', bst.Pump, ins = self.ins[1])
            self.auxiliary('heat_exchanger', bst.HXutility, ins = regeneration_pump.outs[0])

        self.cycle_time = cycle_time
        self.P = P
        self.adsorbate = adsorbate
        self.k = k
        self.void_fraction = void_fraction
        self.rho_adsorbent = rho_adsorbent
        
        self.regeneration_fluid = regeneration_fluid
        self.auxiliary('pump', bst.Pump, ins = self.ins[0])

        self.isotherm_model = self.isotherm_models[isotherm_model.lower()]
        self.isotherm_args = isotherm_args
        
        self.N_slices = N_slices
        self.superficial_velocity = superficial_velocity
        self.outlet_mass_fraction = outlet_conc
        self.particle_diameter = particle_diameter
        self.N_columns = N_columns
        self.vessel_material = vessel_material
        self.vessel_type = vessel_type

    def _run(self):
        feed, regeneration_fluid, adsorbent = self.ins
        outlet, spent_fluid, spent_adsorbent = self.outs
        
        adsorbate = self.adsorbate
        # Outlet composition
        outlet.copy_like(feed)

        adsorbate_in = feed.imass[adsorbate]
        inert_in = feed.F_mass - adsorbate_in

        adsorbate_comp = self.outlet_mass_fraction
        adsorbate_out = (adsorbate_comp/(1-adsorbate_comp)) * inert_in

        outlet.imass[adsorbate] = adsorbate_out

    @staticmethod
    def _calculate_pi(ni, nT, P):
        if nT <= 0.0:
            return 0.0
        return (ni/nT)*P

    @property
    def T0(self):
        return self.ins[0].T

    @property
    def p0(self):
        return self._calculate_pi(
                self.ins[0].imol[self.adsorbate],
                self.ins[0].F_mol,
                self.ins[0].P
            )

    def _PL_to_mass_concentration(self, PL):
        p = PL * self.p0
        C_mol = p / (self.R_cte * self.T0)
        MW = self.ins[0].chemicals[self.adsorbate].MW / 1000.0
        return C_mol * MW

    def _outlet_mass_concentration_profile(self):
        PL_out = self.PL_scaled[-1, :]
        return self._PL_to_mass_concentration(PL_out)
    
    def _breakthrough_time_from_mass_fraction(self):
        feed = self.ins[0]
        adsorbate = self.adsorbate

        C_out = self._outlet_mass_concentration_profile()

        adsorbate_in = feed.imass[adsorbate]
        inert_in = feed.F_mass - adsorbate_in
        w_target = self.outlet_mass_fraction
        adsorbate_out_target = (w_target/(1.0 - w_target)) * inert_in

    def _simulate_adsorption_bed(
        self,
        L,
        u
    ):
        """
        """
        cycle_time = self.cycle_time
        N_slices = self.N_slices
        void_fraction = self.void_fraction
        rho_adsorbent = self.rho_adsorbent
        p0 = self.p0
        T0 = self.T0
        k = self.k
        isotherm_model = self.isotherm_model
        isotherm_args = self.isotherm_args

        # Initial condition
        y0 = np.zeros(2*N_slices,dtype=float)

        # Dimensionless groups
        self.dz = dz = 1.0 / (N_slices - 1.0)
        self.t_scale = t_scale = L/u
        self.Da = Da = k * L/u

        # Reference equilibrium loading at inlet conditions [mol/kg]
        q0 = isotherm_model(p0, *isotherm_args)
        if q0 <= 0:
            raise ValueError("Isotherm returned non-positive q0 at inlet conditions.")
        
        self.q0 = q0

        beta = (1.0 - void_fraction) / void_fraction
        beta_q0_rho_RT_over_p0 = beta * q0 * rho_adsorbent * self.R_cte * T0 / p0

        args = (
            N_slices,
            Da,
            dz,
            isotherm_model,
            isotherm_args,
            beta_q0_rho_RT_over_p0,
            p0,
            q0
        )

        # Integrate from tau = 0 to tau = cycle_time / t_scale
        tf = cycle_time / t_scale

        sol = solve_ivp(
            fun = dPdt,
            t_span = (0.0, tf),
            y0 = y0,
            method = 'BDF',
            args = args,
            atol = 1e-8,
            rtol = 1e-6,
        )

        if not sol.success:
            raise RuntimeError(f"Bed simulation failed: {sol.message}")
        
        # Store results
        self.t_scaled = sol.t
        self.PL_scaled = sol.y[:N_slices, :]
        self.q_scaled = sol.y[N_slices:, :]

        return sol