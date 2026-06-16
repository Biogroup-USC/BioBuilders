"""
"""

import biosteam as bst
import numpy as np
from .centrifuge import SolidsSeparator

__all__ = (
    'RotaryVacuumFilter',
)
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
    _F_BM_default = {'Vessels': 2.32,}
   
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
    _units = {'Area': 'ft^2',
              'Individual area': 'ft^2'}

    def _init(self,
              split,
              order=None,
              moisture_content=0.40,
              moisture_ID=None,
              solute_ID=None,
              strict_moisture_content=None,
              solids=None,
            ):
        SolidsSeparator._init(
            self,
            moisture_content=moisture_content,
            split=split,
            order=order,
            moisture_ID=moisture_ID,
            solute_ID=solute_ID,
            strict_moisture_content=strict_moisture_content,
        )

        self.solids = solids

        self._kWh_per_kg = None

        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._base_CE = None
    
    @property
    def kWh_per_kg(self):
        """
        """
        if self._kWh_per_kg is None:
            self._kWh_per_kg = 0.0055   # mean value from http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kWh_per_kg

    @kWh_per_kg.setter
    def kWh_per_kg(self,value):
        """
        """
        self._kWh_per_kg = value

    def _design(self):
        flow = sum([stream.F_mass for stream in self.outs])
        self.design_results['Area'] = self._calc_Area(flow, self.filter_rate)
        
        if self.solids is not None:
            total_solids = sum(i.imass[self.solids].sum() for i in self.ins)
            self.add_power_utility(self.kWh_per_kg*total_solids)
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 280000     # USD
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
            self._base_area = 22.0       # m3
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
            self._base_n_cost = 0.65
        return self._base_n_cost
    
    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value
    
    @property
    def base_CE(self):
        """
        """
        if self._base_CE is None:
            self._base_CE = 1000.0
        return self._base_CE
    
    @base_CE.setter
    def base_CE(self, value):
        """
        """
        self._base_CE = value

    def _cost(self):
        Design = self.design_results
        Area = Design['Area']
        ub = self._bounds['Individual area'][1]
        N_vessels = np.ceil(Area/ub)
        iArea = Area/N_vessels # individual vessel
        self.parallel['self'] = N_vessels
        Design['Individual area'] = iArea
        
        # Calculate the baseline purchase costs for the Rotatory Vacuum Drum Filter
        ## The base cost accounts for a rotatory drum filter, vacuum with discharger,
        ## filtrate pumps, vacuum system, motor and drive.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Filter_Purchase_Cost = self.base_cost * ((Area * 0.092903)/self.base_area)**self.base_n_cost
        self.baseline_purchase_costs['Vessels'] = Filter_Purchase_Cost * bst.CE/self.base_CE

    @staticmethod
    def _calc_Area(flow, filter_rate):
        """Return area in ft^2 given flow in kg/hr and filter rate in lb/day-ft^2."""
        return flow * 52.91 / filter_rate

MEMBRANE_LMH = {
    "UF_hollow_fibers": (0.005, 0.016),     # L/s*m2
    "UF_Spiral_Wound": (0.08, 0.14),        # L/s*m2
    "UF_Tubes": (0.06, 0.2),                # L/s*m2
    "MF": (0.001, 0.2)
}
MEMBRANE_CAPACITY = {
    "UF_hollow_fibers": (0.1, 25),  # L/s
    "UF_Spiral_Wound": (0.1, 25),   # L/s
    "UF_Tubes": (0.1, 25),          # L/s
    "MF": (0.001, 1.0)              # L/s
}

