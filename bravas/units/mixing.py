"""
"""
import biosteam as bst

__all__ = (
    "MixTank",
)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class Tank(bst.Unit, isabstract=True):
    """
    Abstract class for tanks.

    Attributes
    ----------
    tau : float
        Residence time [hr].
    V_wf : float
        Fraction of working volume over total volume.
    kW_per_m3 : float
        Electricity requirement per unit volume [kW/m^3].

    """
    _default_kW_per_m3 = 0.
    _units = {'Total volume': 'm^3',
              'Residence time': 'hr'}
    _F_BM_default = {'Tank': 2.3}
    _N_outs = 1
    
    def _init(self, 
            vessel_type=None, tau=None, V_wf=None, 
            vessel_material=None, kW_per_m3=0.
        ):
        # [str] Vessel type.
        self.vessel_type = vessel_type or self._default_vessel_type

        #: [float] Residence time in hours.
        self.tau = tau or self._default_tau

        #: [float] Fraction of working volume to total volume.
        self.V_wf = V_wf or self._default_V_wf

        #: [str] Vessel construction material.
        self.vessel_material = vessel_material or self._default_vessel_material
        
        # [float] Electricity requirement per unit volume [kW/m^3].
        self.kW_per_m3 = kW_per_m3 or self._default_kW_per_m3

    def __init_subclass__(cls, isabstract=False):
        if not isabstract:
            hasfield = hasattr
            attributes = ('_default_vessel_type', '_default_tau', 
                          '_default_V_wf', '_default_vessel_material')
            for i in attributes:
                if not hasfield(cls, i):
                    raise NotImplementedError("Tank subclass must implement "
                                              "a '{i}' attribute")
        super().__init_subclass__(isabstract)
    
    def _design(self):
        design_results = self.design_results
        design_results['Residence time'] = tau = self.tau
        design_results['Total volume'] = tau * self.F_vol_out / self.V_wf

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class MixTank(Tank):
    """
    Create a mixing tank with volume based on residence time.

    Parameters
    ----------
    ins : 
        Inlet fluids to be mixed.
    outs : 
        Outlet.
    tau : float, optional
        Residence time [hr]. Defaults to 1.
    V_wf : float, optional
        Fraction of working volume over total volume. Defaults to 0.8.
    kW_per_m3 : float, optional
        Electricity requirement per unit volume [kW/m^3]. Defaults to 0.0985.
    
    """
    rigorous = False
    conserve_phases = False
    _N_ins = 2
    _ins_size_is_fixed = False
    _run = bst.Mixer._run
    _default_vessel_type = 'Conventional'
    _default_tau = 1
    _default_V_wf = 0.8
    _default_vessel_material = 'Stainless steel'
    _default_kW_per_m3 = 0.0985

    def _init(self, 
        vessel_type=None, tau=None, V_wf=None, 
        vessel_material=None, kW_per_m3=0.
    ):
        # [str] Vessel type.
        self.vessel_type = vessel_type
        #: [float] Residence time in hours.
        self.tau = tau or self._default_tau
        #: [float] Fraction of working volume to total volume.
        self.V_wf = V_wf or self._default_V_wf
        # [float] Electricity requirement per unit volume [kW/m^3].
        self.kW_per_m3 = kW_per_m3 or self._default_kW_per_m3

        # Initialize new properties
        self._base_cost = None
        self._base_n_cost = None
        self._base_volume = None
        self._CE_base = None

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 75000.0   # USD
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self,value):
        """
        """
        self._base_cost = value
    
    @property
    def base_volume(self):
        """
        """
        if self._base_volume is None:
            self._base_volume = 3.0     # m3
        return self._base_volume

    @base_volume.setter
    def base_volume(self,value):
        """
        """
        self._base_volume = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.53
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
        # Load all the design parameters
        V_Tank = self.design_results['Total volume']
        
        # Calculate the baseline purchase cost for each reactor
        ## The base cost accounts for jacketed agitated vessel. 
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Reactor_Purchase_Cost = self.base_cost * (V_Tank/self.base_volume)**self.base_n_cost        
        self.baseline_purchase_costs['Mixing Tank'] = Reactor_Purchase_Cost
        
        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D['Mixing Tank'] = self.F_M['Mixing Tank'] = self.F_P['Mixing Tank'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.60             # Metal tanks
        Instrumentation_Control = 0.50
        Piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Mixing Tank'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_Base = self.CE_base
        self.baseline_purchase_costs['Mixing Tank'] *= bst.CE/CE_Base

MixTank._graphics.edge_in *= 3
MixTank._graphics.edge_out *= 3