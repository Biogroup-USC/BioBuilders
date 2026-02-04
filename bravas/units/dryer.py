"""
"""
import biosteam as bst
import flexsolve as flx
import numpy as np
from thermosteam import separations as sep

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

    _N_ins = 1
    _N_outs = 2
    _units = {
        'Evaporation rate': 'kg/hr',
        'Heat duty': 'kJ/hr'
    }

    def _init(self,
              moisture_content = 0.10,
              dryer_efficiency = 0.80, # From Piccinno et al. (2016)
    ):
        """
        Initialize the properties.
        """
        self. moisture_content = moisture_content
        self.dryer_efficiency = dryer_efficiency

        self._base_cost = None
        self._base_evaporation_capacity = None
        self._base_n_cost = None
        self._CE_base = None

        # Add heating utilty (air)
        self.heat_utilities =[bst.HeatUtility()]

    def _run(self):
        """
        """
        # Define the streams
        Feed = self.ins[0]
        Dryed, Water = self.outs
        Dryed.copy_like(Feed)

        # Remove all water first
        Water.copy_flow(Dryed, 'Water', remove=True)

        # Adjust final moisture
        sep.adjust_moisture_content(Dryed, Water, self.moisture_content)
        Water.phase = 'g'
        Dryed.phase = 's'
        Feed.phase = 's'

    def _design(self):
        Dryed, Water = self.outs

        evap_rate = Water.get_total_flow('kg/hr')
        self.design_results['Evaporation rate'] = evap_rate

        # Energy demand 
        latent_heat = 2276 # kJ/kg for water at 105 ºC (2 bar) from HYSYS (low pressure steam)
        Q = evap_rate * latent_heat / self.dryer_efficiency
        self.design_results['Heat duty'] = Q

        steam = bst.settings.get_heating_agent('low_pressure_steam')
        if not self.heat_utilities:
            self.add_heat_utility(
                unit_duty = Q,
                T_in = 378.15, # K (105ºC and 2 bar)
                agent = steam
            )
        else:
            self.heat_utilities[0].duty = Q

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
            self._base_evaporation_capacity = 1 # kg/hr from: Rules of Thumb
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
        Evaporation_Rate = self.design_results['Evaporation rate']

        # Calculate the design cost for the spray dryer: Including instrumentation, pressure nozzle atomization, residence time about 16 s,
        # access platform, support steel, air preheater, feed system, fan, motor and drive and dust collectors. Tin = 150ºC and Tout = 75ºC
        Spray_Dryer_Purchase_Cost = self.base_cost * (Evaporation_Rate/self.base_evaporation_capacity) ** self.base_n_cost
        self.baseline_purchase_costs['Spray Dryer'] = Spray_Dryer_Purchase_Cost

        # The material, pressure and temperature factor are assumed to be 1
        self.F_D['Spray Dryer'] = self.F_M['Spray Dryer'] = self.F_P['Spray Dryer'] = 1

        # The bare module factor which account for installation cost is calculated as the sum of delivery, installation, piping, instrumentation and controls
        Delivery = 0.10
        Installation = 0.60 # Dryer
        Instrumentation_Control = 0.50
        Piping = 0.31 # Solid-fluid

        # Calculate the bare module with percentages from Peters: Plant Design and Economics for Chemical Engineers
        Bare_Module = (1 + (Delivery + Installation +  Instrumentation_Control + Piping))
        self.F_BM['Spray Dryer'] = Bare_Module

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
    R : float, optional
        Flow of hot gas over evaporation. Defaults to 1.4 wt gas / wt evap.
    H : float, optional
        Specific evaporation rate [kg/hr/m3]. Defaults to 20. 
    length_to_diameter : float, optional
        Note that the drum is horizontal. Defaults to 25.
    T : float, optional
        Operating temperature [K]. Defaults to 343.15.
    moisture_content : float
        Moisture content of solids [wt / wt]. Defaults to 0.10.
        
    """

    # auxiliary_unit_names = ('heat_exchanger',)
    _units = {'Evaporation': 'kg/hr',
              'Peripheral drum area': 'm2',
              'Diameter': 'm'}
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

    def _init(self, split, R=1.4, H=20., length_to_diameter=25, T=343.15, P=10*101325,
              moisture_content=0.15, utility_agent='Natural gas', gas_composition=None,
              moisture_ID=None):
        self._isplit = self.chemicals.isplit(split)
        self.define_utility('Natural gas', self.natural_gas)
        self.P = P
        self.T = T
        self.R = R
        self.H = H
        self.gas_composition = gas_composition
        self.length_to_diameter = length_to_diameter
        self.moisture_content = moisture_content
        self.utility_agent = utility_agent
        self.moisture_ID = moisture_ID
    
        # Initialize new properties
        self._base_n_cost = None
        self._base_area = None
        self._base_cost = None
        self._CE_base = None

    @property
    def utility_agent(self):
        return self._utility_agent
    
    @utility_agent.setter
    def utility_agent(self, utility_agent):
        if utility_agent not in ('Natural gas', 'Steam'):
            raise ValueError(f"utility agent must be either 'Steam' or 'Natural gas'; not '{utility_agent}'")
        self._utility_agent = utility_agent
   
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
            gas_composition = [('N2', 0.78), ('O2', 0.32)]
        total_gas_flow = self.R * evaporation
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
        design_results['Peripheral drum area'] = bst.design_tools.cylinder_area(diameter, length)
        if self.utility_agent == 'Steam':
            self.add_heat_utility(self.H_out - self.H_in, self.T)

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