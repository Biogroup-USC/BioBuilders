"""
"""

import biosteam as bst
import numpy as np
from ..tools.mathtools.unitsarea import calculate_rdvf_area

__all__ = (
    'RotaryVacuumFilter',
    'RotatoryVacuumDrumFilter',
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

class RotatoryVacuumDrumFilter(bst.Unit):
    """
    Vacuum drum filtration unit.

    This unit models a rotary vacuum drum filter used to separate solids from a liquid stream, 
    optionally including a washing stream to displace part of the liquid and/or impurities. The 
    model accounts for solvent retention in the solid cake by targeting a specified moisture content. 
    Washing solvent is partially retained by the solid phase according to a moisture specification, 
    and the rest is recovered in the filtrate.

    Design calculations include estimation of the required filtration area based on the slurry 
    flowrate, fluid properties, cake solids concentration, pressure drop, and filtration rate. 
    The area is used to estimate equipment purchase and installation costs.

    Parameters
    ----------
    ID : str
        Unit operation identifier.
    ins : list of [Stream, Stream]
        Inlet streams [Feed, Washing]. The feed contains the solids and retained solvent. 
        The washing stream contains additional solvent to displace retained liquid.
    outs : list of [Stream, Stream]
        Outlet streams [Filtrate, Retentate]. The filtrate contains displaced and unretained liquid; 
        the retentate contains the solid cake and retained liquid.
    moisture_content : float, optional
        Target moisture content in the solid cake (kg retained liquid/kg dry solids). Default is 0.40.
    washing_chem : list[str], optional
        List of washing components to consider for retention and displacement (e.g., ["Water", "Ethanol"]).
    submergence : float, optional
        Submergence ratio of the filter drum (default = 0.35).
    operating_T : float, optional
        Operating temperature in Kelvin (default = 298.15 K).
    operating_P : float, optional
        Operating pressure in Pascal (default = 101325 Pa).
    mu : float, optional
        Liquid viscosity [Pa·s]. If not provided, it is estimated from the mixed feed and washing streams.
    rho : float, optional
        Liquid density [kg/m3]. If not provided, it is estimated from the mixed feed and washing streams.
    solids : list[str], optional
        List of solid-phase component IDs used to determine solid concentration in the slurry.

    Attributes
    ----------
    delta_P : float
        Pressure drop across the filter [Pa]. Default is 80000 Pa.
    filtration_type : str
        Filtration rate class: "Fast", "Medium", or "Slow". Affects area estimation. Default is "Medium".
    base_cost_filter : float
        Reference filter equipment cost at base size and CEPCI. Default is 280,000 USD.
    base_area_filter : float
        Reference filter area [m2] used for scaling. Default is 22.0 m2.
    base_n_cost_filter : float
        Cost scaling exponent. Default is 0.65.
    CE_base_filter : float
        Base CEPCI value for cost reference. Default is 1000.0.

    Notes
    -----
    - Assumes uniform retention of solvent and uniform displacement during washing.
    - If no washing stream is supplied, the model will retain solvent directly from the feed identifying it as the main chemical of this stream.
    - Filtration area is estimated using empirical expressions based on Darcy’s law.
    - Equipment costs are scaled from reference values using BioSTEAM conventions.

    See Also
    --------
    calculate_rdvf_area : Function used for filter area estimation based on fluid and cake properties.
    """
    # Inlets
    _N_ins = 2

    # Outlets
    _N_outs = 2

    def _init(self,
              sfi: dict = None,
              moisture_content: float = 0.40,
              washing_chem: list = None,
              tau: float = 0.5,
              submergence = 0.35,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              mu: float = None,
              rho: float = None,
              solids: list = None,
              ):
        """
        """
        self.sfi = sfi
        self.moisture = moisture_content
        self.wash_chems = washing_chem
        self.tau = tau
        self.submergence = submergence
        self.operating_T = operating_T
        self.operating_P = operating_P
        self.mu = mu
        self.rho = rho
        self.solids = solids
        self._delta_P = None
        self._filtration_type = None
        self._base_cost_filter = None
        self._base_area_filter = None
        self._base_n_cost_filter = None
        self._CE_base_filter = None

    def _run(self):
        """
        """
        # Define the inlet streams
        Feed, Washing = self.ins

        # Define the outlet streams
        Filtrate, Retentate = self.outs

        Filtrate.copy_flow(Washing)
        Filtrate.T = self.operating_T
        Filtrate.P = self.operating_P
        Filtrate.phase = 'l'

        Retentate.copy_flow(Feed)
        Retentate.phase = 's'
        Retentate.T = self.operating_T
        Retentate.P = self.operating_P

        # Simulate the separation
        for chem in self.sfi.keys():
            Filtrate.imass[chem] = self.sfi[chem] * Feed.imass[chem]
            Retentate.imass[chem] = (1-self.sfi[chem]) * Feed.imass[chem]

        # Calculate the moisture
        if self.wash_chems:
            total_washing = sum(Feed.imass[chem] + Washing.imass[chem] for chem in self.wash_chems)
            if total_washing == 0:
                raise ValueError(f"[{self.ID}] No filter washing flow provided.")
            
            # Estimate the dry mass
            dry_mass = Retentate.F_mass - sum(Retentate.imass[chem] for chem in self.wash_chems)
            retained_liquid_mass = self.moisture * dry_mass
            if retained_liquid_mass > total_washing:
                raise ValueError("[{}] Not enough wash/solvent to achieve moisture objective.")
            retention_ratio = retained_liquid_mass / total_washing
            for chem in self.wash_chems:
                total_in = Washing.imass[chem] + Feed.imass[chem]
                Retentate.imass[chem] = retention_ratio * total_in
                Filtrate.imass[chem] = (1-retention_ratio) * total_in
                total_out = Filtrate.imass[chem] + Retentate.imass[chem]
                if not np.isclose(total_out, total_in, rtol = 1e-5, atol = 1e-8):
                    raise ValueError("Not enough {} to achieve moisture objective".format(chem))
        else:
            if Washing.F_mass != 0:
                raise ValueError("If the washing chems are not defined, the washing stream must remain empty")
            fluid = Feed.main_chemical
            total_washing = sum(Feed.imass[fluid])
            retained = self.moisture * Retentate.F_mass
            retention_ratio = retained / total_washing
            Retentate.imass[fluid] = retention_ratio * Feed.imass[fluid]
            Filtrate.imass[fluid] = (1-retention_ratio) * Feed.imass[fluid]
       
    @property
    def delta_P(self):
        """
        """
        if self._delta_P is None:
            self._delta_P = 80000   # Pa 
        return self._delta_P
    
    @delta_P.setter
    def delta_P(self,value):
        """
        """
        self._delta_P = value

    @property
    def filtration_type(self):
        """
        """
        if self._filtration_type is None:
            self._filtration_type = "Medium"
        return self._filtration_type
    
    @filtration_type.setter
    def filtration_type(self,value):
        """
        """
        self._filtration_type = value

    def _design(self):
        """
        """
        # Load the dictionary of results
        design = self.design_results

        # Load the input streams
        Feed, Washing = self.ins

        # Load output streams
        Filtrate, Retentate = self.outs

        # Mix the streams
        Load = bst.Stream(units='kg/hr')
        Load.mix_from(Feed,Washing)

        # Add the filter total area
        design['Filter total area'] = self._calculate_filter_area(Load,Filtrate)

    def _calculate_filter_area(self, load, filtrate):
        # Obtain the viscosity
        if self.mu is not None:
            mu = self.mu
        else:
            mu = load.mu
        
        # Obtain the density
        if self.rho is not None:
            rho = self.rho
        else:
            rho = load.rho

        # Obtain solid concentration
        if self.solids is None or not isinstance(self.solids, list) or not all(isinstance(s, str) for s in self.solids):
            raise ValueError("The solids name must be provided as a list")
        try:
            solids_mass = [load.imass[s] for s in self.solids]
        except KeyError as e:
            raise ValueError("Solid '{}' not found in the stream.".format(e.args[0])) from None
        Cs = sum(solids_mass)/load.F_vol

        # Calculate the filter area
        if filtrate.F_mass == 0:
            raise ValueError("[{}] Filtrate flow is zero. Cannot calculate filter area".format(self.ID))
        A_filter = calculate_rdvf_area(
            filtrate.F_mass,            # kg/h
            rho,                        # kg/m3
            self.delta_P,               # Pa
            mu,                         # Pa*s
            self.filtration_type,       # Fast/Medium/Slow
            Cs,                         # kg/m3
            self.submergence            # fraction
        )
        return A_filter

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
        """
        """
        # Load parameters
        A_Filter = self.design_results['Filter total area']

        # Calculate the baseline purchase costs for the Rotatory Vacuum Drum Filter
        ## The base cost accounts for a rotatory drum filter, vacuum with discharger,
        ## filtrate pumps, vacuum system, motor and drive.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Filter_Purchase_Cost = self.base_cost_filter * (A_Filter/self.base_area_filter)**self.base_n_cost_filter
        self.baseline_purchase_costs['Rotatory Vacuum Drum Filter'] = Filter_Purchase_Cost

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Rotatory Vacuum Drum Filter'] = self.F_M['Rotatory Vacuum Drum Filter'] = self.F_P['Rotatory Vacuum Drum Filter'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.80             # Filters
        Instrumentation_Control = 0.25  # Assumed from the range 0.08 - 0.50 mentioned on the book
        Piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Rotatory Vacuum Drum Filter'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_Base = self.CE_base_filter
        self.baseline_purchase_costs['Rotatory Vacuum Drum Filter'] *= bst.CE/CE_Base

membrane_LMH = {
    "UF_hollow_fibers": (0.005, 0.016),     # L/s*m2
    "UF_Spiral_Wound": (0.08, 0.14),        # L/s*m2
    "UF_Tubes": (0.06, 0.2),                # L/s*m2
    "MF": (0.001, 0.2)
}
membrane_capacity = {
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

    def _init(self, type: int = 0, solids_retained: list[str] = [], solids: list[str] = [], solids_retentate_conc: float = 0.60):
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

        # Calculate the amount of water or solvent needed to get the solids concentration
        ## Get the main chemical of the stream
        main_chemical = feed.main_chemical
        
        ## Solvent content is calculated using solid concentration (kg/kg) of retentate
        C_s = self.retentate_solids_conc
        water_ret_needed = solids_retained * (1 - C_s) / C_s
        
        water_feed = feed.imass[main_chemical]

        ## Could not retain more water than the amount in feed
        water_ret = min(water_ret_needed, water_feed)
        water_per = water_feed - water_ret
        
        retentate.imass[main_chemical] = water_ret
        permeate.imass[main_chemical] = water_per
    
    @property
    def kWh_per_kg(self):
        """
        """
        if self._kWh_per_kg is None:
            self._kWh_per_kg = 10**-3   # Lower value from http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kWh_per_kg

    def _design(self):
        """
        """
        # The area is calculated using the permeate following the next
        # equation: LMH = Q/A                                                           #TODO apply temperature increment (+25% for each +10ºC)
        feed = self.ins[0]
        permeate = self.outs[0]
        
        LMH = membrane_LMH[self.type][1] * 10**-3 * 3600 * permeate.rho  # kg/h         #TODO Use a conservative value (mean for example)S
        
        A = permeate.F_mass / LMH

        # design results
        design = self.design_results
        design["Area (total)"] = A

        # Number of modules needed
        volumetric_flow = permeate.F_vol/3600                   # m3/s
        capacity = membrane_capacity[self.type][1]              # m3/s
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