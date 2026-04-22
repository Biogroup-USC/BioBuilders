"""

References
----------
[1] R. K. Sinnott and G. Towler, “Gas gas separation,” in Chemical Engineering Design, 6th ed. Oxford, U.K.: Elsevier, 2020, p. 531.
[2] D. R. Woods, “Adsorption: Gas,” in Rules of Thumb in Engineering Practice, ch. 4, “Homogeneous Separation,” Weinheim, Germany: Wiley-VCH, 2007, sec. 4.11, p. 118.
[3] M. D. LeVan and G. Carta, “Adsorption and ion exchange,” in Perrys Chemical Engineers Handbook, 8th ed., D. W. Green and R. H. Perry, Eds. New York, NY, USA: McGraw-Hill, 2008, sec. 16.
[4] D. R. Woods, “Adsorption: Gas,” in Rules of Thumb in Engineering Practice, Appendix D, “Homogeneous Separation,” sec. 4.11, p. 399. Weinheim, Germany: Wiley-VCH, 2007.
[5] P. Azhagapillai, M. Khaleel, F. Zoghieb, G. Luckachan, L. Jacob, and D. Reinalda, “Water vapor adsorption capacity loss of molecular sieves 4A, 5A, and 13X resulting from methanol and heptane exposure,” ACS Omega, vol. 7, no. 8, pp. 6463 6471, 2022, doi: 10.1021/acsomega.1c03370.
[6] E. Gabruś, J. Nastaj, P. Tabero, and T. Aleksandrzak, “Experimental studies on 3A and 4A zeolite molecular sieves regeneration in TSA process: Aliphatic alcohols dewatering water desorption,” Chemical Engineering Journal, vol. 259, pp. 232 242, 2015, doi: 10.1016/j.cej.2014.07.108.
[7] R. K. Sinnott and G. Towler, Chemical Engineering Design, 6th ed. Oxford, U.K.: Elsevier, 2020, p. 1076.
[8] C. S. Ana et al., “Experimental analysis of adsorption dynamics in fixed-bed columns under varying superficial velocities,” Fusion Engineering and Design, 2025, doi: 10.1016/j.fusengdes.2025.115039.

"""

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

# [6]
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

# [1]
@njit(cache=True)
def estimate_bed_length_sinnott(
    C_ads,          # mol/m3
    u,              # m/s
    t_ads,          # s
    rho_adsorbent,  # kg/m3
    f_L,            # bed usage fraction
    q_ads,          # mol/kg
    q_regen,        # mol/kg
):
    q_work = (q_ads - q_regen) * rho_adsorbent
    length = C_ads * u * t_ads / (q_work * f_L)
    return length

