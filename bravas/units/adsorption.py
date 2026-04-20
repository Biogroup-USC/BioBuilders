import biosteam as bst
from biosteam.units.design_tools import PressureVessel
from numba import njit
import numpy as np
import math

@njit(cache=True)
def equilibrium_loading_Langmuir_isotherm_gas(
    pi,     # Partial pressure [Pa]
    Kp,     # Adsorption equilibrium constant [1/Pa]
    q_max,  # Maximum equilibrium loading [mol/kg]
):
    return pi * Kp * q_max / (1 + Kp * pi)  # mol/kg

# http://dx.doi.org/10.1016/j.cej.2014.07.108
@njit(cache=True)
def equilibrium_loading_Langmuir_dual_site_isotherm_gas(
    pi,     # Adsorbate partial pressure [Pa] 
    ka,     # Adsorption equilibrium constant for cage alpha [1/Pa]
    kb,     # Adsorption equilibrium constant for cage beta [1/Pa]
    q_max,  # Maximum equilibrium loading [mol/kg]
):
    first_term = 0.162 * q_max * (kb * pi) / (1 + kb * pi)
    second_term = 0.838 * q_max * (ka * pi) / (1 + ka * pi)
    return first_term + second_term

@njit(cache=True)
def estimate_bed_length_sinnott(
    C_ads,          # mol/m3
    u,              # m/h
    t_ads,          # h
    rho_adsorbent,  # kg/m3
    f_L,            # bed usage fraction
    q_ads,          # mol/kg
    q_regen,        # mol/kg
):
    q_work = (q_ads - q_regen) * rho_adsorbent
    length = C_ads * u * t_ads / (q_work * f_L)
    return length

