"""
"""

import biosteam as bst
import numpy as np
from .centrifuge import SolidsSeparator
from ..tools.mathtools.unitsarea import calculate_rdvf_area
from ..tools.streamtools import main_chemical_mass_basis

__all__ = (
    'RotaryVacuumFilter',
    'RotatoryVacuumDrumFilter',
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

    def _init(self,
              split,
              order=None,
              moisture_content=0.40,
              moisture_ID=None,
              solute_ID=None,
              strict_moisture_content=None
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

        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._base_CE = None


    def _design(self):
        flow = sum([stream.F_mass for stream in self.outs])
        self.design_results['Area'] = self._calc_Area(flow, self.filter_rate) * 0.092903

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
        # Calculate the baseline purchase costs for the Rotatory Vacuum Drum Filter
        ## The base cost accounts for a rotatory drum filter, vacuum with discharger,
        ## filtrate pumps, vacuum system, motor and drive.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Filter_Purchase_Cost = self.base_cost * (Area/self.base_area)**self.base_n_cost
        self.baseline_purchase_costs['Vessels'] = Filter_Purchase_Cost * bst.CE/self.base_CE
        
    @staticmethod
    def _calc_Area(flow, filter_rate):
        """Return area in ft^2 given flow in kg/hr and filter rate in lb/day-ft^2."""
        return flow * 52.91 / filter_rate

class RotaryVacuumDrumFilter(bst.Unit):
    """
    Rotary vacuum drum filtration unit.

    This unit separates a slurry into a filtrate (liquid phase) and a
    retentate (solid cake containing retained liquid). A washing stream
    could be supplied to displace the mother liquor. The amount of liquid
    retained in the cake is controlled by moisture (kg retained liquids / kg dry solids
    ).

    Parameters
    ----------
    ID : str
        Unit identifier.
    ins : tuple[Stream]
        Inlet streams. Must contain at least the feed. The washing stream is optionally.
        * [0] feed
        * [1] washing
    outs : tuple[Stream]
        Output streams.
        * [0] Retentate
        * [1] Filtrate
    sfi : dict[str,float]
        Component split to retentate. Keys are component IDs, values are fractions between 0 and 1.
    moisture_content : float, optional
        Target moisture of the cake (kg liquid/kg dry solids). Default: 0.40.
    washing_chem : list[str], optional
        List of liquid components whose distribution is determined by moisture content (e.g., ["Water", "Ethanol"]).
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
        Component IDs considered as dry solids in the cake.

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
        Cost scaling exponent. Default: 0.65.
    CE_base_filter : float
        Base CEPCI value for cost reference. Default is 1000.0.

    Notes
    -----
    - Assumes uniform retention of solvent and uniform displacement during washing.
    - If no washing stream is supplied, the model will retain solvent directly from the feed identifying it as the main chemical of this stream.
    - Filtration area is estimated using empirical expressions based on Darcy's law.
    - Equipment costs are scaled from reference values using BioSTEAM conventions.

    See Also
    --------
    calculate_rdvf_area : Function used for filter area estimation based on fluid and cake properties.
    main_chemical_mass_basis : Function used for calculate the main chemical based on mass flow.

    """
    # Inlets
    _N_ins = 2
    _ins_size_is_fixed = False

    # Outlets
    _N_outs = 2

    def _init(self,
              split: dict = None,
              moisture_content: float = 0.40,
              washing_chem: list = None,
              submergence = 0.35,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              mu: float = None,
              rho: float = None,
              solids: list = None,
              ):
        """
        """
        self.split = split
        self.moisture = moisture_content
        self.wash_chems = washing_chem
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
        ins = self.ins
        feed = ins[0]

        if len(ins) > 1:
            washing = ins[1]
            has_wash = True
        else:
            washing = None
            has_wash = False

        # Define the outlet streams
        retentate, filtrate = self.outs
        retentate.T = filtrate.T = self.operating_T
        retentate.P = filtrate.P = self.operating_P
        retentate.phase = 'l'
        filtrate.phase = 'l'

        # Simulate the separation, by default all go to filtrate
        if has_wash:
            load = bst.Stream()
            load.mix_from([feed,washing])
            filtrate.copy_flow(load)
        else:
            load = feed
            filtrate.copy_flow(feed)
        
        for chem,split in self.split.items():
            filtrate.imass[chem] = (1-split) * load.imass[chem]
            retentate.imass[chem] = (split) * load.imass[chem]

        # Calculate the moisture
        if self.solids is None or not isinstance(self.solids, list) or not all(isinstance(s, str) for s in self.solids):
            raise ValueError("[{}] Solids must be provided as a list of component IDs.".format(self.ID))
        dry_mass = sum(retentate.imass[s] for s in self.solids)
        if dry_mass <= 0:
            raise ValueError("[{}] Mass of dry solids is zero; cannot apply moisture specification".format(self.ID))

        def distribute_liquids(liquids_id):
            # Calculate total liquids entering
            total_liquid_mass = 0.0
            for liquid in liquids_id:
                if has_wash:
                    total_liquid_mass += feed.imass[liquid] + washing.imass[liquid]
                else:
                    total_liquid_mass += feed.imass[liquid]

            if total_liquid_mass <= 0:
                raise ValueError("[{}] No flow of solvent/washing for specified liquids".format(self.ID))
            
            # Calculate the quantity of liquid retained
            retained_liquid_mass = self.moisture * dry_mass

            if retained_liquid_mass > total_liquid_mass:
                raise ValueError("[{}] Not enough washing/solvent to achieve moisture objective.")
            
            retention_ratio = retained_liquid_mass/total_liquid_mass

            # Apply liquid distribution
            for liquid in liquids_id:
                if has_wash:
                    liquid_mass = feed.imass[liquid] + washing.imass[liquid]
                else:
                    liquid_mass = feed.imass[liquid]
                
                mass_ret = retention_ratio * liquid_mass
                mass_filt = liquid_mass - mass_ret
                retentate.imass[liquid] = mass_ret
                filtrate.imass[liquid] = mass_filt
            
        # Distribute the liquids
        if has_wash and self.wash_chems is not None:
            distribute_liquids(self.wash_chems)
        elif has_wash and self.wash_chems is None:
            raise ValueError("You must provide the IDs of the washing chemicals.")
        else:
            solvent = main_chemical_mass_basis(feed)
            distribute_liquids([solvent])
       
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
        ins = self.ins

        # Load output streams
        retentate, filtrate = self.outs

        # Mix the streams
        load = bst.Stream(units='kg/hr')
        load.mix_from(ins)

        # Add the filter total area
        design['Filter total area'] = self._calculate_filter_area(load,filtrate)

    def _calculate_filter_area(self, load, filtrate):
        # Obtain the viscosity
        if self.mu is not None:
            mu = self.mu
        else:
            try:
                mu = load.mu
            except RuntimeError:
                try:
                    # delete solids
                    for solid in self.solids:
                        load_like = bst.Stream()
                        load_like.copy_like(load)
                        load_like.imass[solid] = 0
                    # Try to calculate mu
                    mu = load_like.mu
                except RuntimeError:
                    # Use the viscosity of the main chemical if all fail
                    main_chem = main_chemical_mass_basis(load)
                    available_chems = load.available_chemicals
                    for chem in available_chems:
                        if chem.ID == main_chem:
                            mu = chem.mu('l',self.operating_T,self.operating_P)
                            break
                        else:
                            continue

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
            raise ValueError("Solid '{}' not found in the mixture (feed + washing).".format(e.args[0])) from None
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
        A_filter = self.design_results['Filter total area']

        # Calculate the baseline purchase costs for the Rotatory Vacuum Drum Filter
        ## The base cost accounts for a rotatory drum filter, vacuum with discharger,
        ## filtrate pumps, vacuum system, motor and drive.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        filter_purchase_cost = self.base_cost_filter * (A_filter/self.base_area_filter)**self.base_n_cost_filter
        self.baseline_purchase_costs['Rotatory Vacuum Drum Filter'] = filter_purchase_cost

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Rotatory Vacuum Drum Filter'] = self.F_M['Rotatory Vacuum Drum Filter'] = self.F_P['Rotatory Vacuum Drum Filter'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        delivery = 0.10
        installation = 0.80             # Filters
        instrumentation_control = 0.25  # Assumed from the range 0.08 - 0.50 mentioned on the book
        piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        bare_module = (1 + (delivery + installation + instrumentation_control + piping))
        self.F_BM['Rotatory Vacuum Drum Filter'] = bare_module

        ## Scale the costs using CEPCI
        CE_base = self.CE_base_filter
        self.baseline_purchase_costs['Rotatory Vacuum Drum Filter'] *= bst.CE/CE_base

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