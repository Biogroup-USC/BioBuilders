"""
"""
import biosteam as bst
from math import ceil
from biosteam.exceptions import lb_warning, InfeasibleRegion
from ..tools.moisture_adjust import mix_and_split, adjust_moisture_content, mix_and_split_with_moisture_content

__all__ = (
    "SolidsCentrifuge",
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
    
    def _run(self):
        if self.moisture_content is None:
            mix_and_split(
                self.ins, *self.outs, self.split,
            )
        else:
            moisture_ID = self.moisture_ID
            self.isplit[moisture_ID] = 0.
            mix_and_split_with_moisture_content(
                self.ins, *self.outs, self.split, self.moisture_content, self.moisture_ID,
                self.strict_moisture_content,
            )

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class SolidsCentrifuge(SolidsSeparator):
    """

    Create the same solid centrifuge from BioSTEAM, besides the cost calculation
    parameters which are now defined as properties.

    The parameters for cost calculation are defined as properties so its uncertainty
    could be assest when performing Monte Carlo.

    Parameters
    ----------
    ins : 
        Inlet fluid with solids.
    outs : 
        * [0] Solids-rich stream.
        * [1] Liquid-rich stream.
    split : array_like or dict[str, float]
           Component splits.
    order=None : Iterable[str]
        Species order of split. Defaults to Stream.chemicals.IDs.
    solids : tuple[str]
        IDs of solids.
    moisture_content : float
        Fraction of water in stream.
    centrifuge_type : str
        Type of the centrifuge, either 'reciprocating_pusher' (1-20 ton/hr solids)
        or 'scroll_solid_bowl' (2-40 ton/hr solids).
    
    Attributes
    ----------
    Base_Cost : float

    Base_n_Cost : float

    CE_Base : float

    """
    _units = {'Solids loading': 'ton/hr',
              'Flow rate': 'm3/hr'}
    solids_loading_range = {
    'reciprocating_pusher': (1, 20),
    'scroll_solid_bowl': (2, 40)
    }

    def _init(self, 
              split, 
              order=None, 
              solids=None, 
              moisture_content=0.40,
              moisture_ID=None,
              centrifuge_type='scroll_solid_bowl',
              kWh_per_kg = 0.010,
              strict_moisture_content=None,
            ):
        SolidsSeparator._init(
            self, 
            moisture_content=moisture_content,
            split=split, 
            order=order, 
            moisture_ID=moisture_ID,
            strict_moisture_content=strict_moisture_content
        )
        if solids is None:
            solids = [i.ID for i in self.chemicals if i.locked_state == 's']
        self.solids = solids
        self.centrifuge_type = centrifuge_type
        
        # new parameters
        self.kWh_per_kg = kWh_per_kg

        # new properties
        self._base_n_cost = None
        self._base_cost = None
        self._CE_base = None
        self._base_n_cost_default = None
        self._base_cost_default = None

    @property
    def solids(self):
        return self._solids
    @solids.setter
    def solids(self, solids):
        self._solids = tuple(solids)
    
    @property
    def centrifuge_type(self):
        return self._centrifuge_type
    @centrifuge_type.setter
    def centrifuge_type(self, i):
        if not i in ('reciprocating_pusher', 'scroll_solid_bowl'):
            raise ValueError('`centrifuge_type` can only be "reciprocating_pusher" or '
                            f'"scroll_solid_bowl", not {i}.')
        self._centrifuge_type = i

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 68040   # USD
        return self._base_cost
    @base_cost.setter
    def base_cost(self,value):
        """
        """
        self._base_cost = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.50
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
            self._CE_base = 567.0
        return self._CE_base
    @CE_base.setter
    def CE_base(self, value):
        """
        """
        self._CE_base = value

    @property
    def base_cost_default(self):
        """
        """
        if self._base_cost_default is None:
            self._base_cost_default = 170100  # USD
        return self._base_cost_default
    @base_cost_default.setter
    def base_cost_default(self,value):
        """
        """
        self._base_cost_default = value
    
    @property
    def base_n_cost_default(self):
        """
        """
        if self._base_n_cost_default is None:
            self._base_n_cost_default = 0.3
        return self._base_n_cost_default
    @base_n_cost_default.setter
    def base_n_cost_default(self, value):
        """
        """
        self._base_n_cost_default = value
    
    def _design(self):
        solids, centrifuge_type = self._solids, self.centrifuge_type
        ts = sum([s.imass[solids].sum() for s in self.ins if not s.isempty()]) # Total solids
        ts *= 0.0011023 # To short tons (2000 lbs/hr)
        self.design_results['Solids loading'] = (ts * 0.9072) # To metric tons
        lb, ub = self.solids_loading_range[centrifuge_type]
        if ts < lb:
            lb_warning(self, 'Solids loading', ts, 'ton/hr', lb)
        self.design_results['Number of centrifuges'] = ceil(ts/ub)
        self.design_results['Flow rate'] = self.F_vol_in
        F_mass_in = self.F_mass_in
        self.power_utility(F_mass_in * self.kWh_per_kg)
    
    def _cost(self):
        solids_loading = self.design_results['Solids loading']
        
        # Cost of the unit
        if self.centrifuge_type:
            cost = self.base_cost * (solids_loading**self.base_n_cost)
        else:
            cost = self.base_cost_default * (solids_loading**self.base_n_cost_default)
        
        # Update cost using CEPCI
        cost *= bst.CE / self.CE_base

        self.baseline_purchase_costs['Centrifuges'] = cost
        self.F_BM['Centrifuges'] = 2.03