def ergun_pressure_drop(
        dp,       # particle diameter [m]
        rho,      # gas density [kg/m3]
        mu,       # gas viscosity [Pa*s]
        epsilon,  # bed void fraction [-]
        u,        # superficial velocity [m/s]
        L,        # bed length [m]
    ):
    
    first_term = 150 * ((1-epsilon)**2)/epsilon**3 * (mu * u)/dp**2
    second_term = 1.75 * (1-epsilon)/epsilon**3 * (rho * u**2)/dp

    dP_L = first_term + second_term
    dP = dP_L * L
    return dP, dP_L

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

    # Default lifetime for component
    _default_equipment_lifetime = {
        'Zeolite 3A': 3,    # https://doi.org/10.1021/acsomega.1c03370?urlappend=%3Fref%3DPDF&jav=VoR&rel=cite-as
    }

    # Cost of regeneration $/m3
    absorbent_cost = {

    }

    # Adsorbent properties
    adsorbent_properties = {
        'Zeolite 3A': {                     
            'void fraction': 0.30,                      # Perry's table 16-5 from 16-5.
            'bulk density': (620 + 680)/2,              # Perry's table 16-5 from 16-5.
            'superficial velocity': (0.150+0.250)/2,    # Rules of the Thumb. Chapter 4. Section 11. Page 118
        }
    }

    isotherm_models = {
        'langmuir': equilibrium_loading_Langmuir_isotherm_gas,
        'langmuir-langmuir': equilibrium_loading_Langmuir_dual_site_isotherm_gas,
    }

    # Pa*m3/mol/K
    R_cte = 8.314462

    def _init(
        self,
        adsorbed_fraction: float = 1.,
        u_superficial: float = None,
        t_ads: float = None,
        t_regen: float = None,
        isotherm_args: tuple = None,
        isotherm_model: str = None,
        regeneration_isotherm_args = None,
        regeneration_isotherm_model = None,
        void_fraction = None,
        rho_adsorbent = None,
        P_ads = None,
        P_regen = None,
        regeneration_fluid = None,
        adsorbate = None,
        vessel_material = 'Stainless steel 316',
        vessel_type = 'Vertical',
        adsorbent: str = None,
        N_columns = 3,
        particle_diameter = None,
        f_L = 0.7,
    ):
        if N_columns not in (2,3):
            raise ValueError('only 2 or 3 columns are valid configurations')

        if adsorbate is None:
            raise ValueError('An adsorbate must be specified')
        if not isinstance(adsorbate, str):
            raise ValueError('adsorbate must be a string')
        
        if adsorbent is None:
            raise ValueError('An adsorbent must be specified')
        if not isinstance(adsorbent, str):
            raise ValueError('adsorbent must be a string')

        if rho_adsorbent is None:
            if adsorbent in self.adsorbent_properties.keys():
                rho_adsorbent = self.adsorbent_properties[adsorbent]['bulk density']
            else:
                raise ValueError(f'rho_adsorbent must be provided for this adsorbent. You can choose other adsorbent with available properties: {self.adsorbent_properties.keys()}')
        if void_fraction is None:
            if adsorbent in self.adsorbent_properties.keys():
                void_fraction = self.adsorbent_properties[adsorbent]['void fraction']
            else:
                raise ValueError(f'void_fraction must be provided for this adsorbent. You can choose other adsorbent with available properties: {self.adsorbent_properties.keys()}')
        if u_superficial is None:
            if adsorbent in self.adsorbent_properties.keys():
                u_superficial = self.adsorbent_properties[adsorbent]['superficial velocity']
            else:
                raise ValueError(f'u_superficial must be provided for this adsorbent. You can choose other adsorbent with available properties: {self.adsorbent_properties.keys()}')

        if regeneration_fluid:
            regeneration_pump = self.auxiliary('regeneration_pump', bst.Pump, ins = self.ins[1])
            self.auxiliary('heat_exchanger', bst.HXutility, ins = regeneration_pump.outs[0])

        self.t_ads = t_ads
        self.t_regen = t_regen
        self.P_ads = P_ads
        self.P_regen = P_regen

        self.adsorbate = adsorbate
        self.adsorbed_fraction = adsorbed_fraction
        
        self.adsorbent = adsorbent
        self.void_fraction = void_fraction
        self.rho_adsorbent = rho_adsorbent
        self.f_L = f_L
        self.u_superficial = u_superficial

        self.regeneration_fluid = regeneration_fluid
        self.auxiliary('pump', bst.Pump, ins = self.ins[0])

        self.isotherm_model = self.isotherm_models[isotherm_model.lower()]
        self.isotherm_args = isotherm_args
        
        self.regeneration_isotherm_model = self.isotherm_models[regeneration_isotherm_model.lower()]
        self.regeneration_isotherm_args = regeneration_isotherm_args

        self.particle_diameter = particle_diameter
        self.N_columns = N_columns
        self.vessel_material = vessel_material
        self.vessel_type = vessel_type

        self._adsorbate_chemical = None
        self._regeneration = None

    @property
    def adsorbate_chemical(self):
        if self._adsorbate_chemical is None:
            try:
                self._adsorbate_chemical = self.thermo.chemicals[self.adsorbate]
            except KeyError:
                raise ValueError(f"Adsorbate '{self.adsorbate}' not found in chemicals")
        return self._adsorbate_chemical
    
    @property
    def adsorbate_MW(self):
        return self.adsorbate_chemical.MW
    
    @property
    def regeneration(self):
        return (
            self.regeneration_isotherm_model is not None
            and self.t_regen is not None
            and self.t_regen > 0
        )

    def _run(self):
        feed, regeneration_fluid, adsorbent = self.ins
        outlet, spent_fluid, spent_adsorbent = self.outs
        
        adsorbate = self.adsorbate
        t_cycle = self.t_regen + self.t_ads

        # Outlets
        outlet.copy_like(feed)
        spent_fluid.empty()
        spent_adsorbent.empty()

        # Inlet adsorbate
        feed_in = feed.F_mol
        na_in = feed.imol[adsorbate]

        # Outlet adsorbate
        na_out = (1-self.adsorbed_fraction) * na_in
        na_out = min(max(na_out,0.),na_in)

        # Adsorbate removed during adsorption
        na_removed_rate = max(na_in - na_out, 0.0)

        # Adsorbate removed per column
        na_removed_ads_step = na_removed_rate * self.t_ads

        # Work capacity
        pa = self._calculate_pi(na_in, feed_in, self.P_ads)
        q_ads = self.isotherm_model(
            pa, *self.isotherm_args
        )

        if self.regeneration:
            regen_in = regeneration_fluid.F_mol
            na_regen = regeneration_fluid.imol[adsorbate]
            pa_regen = self._calculate_pi(na_regen, regen_in, self.P_regen)
            q_regen = self.regeneration_isotherm_model(
                pa_regen, *self.regeneration_isotherm_args
            )
        else:
            q_regen = 0.
        
        q_work = max(q_ads - q_regen, 1e-12)

        # Adsorbent mass per column
        mass_adsorbent = na_removed_ads_step / (q_work * self.f_L)

        # Outlet stream
        outlet.P = self.P_ads
        outlet.imol[adsorbate] = na_out
        
        # Spent fluid and spent adsorbent streams
        spent_fluid.P = self.P_regen
        if self.regeneration:
            spent_fluid.imol[adsorbate] = na_removed_ads_step/t_cycle
        else:
            spent_adsorbent.imol[adsorbate] = na_removed_ads_step/t_cycle
        
        # Variables considered in _design
        self._M_ads = mass_adsorbent
        self._q_work = q_work
        self._nAds_removed_ads_step = na_removed_ads_step
        self._q_ads = q_ads
        self._q_regen = q_regen
        self._t_cycle = t_cycle

    @staticmethod
    def _calculate_pi(ni, nT, P):
        if nT <= 0.0:
            return 0.0
        return (ni/nT)*P

    def _design(self):
        feed, regeneration_fluid, adsorbent = self.ins
        design = self.design_results
        
        # Parameters
        q_ads = self._q_ads
        q_regen = self._q_regen
        q_work = self._q_work

        n_columns = self.N_columns
        
        M_ads_col = self._M_ads
        rho_bulk = self.rho_adsorbent
        u_superficial = self.u_superficial
        eps_bed = self.void_fraction
        f_L = self.f_L
        dp = self.particle_diameter

        gas_viscosity = self.gas_viscosity
        gas_density = self.gas_density

        # Adsorbate concentration
        Q_feed = feed.F_vol / 3600
        C_ads = feed.imol[self.adsorbate] / Q_feed

        # Column length
        L_col = estimate_bed_length_sinnott(
            C_ads = C_ads,
            u = u_superficial,
            t_ads = self.t_ads,
            rho_adsorbent = rho_bulk,
            f_L = f_L,
            q_ads = q_ads,
            q_regen = q_regen,
        )

        # Bed volume per column
        V_bed_col = M_ads_col / rho_bulk

        # Area and diameter
        A_col = Q_feed / u_superficial
        D_col = math.sqrt(4.0 * A_col / math.pi)

        # Calculate pressure drop
        dP, dP_L = ergun_pressure_drop(
            dp = dp,
            rho = gas_density,
            mu = gas_viscosity,
            epsilon = eps_bed,
            u = u_superficial,
            L = L_col,
        )
        
        # Pressure vessel design
        if self.P_regen >= self.P_ads:
            vessel_pressure = self.P_regen
        else:
            vessel_pressure = self.P_ads

        
        self._design_and_cost_pressure_vessel(
            pressure = vessel_pressure,
            diameter = D_col,
            length = L_col,
            pressure_units = 'Pa',
            length_units = 'm',
            n_vessels = n_columns
        )

        # Results
        design["Adsorbent per column"] = M_ads_col
        design["Number of columns"] = n_columns
        design["Total adsorbent"] = M_ads_col * n_columns
        design[f"Working capacity (kg {self.adsorbate} / kg adsorbent)"] = q_work * self.adsorbate_MW / 1000
        design["Cycle time"] = self._t_cycle


    def _cost(self):
        