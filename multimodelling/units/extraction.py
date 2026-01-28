"""
"""
import biosteam as bst
from biosteam.units.design_tools import PressureVessel
from ..tools.mathtools.unitsdiameter import calculate_centrifuge_diameter
from ..tools.mathtools.power import calculate_agitator_power
import numpy as np
import math
from typing import Literal

__all__ = (
    "ExtractionReactor",
    "LLESettler",
    "LiquidsSettler",
    "SLECbySplit",
    "LLEbySplit"
)

class ExtractionReactor(bst.Unit):
    """
    """
    # Number of inlet streams
    _N_ins = 2

    # Number of outlet streams
    _N_outs = 1

    _units = {
        'Reactor volume': 'm3',
        'Residence time (tau)': 'h',
        'Volumetric power': 'kW/m3',
    }

    def _init(self,
              extract_reaction: bst.Reaction | bst.ReactionSystem = None,
              tau: float = None,
              operating_T: float = None,
              operating_P: float = None,
              kW_per_m3: float = None,
              ):
        """
        """
        self.extract_react = extract_reaction
        self.tau = tau
        self.operating_T = operating_T if operating_T is not None else (273.15 + 25.0)
        self.operating_P = operating_P if operating_P is not None else 101325
        self.kW_per_m3 = kW_per_m3
        self._V_wf = None
        self._V_max = None
        self._base_cost = None
        self._base_volume = None
        self._base_n_cost = None
        self._CE_base = None
    
    def _run(self):
        """
        """
        # Define the inlet streams
        feed, solvent = self.ins

        # Define the outlet streams
        slurry, = self.outs

        # Mix the streams
        slurry.mix_from([feed, solvent])
        slurry.P = self.operating_P
        slurry.T = self.operating_T

        # Perform the reaction
        self.extract_react(slurry)

    @property
    def V_max(self):            # This value is selected because the range of the cost correlation is 3 - 90 m3
        """
        """
        if self._V_max is None:
            self._V_max = 80    #m3  
        return self._V_max
    
    @V_max.setter
    def V_max(self,value):
        """
        """
        self._V_max = value

    @property
    def V_wf(self):
        """
        """
        if self._V_wf is None:
            self._V_wf = 0.80
        return self._V_wf
    
    @V_wf.setter
    def V_wf(self,value):
        """
        """
        self._V_wf = value

    def _design(self):
        """
        """
        # Load the dictionary of results
        design = self.design_results

        # Load the input streams of the unit and mix them
        feed, solvent = self.ins

        # Load the parameters
        V_wf = self.V_wf
        tau = self.tau

        # Mix streams
        mixed = bst.Stream()
        mixed.mix_from([feed, solvent], energy_balance = True)
        
        # Calculate heat utility     
        Ti = mixed.T
        Tf = self.operating_T
        Cpi = mixed.Cp

        mixed.T = self.operating_T
        mixed.P = self.operating_P

        Cpf = mixed.Cp
        duty = ((Cpf + Cpi)/2) * mixed.F_mass * (Tf - Ti)
        self.add_heat_utility(duty, T_in = Ti, T_out = Tf)

        # Calculate reactor volume
        inputs_F_Vol = mixed.F_vol
        V_0 = inputs_F_Vol * tau

        # Calculate power utility
        if self.kW_per_m3 is not None:
            volumetric_power = self.kW_per_m3
            power = volumetric_power * V_0
        else:
            raise ValueError("kW_per_m3 must be provided to calculate power requirements."
                             "In case you have no data, use `agitator_volumetric_power_determination`"
                             "to stimate the volumetric power.")

        self.add_power_utility(power)

        # Add the reactor volume
        design['Reactor volume'] = V_0/V_wf

        # Add volumetric power
        design['Volumetric power'] = volumetric_power

        # Add tau
        design['Residence time (tau)'] = tau
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 75000     # USD
        return self._base_cost   

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_volume(self):
        """
        """
        if self._base_volume is None:
            self._base_volume = 3.0    # m3
        return self._base_volume
    
    @base_volume.setter
    def base_volume(self, value):
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
        # Load all the design parameters needed to calculate the costs
        V_Tank = self.design_results['Reactor volume']

        # Calculate the baseline purchase cost for the mixing tank
        ## The base cost accounts for jacketed agitated vessel.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Mixing_Tank_Purchase_Cost = self.base_cost * (V_Tank/self.base_volume)**self.base_n_cost
        self.baseline_purchase_costs['Mixing Tank'] = Mixing_Tank_Purchase_Cost

        ## The material, pressure and temperature factors are assumed to be 1
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
        self.baseline_purchase_costs['Mixing Tank'] *= bst.CE/self.CE_base

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class LiquidsSettler(bst.Unit, PressureVessel, isabstract=True):
    """
    Abstract Settler class for liquid-liquid extraction.
    
    Parameters
    ----------
    ins : 
        Inlet fluid with two liquid phases.
    outs : 
        * [0] Low density fluid.
        * [1] Heavy fluid.
    vessel_material='Carbon steel' : str, optional
        Vessel construction material.
    vessel_type='Horizontal': 'Horizontal' or 'Vertical', optional
        Vessel type.
    length_to_diameter=4 : float
        Length to diameter ratio.
    area_to_feed=0.1 : float
        Diameter * length per gpm of feed [ft2/gpm].
        
    """
    _N_ins = 1
    _N_outs = 2
    
    def _init(self, area_to_feed=0.1, 
              length_to_diameter=4,
              vessel_material='Carbon steel',
              vessel_type='Horizontal'):
        self.vessel_material = vessel_material
        self.vessel_type = vessel_type
        self.length_to_diameter = length_to_diameter #: Length to diameter ratio
        self.area_to_feed = area_to_feed #: [ft2/gpm] Diameter * length per gpm of feed

        # New properties for cost calculations
        self._base_cost = None
        self._base_n_cost = None
        self._base_flow = None
        self._CE_base = None
    
    @staticmethod
    def _default_vessel_type():
        return 'Horizontal'
    
    def _design(self):
        feed = self.ins[0]
        F_vol_gpm = feed.get_total_flow('gpm')
        area = self.area_to_feed * F_vol_gpm
        length_to_diameter = self.length_to_diameter
        P = feed.get_property('P', 'psi')
        D = (area / length_to_diameter) ** 0.5
        L = length_to_diameter * D
        self.design_results.update(self._vessel_design(P, D, L))
        self.design_results["Weight"]*= 0.454           # from lb to kg
        self.design_results["Length"]*= 0.3048          # from ft to m
        self.design_results["Diameter"]*= 0.3048        # from ft to m
        self.design_results["Wall thickness"]*= 0.0254  # from in to m
        self.design_results["Feed flow"] = feed.F_vol   # m3/h

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 190000            # USD
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_flow(self):
        """
        """
        if self._base_flow is None:
            self._base_flow = 12 * 3600 / 1000  # m3/h
        return self._base_flow

    @base_flow.setter
    def base_flow(self, value):
        """
        """
        self._base_flow = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.84
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
        # Load the design parameters
        Flow = self.design_results['Feed flow']

        # Calculate the baseline purchase cost for the decanter
        ## The cost account for am API Oil-water "skimmer" separator
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        LLE_Settler_Purchase_Cost = self.base_cost * (Flow/self.base_flow) ** self.base_n_cost
        self.baseline_purchase_costs['Settler'] = LLE_Settler_Purchase_Cost

        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D['Settler'] = self.F_M['Settler'] = self.F_P['Settler'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.60             # Metal tanks
        Instrumentation_Control = 0.50
        Piping = 0.68                   # Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Settler'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_Base = self.CE_base
        self.baseline_purchase_costs['Settler'] *= bst.CE/CE_Base

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class LLESettler(bst.LLEUnit, LiquidsSettler):
    """
    Create a LLESettler object that rigorously simulates liquid-liquid extraction.
    
    Parameters
    ----------
    ins : 
        Inlet fluid with two liquid phases.
    outs : 
        * [0] Low density fluid.
        * [1] Heavy fluid.
    vessel_material='Carbon steel' : str, optional
        Vessel construction material.
    vessel_type='Horizontal': 'Horizontal' or 'Vertical', optional
        Vessel type.
    length_to_diameter=4 : float, optional
        Length to diameter ratio.
    area_to_feed=0.1 : float, optional
        Diameter * length per gpm of feed [ft2/gpm].
    top_chemical=None : str, optional
        Identifier of chemical that will be favored in the low density phase.
    efficiency=1.0 : float
        Fraction of feed in liquid-liquid equilibrium
    cache_tolerance=1e-6 : float, optional
        Molar tolerance of cached partition coefficients.
    
    """
    line = 'Settler'
    _units = {
        "Feed flow": "m3/h",
        "Weight": "kg",
        "Length": "m",
        "Wall thickness": "m",
        "Diameter": "m"
    }
    def _init(self, 
            area_to_feed=0.1, 
            length_to_diameter=4,
            vessel_material='Carbon steel',
            vessel_type='Horizontal',
            top_chemical=None,
            efficiency=1.0,
            cache_tolerance=1e-6,
        ):
        bst.LLEUnit._init(self, top_chemical, efficiency)
        LiquidsSettler._init(self,area_to_feed=area_to_feed,length_to_diameter=length_to_diameter,vessel_material=vessel_material,vessel_type=vessel_type,)
        self.vessel_material = vessel_material
        self.vessel_type = vessel_type
        self.length_to_diameter = length_to_diameter
        self.area_to_feed = area_to_feed
        self.cache_tolerance = cache_tolerance

class SLECbySplit(bst.Unit):                                                
    """ 

    Create a unit that models a Solid-Liquid Extraction. 
    
    The SLE is modelled as an agitated tank to mix the solids and the solvent followed 
    by a centrifuge that separates the two phases. The volume of the vessel is calculated
    as V = In_flow * Tau.   

    Parameters
    ----------
    ID : str
        Name of the unit.
    ins : list 
        List of input streams (BioSTEAM object). This unit has 2 inputs. [Feed, Solvent]
    outs : list 
        List of output streams (BioSTEAM object). This unit has 2 outputs. [Extract, Raffinate]
    sfi : dict 
        Dictionary with the following structure: {"A": 0.5, "B": 0.9}. This means that 50% of A and 90% of B will be extracted by the 
        solvent.  
    moisture_content : float 
        Percentage of solvent retained in the solids. Default to 0.40 kg of solvent per kg of dry solids.
    tau : float
        Residence time in h.
    operating_T : float
        Operating temperature of this unit. Default to 298.15 K.
    operating_P : float
        Operating pressure of this unit. Default to 101325 Pa.
    solids_rho : float
        Density of the solids [kg/m3] to calculate the centrifuge diameter. This parameter allows to give a density for
        the solids that enters the solid-liquid extraction manually instead of calculating it using the BioSTEAM features.
    solvent_rho : float
        Density of the solvent [kg/m3] to calculate the centrifuge diameter. This parameter allows to give a density for
        the solids that enters the solid-liquid extraction manually instead of calculating it using the BioSTEAM features.
    
    Attributes
    ----------    
    kW_per_m3_reactor : float 
        The power consumption due to stirring. The default is set to 0.1803 kW/m3 using the Piccino calculation for 1 m3 reactor: 
        http://dx.doi.org/10.1016/j.jclepro.2016.06.164.
    kW_per_kg_centrifuge : float
        The power consumption of the centrifuge. The default is 0.010 kWh/ton.
    V_wf : float
        The working volume parameter represents the fraction of the reactor filled. Defaults to 0.80.
    V_max : float
        The maximum volume (m3) represents the limit of the tank dimension. Default to 80 m3. 
    max_diameter : float
        The maximum diameter of the centrifuge based on the cost correlations. Default to 1.25 m.
    particle_diameter : float
        Diameter of the solids. Default to 5e-4 m.
    centrifuge_rpm : float
        Rotational speed of the centrifuge. Default to 3000 rpm.
    centrifuge_height : float
        Height of the centrifuge' basket. Defaulto to 1 m.
    base_cost_tank : float
        Base cost of a jacketed mixing tank.
    base_volume_tank : float
        The volume of the jacketed mixing tank whose cost is the base cost.
    base_n_cost_tank : float
        Parameter n for the jacketed mixing tank used in the formula to scale costs.
    CE_base_tank : float
        CEPCI of the base cost.
    base_cost_centrifuge : float
        Base cost of a basket centrifuge.
    base_diameter_centrifuge : float
        The diameter of a basket centrifuge whose cost is the base cost.
    base_n_cost_centrifuge : float
        Parameter n for the basket centrifuge used in the formula to scale costs.
    CE_base_centrifuge : float
        CEPCI of the base cost.
             
    """
    # Inlets
    _N_ins = 2

    # Outlets
    _N_outs = 2

    def _init(self,
              sfi: dict = None,
              moisture_content: float = 0.40,
              solids : list = None,
              tau: float = None,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              kW_per_m3_reactor: float = None,
              kWh_per_kg_centrifuge: float = None,
              V_wf: float = None,
              V_max: float = None,
              max_diameter: float = None,
              particle_diameter: float = None,
              centrifuge_rpm: float = None,
              centrifuge_height: float = None,
              solids_rho: float = None,
              solvent_rho: float = None
              ):
        """
        """
        self.sfi = sfi
        self.moisture = moisture_content
        self.solids = solids
        self.solids_rho = solids_rho
        self.solvent_rho = solvent_rho
        self.tau = tau
        self.operating_T = operating_T
        self.operating_P = operating_P
        self._kW_per_m3 = kW_per_m3_reactor
        self._kWh_per_kg = kWh_per_kg_centrifuge
        self._V_wf = V_wf
        self._V_max = V_max
        self._max_diameter = max_diameter
        self._particle_diameter = particle_diameter
        self._centrifuge_rpm = centrifuge_rpm
        self._centrifuge_height = centrifuge_height
        self._base_cost_tank = None
        self._base_cost_centrifuge = None
        self._base_volume_tank = None
        self._base_diameter_centrifuge = None
        self._base_n_cost_tank = None
        self._base_n_cost_centrifuge = None
        self._CE_base_tank = None
        self._CE_base_centrifuge = None

    def _run(self):
        """
        """
        # Define the inlet streams
        Feed = self.ins[0]
        Solvent = self.ins[1]

        # Define the outlet streams
        Extract = self.outs[0]
        Raffinate = self.outs[1]
        Extract.T = self.operating_T
        Raffinate.T = self.operating_T

        # The mixture of streams is simulated in the design section to perform the heat utilities.
        # The mix is simulated here copying the Feed and Solvent streams as Raffinate and Extract
        Extract.copy_like(Solvent)
        Raffinate.copy_like(Feed)

        # Simulate the separation using a centrifuge
        for chem in self.sfi.keys():
            Extract.imass[chem] = self.sfi[chem] * Feed.imass[chem]
            Raffinate.imass[chem] = (1-self.sfi[chem]) * Feed.imass[chem]
        
        ## Calculate the amount of solvent retained
        Solvent_Retained = self.moisture * Raffinate.F_mass
        Solvent_Retained_Ratio = Solvent_Retained/Solvent.F_mass
        for chemobj in Solvent.available_chemicals:
            chem = chemobj.ID
            Extract.imass[chem] = (1-Solvent_Retained_Ratio) * Solvent.imass[chem]
            Raffinate.imass[chem] = Solvent_Retained_Ratio * Solvent.imass[chem]
            # Check if there is enough solvent to match the moisture content
            Solvent_Extract_plus_Raffinate = (Extract.imass[chem] + Raffinate.imass[chem])
            if not np.isclose(Solvent_Extract_plus_Raffinate, Solvent.imass[chem], rtol = 1e-5, atol = 1e-8):
               raise ValueError("There is not enough amount of {} in {} to match the moisture requeriments".format(chem, Solvent.ID))
        
    @property
    def kW_per_m3(self):
        """
        """
        if self._kW_per_m3 is None:
            self._kW_per_m3 = ((0.79*1000*(1.417**3)*(0.373**5))/90)/1  # kW/m3         using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kW_per_m3
    
    @kW_per_m3.setter
    def kW_per_m3(self, value):
        """
        """
        self._kW_per_m3 = value

    @property
    def kWh_per_kg(self):
        """
        """
        if self._kWh_per_kg is None:
            self._kWh_per_kg = 0.01 # kW/kg         kWh/ton = 10 --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164 
        return self._kWh_per_kg

    @kWh_per_kg.setter
    def kWh_per_kg(self, value):
        """
        """
        self._kWh_per_kg = value

    @property
    def V_wf(self):
        """
        """
        if self._V_wf is None:
            self._V_wf = 0.80
        return self._V_wf
    
    @V_wf.setter
    def V_wf(self,value):
        """
        """
        self._V_wf = value

    @property
    def V_max(self):            # This value is selected because the range of the cost correlation is 3 - 90 m3
        """
        """
        if self._V_max is None:
            self._V_max = 80    #m3  
        return self._V_max
    
    @V_max.setter
    def V_max(self,value):
        """
        """
        self._V_max = value

    @property
    def particle_diameter(self):
        """
        """
        if self._particle_diameter is None:
            self._particle_diameter = 5e-4
        return self._particle_diameter

    @particle_diameter.setter
    def particle_diameter(self, value):
        """
        """
        self._particle_diameter = value

    @property
    def centrifuge_rpm(self):
        """
        """
        if self._centrifuge_rpm is None:
            self._centrifuge_rpm = 1500     # rpm
        return self._centrifuge_rpm
    
    @centrifuge_rpm.setter
    def centrifuge_rpm(self, value):
        """
        """
        self._centrifuge_rpm = value
    
    @property
    def max_diameter(self):
        """
        """
        if self._max_diameter is None:
            self._max_diameter = 1.25       # m
        return self._max_diameter

    @max_diameter.setter
    def max_diameter(self, value):
        """
        """
        self._max_diameter = value

    @property
    def centrifuge_height(self):
        """
        """
        if self._centrifuge_height is None:
            self._centrifuge_height = 1      # m
        return self._centrifuge_height

    @centrifuge_height.setter
    def centrifuge_height(self, value):
        """
        """
        self._centrifuge_height = value

    def _design(self):
        """
        """
        # Load the dictionary of results
        Design = self.design_results

        # Load the streams of the unit and mix them
        Ins1, Ins2 = self.ins
        Outs1, Outs2 = self.outs
        Load = bst.Stream(units = 'kg/hr')
        Load.mix_from([Ins1,Ins2], energy_balance = True)

        # Load the parameters
        V_wf = self.V_wf

        # Calculate the mixing tank volume
        Inputs_F_Vol = (Load.F_vol)
        V_0 = Inputs_F_Vol * self.tau

        # Add the reactor volume
        Design['Mixing tank volume'] = V_0/V_wf

        # Calculate the diameter of the centrifuge              
        ## Calculate the density of the solids
        if self.solids_rho is not None:
            Rho_Solids = self.solids_rho
        else:    
            Rho_Solids = 0
            Outs2_Chemicals = Outs2.available_chemicals
            for solid in self.solids:
                for chem in Outs2_Chemicals:
                    if chem.ID == solid:
                        rho = chem.rho(Outs2.T)
                        Rho_Solids += rho
                    else:
                         continue
            Rho_Solids = Rho_Solids/len(self.solids)

        # Calculate the density of the solvent
        if self.solvent_rho is not None:
            Rho_Liquid = self.solvent_rho
        else:
            Rho_Liquid = Ins2.rho

        ## Estimate the diameter
        Centrifuge_Diameter, Centrifuge_Sigma = calculate_centrifuge_diameter(
            dp = self.particle_diameter,
            rho_p = Rho_Solids,
            rho_l = Rho_Liquid,
            mu = Ins2.mu,
            rpm = self.centrifuge_rpm,
            Q = Load.F_vol,
            H = self.centrifuge_height
        )

        # Calculate the number of centrifuges
        N_Centrifuge = Centrifuge_Diameter / self.max_diameter
        if N_Centrifuge <= 1:
            N_Centrifuge = 1
        else:
            N_Centrifuge = math.trunc(N_Centrifuge) + 1
            Centrifuge_Diameter = Centrifuge_Diameter/N_Centrifuge

        # Add the centrifige design parameters
        Design['Centrifuge diameter'] = Centrifuge_Diameter     
        Design['Centrifuge sigma'] = Centrifuge_Sigma
        self.parallel['Centrifuge'] = N_Centrifuge * 2  # Duplicate the centrifuge because they must be cleaned
        
        # Add the heat utility
        Tf = self.operating_T                   # K
        Ti = Load.T                             # K 
        Duty = Load.Cp * (Tf-Ti) * Load.F_mass  # kJ/h
        self.add_heat_utility(Duty, T_in = Ti, T_out = Tf)

        # Add power utility: Reactor agitation and centrifuge operation
        Power_Stirring = self.kW_per_m3 * Design['Mixing tank volume']
        Power_Centrifuge = self.kWh_per_kg * Load.F_mass
        self.add_power_utility(Power_Stirring)
        self.add_power_utility(Power_Centrifuge)

    @property
    def base_cost_tank(self):
        """
        """
        if self._base_cost_tank is None:
            self._base_cost_tank = 75000     # USD
        return self._base_cost_tank   

    @base_cost_tank.setter
    def base_cost_tank(self, value):
        """
        """
        self._base_cost_tank = value

    @property
    def base_volume_tank(self):
        """
        """
        if self._base_volume_tank is None:
            self._base_volume_tank = 3.0    # m3
        return self._base_volume_tank
    
    @base_volume_tank.setter
    def base_volume_tank(self, value):
        """
        """
        self._base_volume_tank = value

    @property
    def base_n_cost_tank(self):
        """
        """
        if self._base_n_cost_tank is None:
            self._base_n_cost_tank = 0.53
        return self._base_n_cost_tank
    
    @base_n_cost_tank.setter
    def base_n_cost_tank(self, value):
        """
        """
        self._base_n_cost_tank = value
    
    @property
    def CE_base_tank(self):
        """
        """
        if self._CE_base_tank is None:
            self._CE_base_tank = 1000.0
        return self._CE_base_tank
    
    @CE_base_tank.setter
    def CE_base_tank(self, value):
        """
        """
        self._CE_base_tank = value

    @property
    def base_cost_centrifuge(self):
        """
        """
        if self._base_cost_centrifuge is None:
            self._base_cost_centrifuge = 60000
        return self._base_cost_centrifuge   

    @base_cost_centrifuge.setter
    def base_cost_centrifuge(self, value):
        """
        """
        self._base_cost_centrifuge = value

    @property
    def base_diameter_centrifuge(self):
        """
        """
        if self._base_diameter_centrifuge is None:
            self._base_diameter_centrifuge = 0.060
        return self._base_diameter_centrifuge
    
    @base_diameter_centrifuge.setter
    def base_diameter_centrifuge(self, value):
        """
        """
        self._base_diameter_centrifuge = value

    @property
    def base_n_cost_centrifuge(self):
        """
        """
        if self._base_n_cost_centrifuge is None:
            self._base_n_cost_centrifuge = 1.04
        return self._base_n_cost_centrifuge
    
    @base_n_cost_centrifuge.setter
    def base_n_cost_centrifuge(self, value):
        """
        """
        self._base_n_cost_centrifuge = value
    
    @property
    def CE_base_centrifuge(self):
        """
        """
        if self._CE_base_centrifuge is None:
            self._CE_base_centrifuge = 1000
        return self._CE_base_centrifuge    

    def _cost(self):
        """
        """
        # Load all the design parameters needed to calculate the costs
        V_Tank = self.design_results['Mixing tank volume']
        Centrifuge_Diameter = self.design_results['Centrifuge diameter']

        # Calculate the baseline purchase cost for the mixing tank
        ## The base cost accounts for jacketed agitated vessel.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Mixing_Tank_Purchase_Cost = self.base_cost_tank * (V_Tank/self.base_volume_tank)**self.base_n_cost_tank
        self.baseline_purchase_costs['Mixing Tank'] = Mixing_Tank_Purchase_Cost

        ## The material, pressure and temperature factors are assumed to be 1
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
        self.baseline_purchase_costs['Mixing Tank'] *= bst.CE/self.CE_base_tank

        # Calculate the baseline purchase costs for the centrifuge
        ## The base cost accounts for a vertical basket centrifuge with batch top discharge. Note that
        ## motor and drive are excluded from this correlation.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Centrifuge_Purchase_Cost = self.base_cost_centrifuge * (Centrifuge_Diameter/self.base_diameter_centrifuge)**self.base_n_cost_centrifuge
        self.baseline_purchase_costs['Centrifuge'] = Centrifuge_Purchase_Cost * self.parallel['Centrifuge']

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Centrifuge'] = self.F_M['Centrifuge'] = self.F_P['Centrifuge'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.40             # Centrifugal separators
        Instrumentation_Control = 0.25  # Assumed from the range 0.08 - 0.50 mentioned on the book
        Piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Centrifuge'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_Base = 1000
        self.baseline_purchase_costs['Centrifuge'] *= bst.CE/CE_Base

class LLEbySplit(bst.Unit):
    """
    """
    def _init(self):
        pass

    def _run(self):
        pass

    def _design(self):
        pass

    def _cost(self):
        pass