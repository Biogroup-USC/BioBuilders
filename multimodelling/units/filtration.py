"""
"""

import biosteam as bst
import numpy as np

__all__ = (
    'RotaryVacuumFilter',
)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class SolidsSeparator(bst.Splitter):
    """
    Create SolidsSeparator object.
    
    Parameters
    ----------
    ins : 
        Inlet fluids with solids.
    outs : 
        * [0] Retentate.
        * [1] Permeate.
    split : array_like
        Component splits to 0th output stream
    moisture_content : float
        Fraction of water in solids
    
    """
    _N_ins = 1
    _ins_size_is_fixed = False
    
    def _init(self, split, 
            order=None, moisture_content=None, 
            moisture_ID=None,
            strict_moisture_content=None
        ):
        bst.Splitter._init(self, order=order, split=split)
        #: Moisture content of retentate
        self.moisture_content = moisture_content
        self.strict_moisture_content = strict_moisture_content
        if moisture_content is not None:
            if moisture_ID is None: moisture_ID = '7732-18-5'
            self.moisture_ID = moisture_ID
        self._base_cost_filter = None
        self._base_area_filter = None
        self._base_n_cost_filter = None
        self._CE_base_filter = None
    
    def _run(self):
        if self.moisture_content is None:
            bst.separations.mix_and_split(
                self.ins, *self.outs, self.split,
            )
        else:
            moisture_ID = self.moisture_ID
            self.isplit[moisture_ID] = 0.
            bst.separations.mix_and_split_with_moisture_content(
                self.ins, *self.outs, self.split, self.moisture_content, self.moisture_ID,
                self.strict_moisture_content,
            )


    #     if self._recycle_system and self._system.algorithm == 'Phenomena oriented':
    #         ID = self.moisture_ID
    #         if not ID: return
    #         top, bottom = self.outs
    #         top_mol = top.imol[ID]
    #         self.isplit[ID] = top_mol / (top_mol + bottom.imol[ID])
            
    # def _update_nonlinearities(self):
    #     outs = self.outs
    #     data = [i.get_data() for i in outs]
    #     self._run()
    #     for i, j in zip(outs, data): i.set_data(j)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class RotaryVacuumFilter(SolidsSeparator):
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
        self.design_results['Area'] = self._calc_Area(flow, self.filter_rate) * 0.092903

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