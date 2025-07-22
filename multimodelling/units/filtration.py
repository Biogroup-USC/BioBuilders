"""
"""

import biosteam as bst
import numpy as np

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class RotaryVacuumFilter(bst.SolidsSeparator):
    """
    Create a RotaryVacuumFilter object.
    
    Parameters
    ----------
    ins : 
        * [0] Feed
        * [1] Wash water
    outs :  
        * [0] Retentate
        * [1] Permeate
    split : array_like or dict[str, float]
           Component splits.
    moisture_content : float
                       Fraction of water in retentate.
    
    """
    auxiliary_unit_names = ('vacuum_system',)
    _F_BM_default = {'Vessels': 2.32,
                     'Vacuum system': 1.0}
    
    #: Revolutions per second
    rps = 20/3600
    
    #: Radius of the vessel (m)
    radius = 1
    
    #: Suction pressure (Pa)
    P_suction = 1500.
    
    #: For crystals (lb/day-ft^2)
    filter_rate = 6000
    
    _kwargs = {'moisture_content': 0.80} # fraction
    _bounds = {'Individual area': (2, 100)}
    _units = {'Area': 'm^2',
              'Individual area': 'm^2'}
    
    def _design(self):
        flow = sum([stream.F_mass for stream in self.outs])
        self.design_results['Area'] = self._calc_Area(flow, self.filter_rate)

    @property
    def base_cost_filter(self):
        """
        """
        if self._base_cost_filter is None:
            self._base_cost_filter = 280000     # USD
        return self._base_cost_filter   

    @base_cost_filter.setter
    def base_cost_filter(self, value):
        """
        """
        self._base_cost_filter = value

    @property
    def base_area_filter(self):
        """
        """
        if self._base_area_filter is None:
            self._base_area_filter = 22.0       # m3
        return self._base_area_filter
    
    @base_area_filter.setter
    def base_area_filter(self, value):
        """
        """
        self._base_area_filter = value

    @property
    def base_n_cost_filter(self):
        """
        """
        if self._base_n_cost_filter is None:
            self._base_n_cost_filter = 0.65
        return self._base_n_cost_filter
    
    @base_n_cost_filter.setter
    def base_n_cost_filter(self, value):
        """
        """
        self._base_n_cost_filter = value
    
    @property
    def CE_base_filter(self):
        """
        """
        if self._CE_base_filter is None:
            self._CE_base_filter = 1000.0
        return self._CE_base_filter
    
    @CE_base_filter.setter
    def CE_base_filter(self, value):
        """
        """
        self._CE_base_filter = value

    def _cost(self):
        Design = self.design_results
        Area = Design['Area']
        # Calculate the baseline purchase costs for the Rotatory Vacuum Drum Filter
        ## The base cost accounts for a rotatory drum filter, vacuum with discharger,
        ## filtrate pumps, vacuum system, motor and drive.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Filter_Purchase_Cost = self.base_cost_filter * (Area/self.base_area_filter)**self.base_n_cost_filter
        self.baseline_purchase_costs['Vessels'] = Filter_Purchase_Cost * bst.CE/self.CE_base_filter
        
    @staticmethod
    def _calc_Area(flow, filter_rate):
        """Return area in ft^2 given flow in kg/hr and filter rate in lb/day-ft^2."""
        return flow * 52.91 / filter_rate