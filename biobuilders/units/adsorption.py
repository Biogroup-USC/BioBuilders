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
[8] D. W. Green and R. H. Perry, Eds., Perry’s Chemical Engineers’ Handbook, 8th ed. New York, NY, USA: McGraw-Hill, 2008, sec. 2, pp. 2-1 2-151.
[9] M. S. Peters, K. D. Timmerhaus, and R. E. West, Plant Design and Economics for Chemical Engineers, 5th ed. New York, NY, USA: McGraw-Hill, 2004, ch. 6, “Cost Estimation and Capital Investment.”

"""

import biosteam as bst
from biosteam.units.design_tools import PressureVessel
from numba import njit
import math
from warnings import warn
from ..tools.mathtools import calculate_packing_equivalent_diameter

__all__ = (
    "GasAdsorptionColumn",
)

@njit(cache=True)
def equilibrium_loading_Langmuir_isotherm_gas(
    pi,     # Partial pressure [Pa]
    Kp,     # Adsorption equilibrium constant [1/Pa]
    q_max,  # Maximum equilibrium loading [mol/kg]
):
    return pi * Kp * q_max / (1 + Kp * pi)  # mol/kg

# langmuir-langmuir isotherm from paper [6]
@njit(cache=True)
def equilibrium_loading_Langmuir_dual_site_isotherm_gas(
    pi,     # Adsorbate partial pressure [Pa] 
    ka,     # Adsorption equilibrium constant for cage alpha [1/Pa]
    a_term, # Alpha term
    kb,     # Adsorption equilibrium constant for cage beta [1/Pa]
    b_term, # Beta term
    q_max,  # Maximum equilibrium loading [mol/kg]
):
    first_term = a_term * q_max * (kb * pi) / (1 + kb * pi)
    second_term = b_term * q_max * (ka * pi) / (1 + ka * pi)
    return first_term + second_term

# Pressure drop determination [7]
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

class GasAdsorptionColumn(PressureVessel, bst.Unit):    #TODO Add PSA and the same calculation as TSA
    """
    """ 
    auxiliary_unit_names = (
        'feed_heater',
        'regen_gas_heater',
    )

    _N_ins = 3
    _N_outs = 3

    _units = {
        'Vessel length': 'm',
        'Vessel diameter': 'm',
        'Vessel weight': 'kg',
        'Vessel wall thickness': 'mm',
        'Adsorbent per column': 'kg adsorbent',
        'Total adsorbent': 'kg adsorbent',
        'Working capacity': 'kg adsorbate/kg adsorbent',
        'Cycle time': 'h',
        'Bed volume per column': 'm3',
        'Bed length per column': 'm',
        'Superficial gas velocity': 'm/s',
        'Pressure drop per bed length': 'Pa/m',
        'Pressure drop': 'Pa',
        'Pressure': 'Pa',
        **PressureVessel._units,  
    }

    # Default lifetime for component
    _default_equipment_lifetime = {
        'Zeolite 3A': 3,    # years [6]
    }

    # Cost of regeneration $/kg
    adsorbent_cost = {
        'Zeolite 3A': (1.5+6.5)/2   # https://spanish.alibaba.com/g/zeolite-cost-per-kg.html
    }

    # Adsorbent properties
    adsorbent_properties = {
        'Zeolite 3A': {                     
            'void fraction': 0.30,                                  # - [3]
            'specific surface area': 0.7 * 10**6 / ((620 + 680)/2), # m2/m3 [3]
            'bulk density': (620 + 680)/2,                          # kg/m3 [3]
            'temperature limit': 300.+273.15,                       # K [2]
            'specific heat': 0.74                                   # kJ / kg * K (300 K) [8]
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
        T_ads = None,
        T_regen = None,
        T_limit = None,
        regeneration_fluid = None,
        adsorbate = None,
        vessel_material = 'Stainless steel 316',
        vessel_type = 'Vertical',
        adsorbent: str = None,
        isosteric_heat: float = -45.95,
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

        if particle_diameter is None:
            if adsorbent in self.adsorbent_properties:
                epsilon = self.adsorbent_properties[adsorbent]['void fraction']
                specific_surface_area = self.adsorbent_properties[adsorbent]['specific surface area']
                particle_diameter = calculate_packing_equivalent_diameter(epsilon,specific_surface_area)

        if T_limit is None:
            if adsorbent in self.adsorbent_properties:
                T_limit = self.adsorbent_properties[adsorbent]['temperature limit']

        self.t_ads = t_ads
        self.t_regen = t_regen
        self.P_ads = P_ads
        self.P_regen = P_regen
        self.T_ads = T_ads
        self.T_regen = T_regen
        self.T_limit = T_limit

        self.adsorbate = adsorbate
        self.adsorbed_fraction = adsorbed_fraction
        
        self.adsorbent = adsorbent
        self.void_fraction = void_fraction
        self.rho_adsorbent = rho_adsorbent
        self.particle_diameter = particle_diameter
        self.f_L = f_L

        self.regeneration_fluid = regeneration_fluid
        self.isosteric_heat = isosteric_heat

        key = isotherm_model.lower()
        if key not in self.isotherm_models:
            raise ValueError(
                f"isotherm_model must be one of {tuple(self.isotherm_models)}"
            )
        self.isotherm_model = self.isotherm_models[key]
        self.isotherm_args = list(isotherm_args or ())
        
        if regeneration_isotherm_model is None:
            self.regeneration_isotherm_model = None
            self.regeneration_isotherm_args = []
        else:
            rkey = regeneration_isotherm_model.lower()
            if rkey not in self.isotherm_models:
                raise ValueError(
                    f"regeneration_isotherm_model must be one of {tuple(self.isotherm_models)}"
                )
            
            self.regeneration_isotherm_model = self.isotherm_models[regeneration_isotherm_model.lower()]
            self.regeneration_isotherm_args = list(regeneration_isotherm_args)

        self.N_columns = N_columns
        self.vessel_material = vessel_material
        self.vessel_type = vessel_type

        self.load_auxiliaries()

        self._adsorbate_chemical = None
        self._regeneration = None
        self._fraction_inert_packed = None
        self._L_D_ratio = None

        self._base_cost_vessel = None
        self._base_n_cost_vessel = None
        self._base_adsorbent_mass = None
        self._base_CE = None

    def load_auxiliaries(self):
        self.feed_heater = self.auxiliary(
            'feed_heater',
            bst.HXutility,
            ins = self.ins[0]
        )
        if self.regeneration:
            self.regen_gas_heater = self.auxiliary(
                'regen_gas_heater',
                bst.HXutility,
                ins = self.ins[1]
            )

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

    @property
    def L_D_ratio(self):
        if self._L_D_ratio is None:
            self._L_D_ratio = 3.    # - [1]
        return self._L_D_ratio
    
    @L_D_ratio.setter
    def L_D_ratio(self,value):
        self._L_D_ratio = value

    def _calculate_bed_geometry_and_pressure_drop(self, feed, M_ads_col):
        rho_bulk = self.rho_adsorbent
        eps = self.void_fraction
        dp = self.particle_diameter

        Q_feed = feed.F_vol / 3600
        if Q_feed <= 0.:
            raise ValueError("Feed volumetric flow must be > 0")
        
        # Bed volume from adsorbent
        V_bed_col = M_ads_col / rho_bulk
        
        # Geometric design [1]
        L_D_ratio = self.L_D_ratio
        D_col = (4. * V_bed_col / (math.pi * L_D_ratio))**(1./3.)
        L_bed = L_D_ratio * D_col
        A_col = math.pi * D_col**2 / 4.0

        # Superficial velocity
        u = Q_feed / A_col

        # Extra length for inert/distributors: tangent-to-tangent length
        L_vessel_tt = L_bed / (1 - self.fraction_inert_packed)

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

        return {
            'Volumetric flow': Q_feed,
            'Bed volume': V_bed_col,
            'Bed length': L_bed,
            'Column area': A_col,
            'Column diameter': D_col,
            'Column length': L_vessel_tt,
            'Superficial velocity': u,
            'Pressure drop': dP,
            'Pressure drop per length': dP_L,
        }

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

        heat_feed = feed.F_mass * feed.Cp * (self.T_ads - feed.T)

        # Outlet adsorbate
        na_out = (1-self.adsorbed_fraction) * na_in
        na_out = min(max(na_out,0.),na_in)

        # Adsorbate removed during adsorption
        na_removed_rate = max(na_in - na_out, 0.0)

        # Adsorbate removed per column
        na_removed_ads_step = na_removed_rate * self.t_ads

        # Adsorption conditions
        P_in = self.P_ads if self.P_ads is not None else feed.P
        pa = self._calculate_pi(na_in, feed_in, P_in)
        q_ads = self.isotherm_model(pa, *self.isotherm_args)

        # Regeneration
        if self.regeneration:
            P_regen = self.P_regen if self.P_regen is not None else regeneration_fluid.P

            regen_in = regeneration_fluid.F_mol
            na_regen = regeneration_fluid.imol[adsorbate]
            pa_regen = self._calculate_pi(na_regen, regen_in, P_regen)
            q_regen = self.regeneration_isotherm_model(pa_regen, *self.regeneration_isotherm_args)

            spent_fluid.copy_like(regeneration_fluid)
            spent_fluid.P = P_regen
            spent_fluid.T = self.T_regen
            
            spent_fluid.imol[adsorbate] += na_removed_rate
        else:
            P_regen = P_in
            q_regen = 0.

            spent_adsorbent.imol[adsorbate] = na_removed_ads_step / t_cycle
        
        q_work = max((q_ads - q_regen) * self.f_L, 1e-12)
        q_work_kmol = q_work / 1000

        # Adsorbent mass per column
        mass_adsorbent = na_removed_ads_step / q_work_kmol
        column_results = self._calculate_bed_geometry_and_pressure_drop(feed,mass_adsorbent)

        # Outlet stream
        P_out = P_in - column_results['Pressure drop']
        if P_out <= 0.:
            raise ValueError("Outlet P must be > 0.")

        outlet.P = P_out
        outlet.T = self.T_ads
        outlet.imol[adsorbate] = na_out

        # Variables considered in _design
        self._M_ads = mass_adsorbent
        self._q_work = q_work
        self._q_work_kmol = q_work_kmol
        self._nAds_removed_ads_step = na_removed_ads_step
        self._q_ads = q_ads
        self._q_regen = q_regen
        self._t_cycle = t_cycle
        self._Q_feed = column_results['Volumetric flow']
        self._superficial_velocity = column_results['Superficial velocity']
        self._V_bed_col = column_results['Bed volume']
        self._A_col = column_results['Column area']
        self._D_col = column_results['Column diameter']
        self._L_bed = column_results['Bed length']
        self._L_vessel_tt = column_results['Column length']
        self._dP = column_results['Pressure drop']
        self._dP_per_length = column_results['Pressure drop per length']

        # Utilities
        ## Feed conditioning duty
        self.feed_heater.simulate(
            run=False,
            design_kwargs=dict(duty=heat_feed)
        )
        
        ## Bed regeneration
        if self.regeneration:
            flow_gas = regeneration_fluid.F_mass
            Cp_gas = regeneration_fluid.Cp     
            
            heat_desorption = na_removed_ads_step * 1000 * abs(self.isosteric_heat) / self.t_regen
            heat_adsorbent = mass_adsorbent/self.t_regen * self.adsorbent_properties[self.adsorbent]['specific heat'] * (self.T_regen - self.T_ads)
            heat_required = heat_desorption + heat_adsorbent
            
            T_in = self.T_regen - heat_required / (flow_gas * Cp_gas)
            heat_gas_heater = flow_gas * Cp_gas * (T_in - regeneration_fluid.T)

            self.regen_gas_heater.simulate(
                run=False,
                design_kwargs=dict(duty=heat_gas_heater)
            )

            if T_in > self.T_limit:
                warn(
                    f"Temperature of regeneration gas is above the maximum temperature of '{self.adsorbent}'. T_in: {T_in:.2f} | T_limit: {self.T_limit:.2f}"
                )

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
        
        P_ads = self.P_ads if self.P_ads is not None else self.ins[0].P
        if self.regeneration:
            P_regen = self.P_regen if self.P_regen is not None else self.ins[1].P
        else:
            P_regen = P_ads

        vessel_pressure = max(max(P_ads, P_regen) - 101325, 0.)

        self._design_and_cost_pressure_vessel(
            pressure=vessel_pressure,
            diameter=self._D_col,
            length=self._L_vessel_tt,
            pressure_units='Pa',
            length_units='m',
            n_vessels=self.N_columns
        )

        # L/D check
        length_diameter = self._L_bed / self._D_col
        if not 2.5 <= length_diameter <= 3.5:
            warn(
                f"Bed length / diameter ratio is outside the target range [2.5, 3.5]. Current: {length_diameter}"
            )

        # Bed related results
        design["Vessel length"] = design.pop("Length") * 0.3048
        design["Vessel diameter"] = design.pop("Diameter") * 0.3048
        design["Vessel weight"] = design.pop("Weight") * 0.4536
        design["Vessel wall thickness"] = design.pop("Wall thickness") * 25.4
        design["length / diameter ratio"] = length_diameter
        design["Number of columns"] = self.N_columns
        
        design["Adsorbent per column"] = self._M_ads
        design["Total adsorbent"] = self._M_ads * self.N_columns
        design["Working capacity"] = self._q_work * self.adsorbate_MW / 1000
        design["Cycle time"] = self._t_cycle
        
        design["Bed volume per column"] = self._V_bed_col
        design["Bed length per column"] = self._L_bed
        design["Superfical gas velocity"] = self._superficial_velocity

        design["Pressure drop per bed length"] = self._dP_per_length
        design["Pressure drop"] = self._dP

    @property
    def base_cost_vessel(self):
        if self._base_cost_vessel is None:
            self._base_cost_vessel = 235000     # $ [4]
        return self._base_cost_vessel

    @base_cost_vessel.setter
    def base_cost_vessel(self,value):
        self._base_cost_vessel = value

    @property
    def base_n_cost_vessel(self):
        if self._base_n_cost_vessel is None:
            self._base_n_cost_vessel = 0.51     # $ [4]
        return self._base_n_cost_vessel
    
    @base_n_cost_vessel.setter
    def base_n_cost_vessel(self,value):
        self._base_n_cost_vessel = value

    @property
    def base_adsorbent_mass(self):
        if self._base_adsorbent_mass is None:
            self._base_adsorbent_mass = 2200    # kg [4]
        return self._base_adsorbent_mass

    @base_adsorbent_mass.setter
    def base_adsorbent_mass(self,value):
        self._base_adsorbent_mass = value

    @property
    def base_CE(self):
        if self._base_CE is None:
            self._base_CE = 1000                # - [4]
        return self._base_CE

    @base_CE.setter
    def base_CE(self,value):
        self._base_CE = value

    def _cost(self):
        baseline_purchase_costs = self.baseline_purchase_costs
        
        # Adsorbent cost
        total_ads = self.design_results["Total adsorbent"]
        adsorbent_cost_per_kg = self.adsorbent_cost[self.adsorbent]
        baseline_purchase_costs['Adsorbent initial charge'] = adsorbent_cost_per_kg * total_ads
        if self.regeneration:
            lifetime = self._default_equipment_lifetime[self.adsorbent]
            self.equipment_lifetime['Adsorbent initial charge'] = lifetime

        # Equipment
        vessel = f"{self.vessel_type} pressure vessel x{self.N_columns}"
        adsorbent_mass = self.design_results['Adsorbent per column']
        vessel_purchase_cost = self.base_cost_vessel * (adsorbent_mass/self.base_adsorbent_mass)**self.base_n_cost_vessel
        baseline_purchase_costs[vessel] = vessel_purchase_cost

        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D[vessel] = self.F_M[vessel] = self.F_P[vessel] = 1

        ## Bare module
        delivery = 0.10                 # - [9]
        installation = 0.90             # Metal tanks [9]
        instrumentation_Control = 0.50  # - [9]
        piping = 0.68                   # Fluid [9]   

        bare_module = (1 + (delivery + installation + instrumentation_Control + piping))
        self.F_BM[vessel] = bare_module

        ## Scale costs using CEPCI
        base_CE = self.base_CE
        baseline_purchase_costs[vessel] *= bst.CE/base_CE