# [7]
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
        'Zeolite 3A': 3,    # years [6]
    }

    # default gas velocity
    default_gas_velocity = (0.20+1.32)/2  # m/s [8]

    # Cost of regeneration $/m3
    absorbent_cost = {

    }

    # Adsorbent properties
    adsorbent_properties = {
        'Zeolite 3A': {                     
            'void fraction': 0.30,                      # -     [3]
            'bulk density': (620 + 680)/2,              # kg/m3 [3]
            'temperature limit': 300.,                  # ºC    [2]
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

        if adsorbate is None or not isinstance(adsorbate, str):
            raise ValueError('An adsorbate must be specified as a string')
        
        if adsorbent is None or not isinstance(adsorbent, str):
            raise ValueError('An adsorbent must be specified as a string')

        if isotherm_model is None:
            raise ValueError("isotherm_model must be specified")

        if rho_adsorbent is None:
            if adsorbent in self.adsorbent_properties:
                rho_adsorbent = self.adsorbent_properties[adsorbent]['bulk density']
            else:
                raise ValueError(
                    f"rho_adsorbent must be provided for adsorbent '{adsorbent}'"
                )
            
        if void_fraction is None:
            if adsorbent in self.adsorbent_properties:
                void_fraction = self.adsorbent_properties[adsorbent]['void fraction']
            else:
                raise ValueError(
                    f"void_fraction must be provided for adsorbent '{adsorbent}'"
                )
        
        if u_superficial is None:
            u_superficial = self.default_gas_velocity

        # Auxiliary equipment
        self.auxiliary('pump', bst.Pump, ins = self.ins[0])

        if regeneration_fluid is not None:
            regeneration_pump = self.auxiliary(
                'regeneration_pump', bst.Pump, ins = self.ins[1]
            )
            self.auxiliary(
                'heat_exchanger', bst.HXutility, ins = regeneration_pump.outs[0]
            )

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

        key = isotherm_model.lower()
        if key not in self.isotherm_models:
            raise ValueError(
                f"isotherm_model must be one of {tuple(self.isotherm_models)}"
            )
        self.isotherm_model = self.isotherm_models[key]
        self.isotherm_args = isotherm_args or ()
        
        if regeneration_isotherm_model is None:
            self.regeneration_isotherm_model = None
            self.regeneration_isotherm_args = ()
        else:
            rkey = regeneration_isotherm_model.lower()
            if rkey not in self.isotherm_models:
                raise ValueError(
                    f"regeneration_isotherm_model must be one of {tuple(self.isotherm_models)}"
                )
            
            self.regeneration_isotherm_model = self.isotherm_models[regeneration_isotherm_model.lower()]
            self.regeneration_isotherm_args = regeneration_isotherm_args

        self.particle_diameter = particle_diameter
        self.N_columns = N_columns
        self.vessel_material = vessel_material
        self.vessel_type = vessel_type

        self._adsorbate_chemical = None
        self._regeneration = None
        self._fraction_inert_packed = None

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

    def _calculate_bed_geometry_and_pressure_drop(self, feed, M_ads_col):
        rho_bulk = self.rho_adsorbent
        u = self.u_superficial
        eps = self.void_fraction
        dp = self.particle_diameter

        Q_feed = feed.F_vol / 3600
        if Q_feed <= 0.:
            raise ValueError("Feed volumetric flow must be > 0")
        
        V_bed_col = M_ads_col / rho_bulk
        A_col = Q_feed / u
        D_col = math.sqrt(4.0 * A_col / math.pi)
        L_bed = V_bed_col / A_col

        # Extra length for inert/distributors: tangent-to-tangent length
        L_vessel_tt = L_bed / (1-self.fraction_inert_packed)

        gas_rho = feed.rho
        gas_mu = feed.mu

        dP, dP_L = ergun_pressure_drop(
            dp=dp,
            rho=gas_rho,
            mu=gas_mu,
            epsilon=eps,
            u=u,
            L=L_bed
        )

        return Q_feed, V_bed_col, A_col, D_col, L_bed, L_vessel_tt, dP, dP_L

    def _run(self):
        feed, regeneration_fluid, adsorbent = self.ins
        outlet, spent_fluid, spent_adsorbent = self.outs
        
        adsorbate = self.adsorbate
        t_regen = self.t_regen if self.t_regen is not None else 0.
        t_cycle = t_regen + self.t_ads

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
        P_in = self.P_ads if self.P_ads is not None else feed.P
        pa = self._calculate_pi(na_in, feed_in, P_in)
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
        Q_feed,V_bed_col,A_col,D_col,L_bed,L_vessel_tt,dP,dP_L = self._calculate_bed_geometry_and_pressure_drop(feed,mass_adsorbent)

        # Outlet stream
        P_out = P_in - dP
        if P_out <= 0.:
            raise ValueError("Outlet P must be > 0.")

        outlet.P = P_out
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
        self._Q_feed = Q_feed
        self._V_bed_col = V_bed_col
        self._A_col = A_col
        self._D_col = D_col
        self._L_bed = L_bed
        self._L_vessel_tt = L_vessel_tt
        self._dP_bed = dP
        self._dP_per_length = dP_L

    @staticmethod
    def _calculate_pi(ni, nT, P):
        if nT <= 0.0:
            return 0.0
        return (ni/nT)*P

    @property
    def fraction_inert_packed(self):
        if self._fraction_inert_packed is None:
            self._fraction_inert_packed = 0.20  # - [1]
        return self._fraction_inert_packed
    
    @fraction_inert_packed.setter
    def fraction_inert_packed(self,value):
        self._fraction_inert_packed = value

    def _design(self):
        design = self.design_results
        
        vessel_pressure = max(self.P_ads, self.P_regen)
        self._design_and_cost_pressure_vessel(
            pressure=vessel_pressure,
            diameter=self._D_col,
            length=self._L_vessel_tt,
            pressure_units='Pa',
            length_units='m',
            n_vessels=self.N_columns
        )

        # Bed related results
        design["Adsorbent per column"] = self._M_ads
        design["Number of columns"] = self.N_columns
        design["Total adsorbent"] = self._M_ads * self.N_columns
        design["Bed volume per column"] = self._V_bed_col
        design["Bed length per column"] = self._L_bed
        design["Pressure drop per bed length"] = self._dP_per_length
        design["Pressure drop per column"] = self._dP_bed
        design[f"Working capacity (kg {self.adsorbate} / kg adsorbent)"] = self._q_work * self.adsorbate_MW / 1000
        design["Cycle time"] = self._t_cycle

        # Vessel related to convert imperial units to SI units
        design["Vessel Length"] = design.pop("Length") * 0.3048
        design["Vessel Diameter"] = design.pop("Diameter") * 0.3048
        design["Vessel Weight"] = design.pop("Weight") * 0.4536
        design["Vessel Wall thickness"] = design.pop("Wall thickness") * 25.4

    def _cost(self):
        