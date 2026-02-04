"""
Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of
Illionois/NCSA Open Sourece License.
Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
"""

import biosteam as bst

__all__ = ('BiomassBoiler',)

class BiomassBoiler(bst.Unit): 
    """
    Create a boiler for the production of steam from biomass.

    This class simulates a biomass boiler, accounting for its steam generation, design and cost.
    
    Parameters
    ----------
    ID: str
        Name of the unit operation.
      
    ins: tuple
        List of input streams.
        * [0]: Biomass feed that will be burned.
        * [1]: Water.
        * [2]: Air or oxygen-rich gas.

    outs: tuple
        List of output streams.
        * [0]: Total emissions produced.
        * [1]: Steam.
        * [3]: Ash disposal.

    Attributes
    ---------
    boiler_efficiency: float, optional
        Boiler efficiency for conversion of fuel energy into steam [fraction]. Default is 0.80.
    
    LHV: float, optional
        Lower heating value of biomass feed [kJ/kg].
    
    elemental_composition: dict, optional
        Mass fractions of elements in the combustible portion of biomass (e.g., {'C': 0.5, 'H': 0.06,
        'O': 0.44, 'N': 0.01, 'S': 0.001})  .

    h_steam: float, optional
        Enthalpy of the produced steam [kJ/kg]. Default is 2706 kJ/kg (low pressure steam, 2 bar, 120ºC).
    
    h_water: float, optional
        Enthalpy of the input water [kJ/kg]. Default is 105 kJ/kg (saturated water at 25ºC).
    
    T_water_in: float, optional
        Temperature of the input water [K]. Default is 298.15 K (25ºC).
    
    P_steam: float, optional
        Pressure of the produced steam [Pa]. Default is 202650 Pa (2 bar).
    
    T_steam: float, optional
        Temperature of the produced steam [K]. Default is 393.13 (120ºC).
    """
    
    _N_ins = 3
    _N_outs = 3
    _units = {'Steam flow': 'kg/hr',
              }
    
    def __init__(self, ID = '', ins = None, 
                 outs = ('Emissions',
                       'Steam',
                       'Ash'),
                 thermo = None, *,
                 boiler_efficiency = 0.80,
                 LHV = None,
                 elemental_composition = None,
                 h_steam = 2706, # kJ/kg default for low pressure steam at 2 bar and 120ºC, from HYSYS,
                 h_water = 105, # kJ/kg default for saturated water at 25ºC (1 atm), from HYSYS,
                 T_water_in = 298.15, # K default (25ºC for water)
                 P_steam = 202650, # Pa default (for steam)
                 T_steam = 393.15 # K default (120ºC for steam) 
        ):
        
        super().__init__(ID, ins, outs, thermo)       
        self.boiler_efficiency = boiler_efficiency
        self.LHV = LHV
        self.elemental_composition = elemental_composition # (dict, fractions)
        self.h_steam = h_steam
        self.h_water = h_water 
        self.T_water_in = T_water_in
        self.P_steam = P_steam
        self.T_steam = T_steam

    def _init(self):
        """
        Initialize the properties.
        """
        self._base_cost = None
        self._base_produced_steam = None
        self._base_n_cost = None
        self._CE_base = None
    
    @property
    def emissions(self):
        return self.outs[0]
    
    @property 
    def steam(self):
        return self.outs[1]
    
    @property
    def ash(self):
        return self.outs[2]
  
    @property
    def biomass(self):
        return self.ins[0]

    @property
    def makeup_water(self):
        return self.ins[1]

    @property
    def air(self):
        return self.ins[2]
      
    def _run(self):
        """
        """
        pass

    def _design(self):
        """
        """
        biomass = self.biomass
        biomass.phase = 's'

        makeup_water = self.makeup_water
        makeup_water.phase = 'l'

        air = self.air
        air.phase = 'g'

        emissions = self.emissions
        emissions.phase = 'g'

        steam = self.steam
        steam.phase = 'g'

        ash = self.ash
        ash.phase = 's'

        emissions.empty()
        steam.empty()
        makeup_water.empty()

        # Split biomass into ash and combustible
        ash_mass = biomass.imass['Ash']
        water_mass = biomass.imass['Water']
        ash.imass['Ash'] = ash_mass
        combustible_mass = biomass.F_mass - ash_mass - water_mass

        # Energy from combustion
        Q_combustion = self.LHV * biomass.F_mass # kJ/hr       
        Q_available =self.boiler_efficiency * Q_combustion # kJ/hr

        # Calculate the stream produced
        delta_h = self.h_steam - self.h_water # kJ/kg
        stream_mass =  Q_available / delta_h # kg/hr
        steam.imass['Water'] = stream_mass

        # Heat utility (energy balance)
        T_steam = getattr(self, 'T_steam', 393.15) # K, default 120ºC
        P_steam = getattr(self, 'P_stream', 202650) # Pa, default 2 bar
        steam.T = T_steam
        steam.P = P_steam

        T_water_in = getattr(self, 'T_water_in', 298.15) # K, default 25ºC
        makeup_water.T = T_water_in

        hu = bst.HeatUtility()
        hu.duty = -Q_available
        self.heat_utilities.append(hu)

        # Combustion chemistry
        ec = self.elemental_composition
        C = ec.get('C', 0) * combustible_mass # C + O2 -> CO2
        H = ec.get('H', 0) * combustible_mass # H + 0.25 02 -> 0.5 H2O
        S = ec.get('S', 0) * combustible_mass # S + O2 -> SO2
        N = ec.get('N', 0) * combustible_mass # Mostly to N2
        O = ec.get('O', 0) * combustible_mass 

        CO2 = C * (44/12) # kg basis
        SO2 = S * (64/32) # kg basis
        H2O_combustion = H * 9 # kg basis

        # Calculate the required oxygen 
        O2_C = C * (32/12)
        O2_H = H * 8
        O2_S = S * (32/32)
        O2_required = O2_C + O2_H + O2_S - O

        # Air composition (mass basis)
        z_O2 = 0.232
        z_N2 = 0.768
        
        # Required air (input flow)
        air_mass = O2_required / z_O2
        air.imass['O2'] = O2_required
        air.imass['N2'] = air_mass * z_N2

        # Calculate the emissions (output)
        emissions.imass['CO2'] = CO2
        emissions.imass['SO2'] = SO2
        emissions.imass['N2'] = air.imass['N2'] + N

        # Calculate the input water
        M_water_biomass = biomass.imass['Water'] # Humidity in the initial biomass
        makeup_water_mass = stream_mass - M_water_biomass - H2O_combustion
        makeup_water.imass['Water'] = makeup_water_mass

        # Compile the design results
        Design = self.design_results
        Design['Steam flow'] = self.steam.F_mass

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 500000 # USD from: Rules of Thumb
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value
    
    @property
    def base_produced_steam(self):
        """
        """
        if self._base_produced_steam is None:
            self._base_produced_steam = 9720 # kg/hr from. Rules of Thumb
        return self._base_produced_steam
    
    @base_produced_steam.setter
    def base_produced_steam(self, value):
        """
        """
        self._base_produced_steam = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.92 # From: Rules of Thumb
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
        Produced_Steam = self.design_results['Steam flow']

        # Calculate the baseline purchase cost for the biomass boiler: Water tube with fire tube for smaller size, 1.5 MPa
        # with boiler, burner, fan, deaerator, chemical injection, stack, integral piping, instrument.
        Biomass_Boiler_Baseline_Cost = self.base_cost * (Produced_Steam/self.base_produced_steam) ** self.base_n_cost
        self.baseline_purchase_costs['Biomass Boiler'] = Biomass_Boiler_Baseline_Cost

        # The material, pressure and temperature factor are assumed to be 1
        self.F_D['Biomass Boiler'] = self.F_M['Biomass boiler'] = self.F_P['Biomass boiler'] = 1

        # The bare module factor which account for installation cost is calculated as the sum of delivery, installation, piping, instrumentation and controls
        Delivery = 0.10
        Installation = 0.50 # Assumed
        Instrumentation_Control = 0.5
        Piping = 0.31 # Solid-fluid

        # Calculate the bare module with percentages from Peters: Plant Design and Economics for Chemical Engineers
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Biomass Boiler'] = Bare_Module

        # Scale the cost using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Biomass Boiler'] *= bst.CE/CE_base