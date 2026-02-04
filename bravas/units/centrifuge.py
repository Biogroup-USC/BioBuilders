"""
"""
import biosteam as bst
from math import ceil, exp, log
from biosteam.exceptions import lb_warning, InfeasibleRegion

__all__ = (
    "SolidsCentrifuge",
)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class SolidsCentrifuge(bst.SolidsCentrifuge):
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
    def _init(self, split, order=None, solids=None, moisture_content=0.40,
              centrifuge_type='scroll_solid_bowl', moisture_ID=None,
              strict_moisture_content=None):
        bst.SolidsSeparator._init(
            self, moisture_content=moisture_content,
            split=split, order=order, moisture_ID=moisture_ID,
            strict_moisture_content=strict_moisture_content
        )
        if solids is None:
            solids = [i.ID for i in self.chemicals if i.locked_state == 's']
        self.solids = solids
        self.centrifuge_type = centrifuge_type
        
        # Initialize new properties
        self._base_n_cost = None
        self._base_cost = None
        self._CE_base = None
        self._base_n_cost_ifnot = None
        self._base_cost_ifnot = None

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
    def base_cost_ifnot(self):
        """
        """
        if self._base_cost_ifnot is None:
            self._base_cost_ifnot = 170100  # USD
        return self._base_cost_ifnot
    
    @base_cost_ifnot.setter
    def base_cost_ifnot(self,value):
        """
        """
        self._base_cost_ifnot = value
    
    @property
    def base_n_cost_ifnot(self):
        """
        """
        if self._base_n_cost_ifnot is None:
            self._base_n_cost_ifnot = 0.3
        return self._base_n_cost_ifnot

    @base_n_cost_ifnot.setter
    def base_n_cost_ifnot(self, value):
        """
        """
        self._base_n_cost_ifnot = value
    
    def _design(self):
        solids, centrifuge_type = self._solids, self.centrifuge_type
        ts = sum([s.imass[solids].sum() for s in self.ins if not s.isempty()]) # Total solids
        ts *= 0.0011023 # To short tons (2000 lbs/hr)
        self.design_results['Solids loading'] = ts
        lb, ub = self.solids_loading_range[centrifuge_type]
        if ts < lb:
            lb_warning(self, 'Solids loading', ts, 'ton/hr', lb)
        self.design_results['Number of centrifuges'] = ceil(ts/ub)
        cost = self.base_cost*(ts**self.base_n_cost) if centrifuge_type else self.base_cost_ifnot*(ts**self.base_n_cost_ifnot)
        cost *= bst.CE / self.CE_base
        self.baseline_purchase_costs['Centrifuges'] = cost
        self.F_BM['Centrifuges'] = 2.03
        self.design_results['Flow rate'] = F_vol_in = self.F_vol_in
        self.power_utility(F_vol_in * self.kWhr_per_m3)