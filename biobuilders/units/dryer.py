"""
"""
import biosteam as bst
import flexsolve as flx
import numpy as np 
from thermosteam import separations as sep
from .boiler import NaturalGasBoiler

__all__ = (
    "SprayDryer", "DrumDryer"
)

class SprayDryer(bst.Unit):
    """
    Create a spray dryer for drying solids.

    This class simulates a dryer, accounting for its evaporation capacity, design and cost.
    The mass balance uses the moisture content in flows to equal input and ouputs.

    Parameters
    ----------
    ID: str
        Name of the unit operation.

    ins: tuple
        List of input streams:
        * [0] solid flow with high humidity
    
    outs: tuple
        List of output streams:
        * [0] dryed solids
        * [1] evaporated water

    Attributes
    ----------
    moisture_content: float
        Humidity content of the flow (fraction)
    """

    _N_ins = 2
    _ins_size_is_fixed = False
    _N_outs = 2
    _outs_size_is_fixed = False
    
    auxiliary_unit_names = (
        'air_heater',
    )

    _units = {
        "Evaporation rate": "kg/s",
        "Residence time": "s",
        "Gas volumetric flow": "m3/s",
        "Volume": "m3",
        "Diameter": "m",
        "Height": "m",
    }

    def _init(self,
        moisture_content = 0.10,
        moisture_ID: str = "Water",
        split: dict = None,
        dryer_efficiency = 0.80,    # From Piccinno et al. (2016)
        RH: float = 0.50,
        T: float = 273.15 + 70,
        P: float = 101325,
        residence_time: float = 30,
        gas_composition: dict = None,
        utility_agent: str = 'natural_gas',
        peripheral_velocity: float = 161,
    ):
        self. moisture_content = moisture_content
        self.moisture_ID = moisture_ID
        self._isplit = self.chemicals.isplit(split or {})
        self.dryer_efficiency = dryer_efficiency
        self.RH = RH
        self.T = T
        self.P = P
        self.residence_time = residence_time
        self.gas_composition = gas_composition
        self.utility_agent = utility_agent
        self.peripheral_velocity = peripheral_velocity

        if utility_agent == 'natural_gas':
            self._load_auxiliaries()

        self._base_cost = None
        self._base_evaporation_capacity = None
        self._base_n_cost = None
        self._CE_base = None

    def _load_auxiliaries(self):
        self.air_heater = self.auxiliary(
            'air_heater',
            NaturalGasBoiler,
            ins = (
                'natural_gas',
                'combustion_air',
                self.ins[1]
            ),
        )

    def _get_moisture_vapor_pressure(self, T):
        chemical = self.thermo.chemicals[self.moisture_ID]
        return chemical.Psat(T)

    @property
    def isplit(self):
        """Componentwise split indexer to wet gas."""
        return self._isplit
    
    @property
    def split(self):
        """Componentwise split array to wet gas."""
        return self._isplit.data

    def _run(self):
        """
        """
        design = self.design_results
        # Define the streams
        feed = self.ins[0]
        gas = self.ins[1]

        dryed = self.outs[0]
        wet_gas = self.outs[1]
        
        dryed.empty()
        wet_gas.empty()

        # Adjust final moisture
        feed.split_to(wet_gas, dryed, self.split)
        sep.adjust_moisture_content(dryed, wet_gas, self.moisture_content, self.moisture_ID)
        design['Evaporation rate'] = wet_gas.imass[self.moisture_ID]/3600

        # Calculate moisture ID vapor molar fraction in outlet gas
        Psat = self._get_moisture_vapor_pressure(self.T)
        P = self.P

        y_moisture = self.RH * Psat / P
        if y_moisture <= 0:
            raise ValueError("Calculated outlet moisture molar fraction is zero or negative.")

        if y_moisture >= 1:
            raise ValueError(
                "Outlet gas is pure moisture or above saturation. "
                "Increase pressure, reduce RH, or reduce operating temperature."
            )
        
        # Required dry gas molar flow
        n_other = wet_gas.imol[self.moisture_ID]
        n_dry_gas = n_other * (1 - y_moisture) / y_moisture

        if not self.gas_composition:
            gas_composition = {"O2": 0.21, "N2": 0.79}
        else:
            gas_composition = self.gas_composition

        # molar gas flow
        gas.reset_flow(**dict(gas_composition), units='kmol/hr',total_flow=n_dry_gas)
        wet_gas.mol += gas.mol
        
        # Temperature and pressure
        dryed.T = wet_gas.T = self.T
        dryed.P = wet_gas.P = self.P
        dryed.phase = 's'
        wet_gas.phase = gas.phase = 'g'

    def _design(self):
        feed = self.ins[0]
        gas = self.ins[1]

        dryed = self.outs[0]
        wet_gas = self.outs[1]

        design = self.design_results

        # Heating utilities
        Q = wet_gas.H + dryed.H - feed.H - gas.H
        Q = Q / self.dryer_efficiency

        design["Dryer efficiency"] = self.dryer_efficiency

        if self.utility_agent != 'natural_gas':
            utility_agent = bst.settings.get_heating_agent(self.utility_agent)
            self.add_heat_utility(Q, T_in = gas.T, agent = utility_agent)
        else:
            # Simulate auxiliary to heat air    
            T_hot_gas = gas.T + Q / (gas.F_mass * gas.Cp)
            self.air_heater.hot_fluid_T = T_hot_gas
            self.air_heater.hot_fluid_P = gas.P
            self.air_heater.simulate()

            self.ins[2].copy_like(self.air_heater.ins[0])
            self.ins[3].copy_like(self.air_heater.ins[1])
            
            self.outs[2].copy_like(self.air_heater.outs[0])

        # Power utilities
        if self.peripheral_velocity is not None:
            U = self.peripheral_velocity # m/s
            
            # Specific atomizer power
            Ps = U**2 / 3600    # kWh/t feed

            feed_tph = feed.F_mass / 1000   # t/h
            atomizer_power = Ps * feed_tph  # kW

            design["Atomizer specific power"] = Ps
            
            self.add_power_utility(atomizer_power)
        
        # chamber volume
        tau = self.residence_time

        gas_vol_flow = wet_gas.F_vol / 3600
        volume = gas_vol_flow * tau

        diameter = (volume / 1.47) ** (1/3)
        height = diameter

        design["Residence time"] = tau
        design["Gas volumetric flow"] = gas_vol_flow
        design["Volume"] = volume
        design["Diameter"] = diameter
        design["Height"] = height

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 2000000 # USD from: Rules of Thumb
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_evaporation_capacity(self):
        """
        """
        if self._base_evaporation_capacity is None:
            self._base_evaporation_capacity = 1 # kg/s from: Rules of Thumb
        return self._base_evaporation_capacity
    
    @base_evaporation_capacity.setter
    def base_evaporation_capacity(self, value):
        """
        """
        self._base_evaporation_capacity = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.42 # From: Rules of Thumb
        return self._base_n_cost
    
    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value
    
    @property
    def CE_base(self):
        if self._CE_base is None:
            self._CE_base = 1000
        return self._CE_base
    
    @CE_base.setter
    def CE_base(self, value):
        """
        """
        self._CE_base = value
    
    def _cost(self):
        """
        """
        # Load all the design parameters needed
        evaporation_rate = self.design_results['Evaporation rate']

        # Calculate the design cost for the spray dryer: Including instrumentation, pressure nozzle atomization, residence time about 16 s,
        # access platform, support steel, air preheater, feed system, fan, motor and drive and dust collectors. Tin = 150ºC and Tout = 75ºC
        purchase_cost = self.base_cost * (evaporation_rate/self.base_evaporation_capacity) ** self.base_n_cost
        self.baseline_purchase_costs['Spray Dryer'] = purchase_cost

        # The material, pressure and temperature factor are assumed to be 1
        self.F_D['Spray Dryer'] = self.F_M['Spray Dryer'] = self.F_P['Spray Dryer'] = 1

        # The bare module factor which account for installation cost is calculated as the sum of delivery, installation, piping, instrumentation and controls
        delivery = 0.10
        installation = 0.60 # Dryer
        instrumentation_Control = 0.50
        piping = 0.31 # Solid-fluid

        # Calculate the bare module with percentages from Peters: Plant Design and Economics for Chemical Engineers
        bare_module = (1 + (delivery + installation +  instrumentation_Control + piping))
        self.F_BM['Spray Dryer'] = bare_module

        # Scale the cost using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Spray Dryer'] *= bst.CE/CE_base


# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class DrumDryer(bst.Unit):
    """
    Create a drum dryer that dries solids by passing hot air 
    (heated by burning natural gas).
    
    Parameters
    ----------
    ins : 
        * [0] Wet solids.
        * [1] Dry gas.
        * [2] Natural gas.
    outs : 
        * [0] Dried solids
        * [1] Hot gas
        * [2] Emissions
    split : dict[str, float]
        Component splits to hot gas (stream [1]).
    RH : float, optional
        Relative humidity of hot gas [as fraction]. Defaults to 0.80.
    H : float, optional
        Specific evaporation rate [kg/hr/m3]. Defaults to 20. 
    length_to_diameter : float, optional
        Note that the drum is horizontal. Defaults to 25.
    T : float, optional
        Operating temperature [K]. Defaults to 343.15.
    moisture_content : float
        Moisture content of solids [wt / wt]. Defaults to 0.10.
        
    Notes
    -----
    The flow rate for gas in the inlet is calculated to meet the `RH` specification
    (i.e. relative humidity of hot gas depending on moisture_ID evaporated). The flow 
    rate of inlet natural gas is also altered to meet the heat demand.
    
    The default parameter values are based on heuristics for drying 
    dried distillers grains with solubles (DDGS).
    
    Examples
    --------
    >>> import biosteam as bst
    >>> from biorefineries import corn as c
    >>> bst.settings.set_thermo(c.create_chemicals())
    >>> feed = bst.Stream('feed', phase='l', T=352.33, P=101325,
    ...     Water=0.6749, Ethanol=5.041e-06, Ash=0.01978, Yeast=0.008452, 
    ...     CaO=0.0001446, TriOlein=0.02702, H2SO4=0.001205, Fiber=0.1508, 
    ...     SolubleProtein=0.04805, InsolubleProtein=0.06967, 
    ...     total_flow=32720, units='kg/hr',
    ... )
    >>> dryer = bst.DrumDryer('D610', 
    ...     (feed, 'dryer_air', 'natural_gas'), 
    ...     ('dryed_solids', 'hot_air', 'emissions'),
    ...     moisture_content=0.10, split=dict(Ethanol=1.0)
    ... )
    >>> dryer.simulate()
    >>> dryer.show('cwt100')
    DrumDryer: D610
    ins...
    [0] feed
        phase: 'l', T: 352.33 K, P: 101325 Pa
        composition (%): Water             67.5
                         Ethanol           0.000504
                         Ash               1.98
                         Yeast             0.845
                         CaO               0.0145
                         TriOlein          2.7
                         H2SO4             0.12
                         Fiber             15.1
                         SolubleProtein    4.8
                         InsolubleProtein  6.97
                         ----------------  3.27e+04 kg/hr
    [1] dryer_air
        phase: 'g', T: 298.15 K, P: 1.01325e+06 Pa
        composition (%): O2  21
                         N2  79
                         --  1.32e+06 kg/hr
    [2] natural_gas
        phase: 'g', T: 298.15 K, P: 101325 Pa
        composition (%): CH4  100
                         ---  2.45e+03 kg/hr
    outs...
    [0] dryed_solids
        phase: 'l', T: 343.15 K, P: 101325 Pa
        composition (%): Water             10
                         Ash               5.48
                         Yeast             2.34
                         CaO               0.04
                         TriOlein          7.48
                         H2SO4             0.334
                         Fiber             41.7
                         SolubleProtein    13.3
                         InsolubleProtein  19.3
                         ----------------  1.18e+04 kg/hr
    [1] hot_air
        phase: 'g', T: 343.15 K, P: 1.01325e+06 Pa
        composition (%): Water    1.56
                         Ethanol  1.23e-05
                         O2       20.7
                         N2       77.8
                         -------  1.34e+06 kg/hr
    [2] emissions
        phase: 'g', T: 373.15 K, P: 101325 Pa
        composition (%): Water  45
                         CO2    55
                         -----  1.22e+04 kg/hr
                        
    >>> dryer.results()
    Drum dryer                                 Units     D610
    Electricity         Power                     kW      845
                        Cost                  USD/hr       66
    Natural gas (inlet) Flow                   kg/hr 2.45e+03
                        Cost                  USD/hr      534
    Design              Evaporation            kg/hr 2.09e+04
                        Volume                       1.05e+03
                        Diameter                   m     3.76
                        Length                             94
                        Peripheral drum area      m2 1.11e+03
    Purchase cost       Drum dryer               USD  1.2e+06
    Total purchase cost                          USD  1.2e+06
    Utility cost                              USD/hr      600
    
    """
    # auxiliary_unit_names = ('heat_exchanger',)
    _units = {'Evaporation': 'kg/hr',
              'Peripheral drum area': 'm2',
              'Diameter': 'm',
              'length': 'm'}
    _N_ins = 3
    _N_outs = 3
    
    @property
    def isplit(self):
        """[ChemicalIndexer] Componentwise split of feed to 0th outlet stream."""
        return self._isplit
    @property
    def split(self):
        """[Array] Componentwise split of feed to 0th outlet stream."""
        return self._isplit.data
    
    @property
    def natural_gas(self):
        """[Stream] Natural gas to satisfy steam and electricity requirements."""
        return self.ins[2]
    
    def _init(self, split, RH=0.80, H=20., length_to_diameter=25, T=343.15, P=10*101325,
              moisture_content=0.15, utility_agent='Natural gas', gas_composition=None,
              moisture_ID=None, kW_per_m2=1.3):
        self._isplit = self.chemicals.isplit(split)
        self.define_utility('Natural gas', self.natural_gas)
        self.P = P
        self.T = T
        self.RH = RH
        self.H = H
        self.gas_composition = gas_composition
        self.length_to_diameter = length_to_diameter
        self.moisture_content = moisture_content
        self.utility_agent = utility_agent
        self.moisture_ID = moisture_ID if moisture_ID is not None else "Water"

        # new properties
        self.kW_per_m2 = kW_per_m2

        self._base_cost = None
        self._base_area = None
        self._base_n_cost = None
        self._CE_base = None
        
    @property
    def utility_agent(self):
        return self._utility_agent
    
    @utility_agent.setter
    def utility_agent(self, utility_agent):
        if utility_agent not in ('Natural gas', 'Steam'):
            raise ValueError(f"utility agent must be either 'Steam' or 'Natural gas'; not '{utility_agent}'")
        self._utility_agent = utility_agent

    def _get_moisture_ID_psat(self, T):
        chemical = self.thermo.chemicals[self.moisture_ID]
        return chemical.Psat(T)

    def _convert_air_mol_to_mass(self, n_air, gas_composition):
        mol_weight_air = 0.
        for chem, x in gas_composition:
            chem_mol_weight = self.thermo.chemicals[chem].MW
            mol_weight_air += x / chem_mol_weight
        return n_air / mol_weight_air

    def _run(self):
        wet_solids, air, natural_gas = self.ins
        dry_solids, hot_air, emissions = self.outs
        wet_solids.split_to(hot_air, dry_solids, self.split)
        sep.adjust_moisture_content(dry_solids, hot_air, self.moisture_content, self.moisture_ID)
        hot_air.P = air.P = self.P
        emissions.phase = air.phase = natural_gas.phase = hot_air.phase = 'g'
        design_results = self.design_results
        design_results['Evaporation'] = evaporation = hot_air.F_mass
        gas_composition = self.gas_composition
        if gas_composition is None:
            gas_composition = [('N2', 0.79), ('O2', 0.21)]

        # Calculate n_moisture_ID and n_evap_compounds
        n_moisture_id = hot_air.imol[self.moisture_ID]
        n_evap_compounds = hot_air.F_mol - n_moisture_id

        # Calculate y_moisture_ID
        y_moisture_id = self.RH * self._get_moisture_ID_psat(self.T)/self.P
        if not (0 < y_moisture_id < 1):
            raise ValueError(
                f"Invalid partial pressure of moisture_ID compound (expected between 0 and 1). Current: {y_moisture_id}."
            )

        # Calculate total gas flow (molar basis)
        n_dry_gas = (n_moisture_id * (1-y_moisture_id)/y_moisture_id - n_evap_compounds)

        total_gas_flow = self._convert_air_mol_to_mass(n_dry_gas, gas_composition)
        for ID, x in gas_composition:
            air.imass[ID] = x * total_gas_flow
        hot_air.mol += air.mol
        dry_solids.T = hot_air.T = self.T
        emissions.T = self.T + 30.
        natural_gas.empty()
        emissions.empty()
        if self.utility_agent == 'Natural gas':
            LHV = self.chemicals.CH4.LHV
            def f(CH4):
                CO2 = CH4    
                H2O = 2. * CH4
                natural_gas.imol['CH4'] = CH4
                emissions.imol['CO2', 'H2O'] = [CO2, H2O]    
                duty = (dry_solids.H + hot_air.H + emissions.H) - (wet_solids.H + air.H + natural_gas.H)
                CH4 = duty / LHV
                return CH4
            flx.wegstein(f, 0., 1e-3)
        
    def _design(self):
        length_to_diameter = self.length_to_diameter
        design_results = self.design_results
        design_results['Volume'] = volume = design_results['Evaporation'] / self.H 
        design_results['Diameter'] = diameter = bst.design_tools.cylinder_diameter_from_volume(volume, length_to_diameter)
        design_results['Length'] = length = diameter * length_to_diameter
        design_results['Peripheral drum area'] = drum_area = bst.design_tools.cylinder_area(diameter, length)
        if self.utility_agent == 'Steam':
            self.add_heat_utility(self.H_out - self.H_in, self.T)
        
        # power utility
        kW = self.kW_per_m2 * drum_area
        self.add_power_utility(kW)

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 210000    # USD
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            self._base_area = 9.0       # m2
        return self._base_area

    @base_area.setter
    def base_area(self, value):
        """
        """
        self._base_area = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.52
        return self._base_n_cost
    
    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value
    
    @property
    def CE_base(self):
        """
        """
        if self._CE_base is None:
            self._CE_base = 1000.0
        return self._CE_base
    
    @CE_base.setter
    def CE_base(self, value):
        """
        """
        self._CE_base = value

    def _cost(self):
        """
        """
        # Get the peripheral drum area from design results
        Peripheral_Drum_Area = self.design_results['Peripheral drum area']
        
        # Calculate the baseline purchase cost for the drum dryer
        ## The base cost account for double drum, atmospheric pressure, cast iron, chrome plated 
        ## with 304 s/s side and cross conveyors, dip pan, knife assembly, rotary steam/water
        ## joints, end scrapers, drive, motors and fume hood.
        ## reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Drum_Dryer_Purchase_Cost = self.base_cost * (Peripheral_Drum_Area/self.base_area)**self.base_n_cost
        self.baseline_purchase_costs['Drum Dryer'] = Drum_Dryer_Purchase_Cost

        ## Material, pressure and temperature factor
        self.F_D['Drum Dryer'] = self.F_M['Drum Dryer'] = self.F_P['Drum Dryer'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.60             # Dryer
        Instrumentation_Control = 0.50
        Piping = 0.31                   # Solid-Fluid

        ### Calculate the Bare Module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Drum Dryer'] = Bare_Module

        ## Scale the cost using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Drum Dryer'] *= bst.CE/CE_base