"""
Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of
Illinois/NCSA Open Source License.
Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
"""

import biosteam as bst

__all__ = ('PelletMill',)

class PelletMill(bst.Unit):
    """
    Create a pellet mill for pelletizing solids.

    This class simulates a pelletizer, accounting for its energy consumption, solid capacity, design and cost.
    The mass balance assumes that the output is equal to the input.

    Parameters
    ----------
    ID: str
        Name of the unit operation.
    
    ins: tuple
        List of input streams.
        * [0] solid
    
    outs: tuple
        List of output streams.
        * [0] pelletized solid

    Attributes
    ----------
    power_consumption: float
        Specific power consumption of the pelletizer [kWh/kg].
    """

    _N_ins = 1
    _N_outs = 1
    _units = {
        'Power': 'kW',
        'Specific power': 'kWh/kg',
        'Solids capacity': 'kg/hr'
    }

    def _init(self):
        """
        Initialize the properties.
        """
        self._power_consumption = None
        self._base_cost = None
        self._base_solids_capacity = None
        self._base_n_cost = None
        self._CE_base = None

    def _run(self):
        """
        This method runs the unit. 
        The pellet mill mass balance is simulated with inflow equal to outflow.
        """

        # Defining the inlet
        Feed = self.ins[0]
        Feed.phase = 's'

        # Defining the oulet
        Out = self.outs[0]
        Out.phase = 's'

        # Running the unit
        Out.copy_like(Feed)
        Out.F_mass = Feed.F_mass 

    @property
    def power_consumption(self):
        """
        This property refers to the power consumption as kWh/kg.
        """
        if self._power_consumption is None:
            self._power_consumption = 0.01 # kWh heuristic value from: Perry's Handbook.
        return self._power_consumption


    def _design(self):
        """
        """
        Design = self.design_results
        Ins1, = self.ins

        # Power
        Power = self.power_consumption * Ins1.F_mass
        Design['Specific Power'] = self.power_consumption
        Design['Power'] = Power

        # Solids capacity
        Design['Solids Capacity'] = Ins1.F_mass

        # Add electricity utility
        self.add_power_utility(Power)
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 30000 # USD from: Rules of Thumb
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value
    
    @property
    def base_solids_capacity(self):
        """
        """
        if self._base_solids_capacity is None:
            self._base_solids_capacity = 3000 # kg/hr from: Rules of Thumb
        return self._base_solids_capacity
    
    @base_solids_capacity.setter
    def base_solids_capacity(self, value):
        """
        """
        self._base_solids_capacity = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.12 # From: Rules of Thumb
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
        Solids_Capacity = self.design_results['Solids Capacity']

        # Calculate the baseline purchase cost for the pellet mill
        Pellet_Mill_Baseline_Cost = self.base_cost * (Solids_Capacity/self.base_solids_capacity) ** self.base_n_cost
        self.baseline_purchase_costs['Pellet Mill'] = Pellet_Mill_Baseline_Cost

        # The material, pressure and temperature factor are assumed to be 1
        self.F_D['Pellet Mill'] = self.F_M['Pellet Mill'] = self.F_P['Pellet Mill'] = 1

        # The bare module factor which account for installation cost is calculated as the sum of delivery, installation, piping, instrumentation and controls
        Delivery = 0.10
        Installation = 0.50 # Assumed  
        Instrumentation_Control = 0.50
        Piping = 0.16 # Solid

        # Calculate the bare module with percentages from Peters: Plant Design and Economics for Chemical Engineers
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Pellet Mill'] = Bare_Module

        # Scale the cost using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Pellet Mill'] *= bst.CE/CE_base