class MembraneFiltration(bst.Unit):
    """

    This class simulates a filtration using a membrane system.

    The solids retained must be specified, this solids are assumed to
    be completely separated. In addition, all the solids must be defined
    to calculate the solid loading which is used to estimate the power.

    Parameters
    ----------
    ID : str
        Unit name.
    ins : tuple
        Inlet streams.
        * [0] feed.
    outs : tuple
        Outlet streams.
        * [0] permeate.
        * [1] retentate.
    type : float
        * [0] Ultrafiltration using polysulfone hollow fibers.
        * [1] Ultrafiltration using polysulfone spiral wounds.
        * [2] Ultrafiltration using polysulfone tubes.
        * [3] Microfiltration.
    solids_retained : list[str]
        List of chemical IDs retained in the retentate.
    solids : list[str]
        List of chemical IDs of all solids. This is used
        to calculate the solids loading.
    solids_retentate_conc : float
        Mass concentration of solids in the retentate used
        to calculate the amount of water retained. Default to
        0.60 kg DW/kg

    """
    # Number of input streams
    _N_ins = 1
    # Number of output streams
    _N_outs = 2
    # Results units
    _units = {
        "Area (total)": "m2",
    }

    def _init(
        self, 
        type: int = 0, 
        solids_retained: list[str] = [], 
        solids: list[str] = [], 
        solids_retentate_conc: float = 0.60, 
        solvent_IDs: list = [], 
        solute_IDs: list = []
        ):
        """
        """
        if type == 0:
            self.type = "UF_hollow_fibers"
        elif type == 1:
            self.type = "UF_Spiral_Wound"
        elif type == 2:
            self.type = "UF_Tubes"
        elif type == 3:
            self.type = "MF"
        
        self.solids_retained = solids_retained
        self.solids = solids
        self.retentate_solids_conc = solids_retentate_conc
        self.solvent_IDs = solvent_IDs
        self.solute_IDs = solute_IDs

        # Properties
        self._kWh_per_kg = None
        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._CE_base = None

    def _run(self):
        """
        """
        # Input stream
        feed, = self.ins

        # Output streams
        permeate, retentate = self.outs
        permeate.copy_like(feed)

        # Calculate the amount of solids retained
        solids_retained = 0
        for solid in self.solids_retained:
            flow_permeate = 0 * feed.imass[solid]
            flow_retentate = 1 * feed.imass[solid]
            solids_retained += flow_retentate

            permeate.imass[solid] = flow_permeate
            retentate.imass[solid] = flow_retentate

        # Calculate solute and solvent needed to satisfy retained solids concentration
        mass_solute_solvent = solids_retained / self.retentate_solids_conc - solids_retained

        # Distribute solute and solvent
        solvent_feed = 0.
        for solvent_ID in self.solvent_IDs:
            solvent_feed += feed.imass[solvent_ID]

        solute_feed = 0.
        for solute_ID in self.solute_IDs:
            solute_feed += feed.imass[solute_ID]

        split_to_retentate = mass_solute_solvent/(solvent_feed+solute_feed)

        for element in self.solvent_IDs + self.solute_IDs:
            retentate.imass[element] = feed.imass[element] * split_to_retentate
            permeate.imass[element] -= retentate.imass[element]
    
    @property
    def kWh_per_kg(self):
        """
        """
        if self._kWh_per_kg is None:
            self._kWh_per_kg = 0.0055   # mean value from http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kWh_per_kg

    @kWh_per_kg.setter
    def kWh_per_kg(self,value):
        """
        """
        self._kWh_per_kg = value

    def _design(self):
        """
        """
        # The area is calculated using the permeate following the next
        # equation: LMH = Q/A                                                           #TODO apply temperature increment (+25% for each +10ºC)
        feed = self.ins[0]
        permeate = self.outs[0]
        
        LMH = MEMBRANE_LMH[self.type][1] * 10**-3 * 3600 * permeate.rho  # kg/h         #TODO Use a conservative value (mean for example)S
        
        A = permeate.F_mass / LMH

        # design results
        design = self.design_results
        design["Area (total)"] = A

        # Number of modules needed
        volumetric_flow = permeate.F_vol/3600                   # m3/s
        capacity = MEMBRANE_CAPACITY[self.type][1]              # m3/s
        self.parallel["Modules"] = volumetric_flow/capacity

        # Utilities
        solids_load = 0
        for solid in self.solids:
            solids_load += feed.imass[solid]

        power = self.kWh_per_kg * solids_load
        self.add_power_utility(power)
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            if self.type.startswith("MF"):
                self._base_cost = 150000    # $ for membrane and housing
            elif self.type.startswith("UF"):
                self._base_cost = 240       # $ for m2 of membrane
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            if self.type.startswith("MF"):
                self._base_n_cost = 0.92
            elif self.type.startswith("UF"):
                self._base_n_cost = 1.0
        return self._base_n_cost

    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            if self.type.startswith("MF"):
                self._base_area = 50        # m2
            elif self.type.startswith("UF"):
                self._base_area = 1         # m2
        return self._base_area

    @base_area.setter
    def base_area(self, value):
        """
        """
        self._base_area = value

    @property
    def CE_base(self):
        """
        """
        if self._CE_base is None:
            if self.type.startswith("MF"):
                self._CE_base = 1000
            elif self.type.startswith("UF"):
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
        # Load all the design parameters needed to calculate the costs
        area = self.design_results["Area (total)"]

        # Calculate the baseline purchase cost for membrane module
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        membranes_module = self.base_cost * (area/self.base_area)**self.base_n_cost
        
        ## UF membranes are accounted individually, but they represent 10 % of the total cost for small areas and
        ## 50% for largest
        if self.type.startswith("UF"):
            if area < 10:
                membranes_module *= 1/0.15
            else:
                membranes_module *= 1/0.50

        self.baseline_purchase_costs['Membrane module'] = membranes_module

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Membrane module'] = self.F_M['Membrane module'] = self.F_P['Membrane module'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.80             # Filters
        Instrumentation_Control = 0.50
        Piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Membrane module'] = Bare_Module

        ## Scale the costs using CEPCI
        self.baseline_purchase_costs['Membrane module'] *= bst.CE/self.CE_base