"""
"""
import biosteam as bst
from ..mathtools.unitsdiameter import calculate_centrifuge_diameter
import numpy as np
import math

__all__ = (
    "SLEPFbySplit",
    "SLECbySplit"
)

class SLEPFbySplit(bst.Unit):
    """

    Create a Solid-Liquid extraction modelled as a CSTR with a pressure filter.

    The extraction is modelled based on the split factor which represents the mass of certain 
    compound extracted per its input mass. Moreover, it is important to remark that the amount 
    of washing stream used in the filtration, which is retained by te solid, is calculated using 
    the moisture parameter.           

    Parameters
    ----------
    ID : str
        Name of the unit.
    ins : list
        List of input streams (BioSTEAM object). This unit has 3 inputs.[Feed, Solvent, Filter_Washing]
    outs : list
        List of output streams (BioSTEAM object). This unit has 2 outputs. [Extract, Raffinate]
    sfi : dict
        Dictionary with the following structure: {"A": 0.5, "B": 0.9}. This means that 50% of A and 90% of B will be 
        extracted by the solvent.
    moisture_content : float
        percentage of washing stream retained in the solids. Default to 0.40 kg of washing stream per kg of dry solids.
    washing_chem : dict
        Dictionary with the following structure:  {"C": 2, "D": 4}. This means that the steam used to wash the solids 
        during the filtration will have a flow of C and D which is 2 and 4 times the flow of Feed, respectively.
    tau : float 
        Residence time in h.
    operating_T : float
        The operating temperature is set to 298.15 K by default.
    operating_P : float
        The operating pressure is set to 101325 bar by default.
    
    Attributes
    ----------
    kW_per_m3 : (float)
        The power consumption due to stirring. The default is set to 0.1803 kW/m3 using the Piccino calculation for 1 m3 
        reactor: http://dx.doi.org/10.1016/j.jclepro.2016.06.164.
    base_cost_tank : float
        Base cost of a jacketed mixing tank.
    base_volume_tank : float
        The volume of the jacketed mixing tank whose cost is the base cost.
    base_n_cost_tank : float
        Parameter n for the jacketed mixing tank used in the formula to scale costs.
    CE_base_tank : float
        CEPCI of the base cost.
        
    """
    # Inlets
    _N_ins = 3

    # Outlets
    _N_outs = 2

    # Set the default washing chem and its kg / kg solids 
    wash_chem_default = {
        'Ethanol': 64,
        'Water': 16
    }

    def _init(self,
              sfi: dict = None,
              moisture_content: float = 0.40,
              washing_chem: dict = None,
              tau: float = 0.5,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              kW_per_m3: float = None,
              ):
        """
        """
        self.sfi = sfi
        self.moisture = moisture_content
        self.wash_chem = washing_chem if washing_chem is not None else self.wash_chem_default
        self.tau = tau
        self.operating_T = operating_T
        self.operating_P = operating_P
        self._kW_per_m3 = kW_per_m3
        self._V_wf = None
        self._V_max = None
        self._base_cost_tank = None
        self._base_volume_tank = None
        self._base_n_cost_tank = None
        self._CE_base_tank = None

    def _run(self):
        """
        """
        # Define the inlet streams
        Feed = self.ins[0]
        Solvent = self.ins[1]
        Filter_Washing = self.ins[2]
        
        # Define the washing chemical
        for key in self.wash_chem.keys():
            Filter_Washing.imass[key] = self.wash_chem[key] * Feed.get_total_flow('kg/hr')

        # Define the outlet streams
        Extract = self.outs[0]
        Raffinate = self.outs[1]

        # The mixture of streams is simulated in the design section to perform the heat utilities.
        # The mix is simulated here copying the Feed and Solvent streams as Raffinate and Extract
        Extract.copy_flow(Solvent)
        Extract.T = self.operating_T
        Extract.P = self.operating_P
        Extract.phase = 'l'
        Raffinate.copy_flow(Feed)
        Raffinate.phase = 's'
        Raffinate.T = self.operating_T
        Raffinate.P = self.operating_P

        # Simulate the separation using a pressure filter
        for chem in self.sfi.keys():
            Extract.imass[chem] = self.sfi[chem] * Feed.imass[chem] + Solvent.imass[chem]   # It takes into account if there is any chemical in both Solvent and Feed
            Raffinate.imass[chem] = (1-self.sfi[chem])* Feed.imass[chem]                    # assuming all the solvent and solutes are washed during the filtration 
        
        # Calculate the amount of solvent retained
        solvent_retained = self.moisture * Raffinate.F_mass
        solvent_retained_ratio = solvent_retained/Solvent.F_mass
        for chemobj in Solvent.available_chemicals:
            chem = chemobj.ID
            Extract.imass[chem] = (1-solvent_retained_ratio) * Solvent.imass[chem]
            Raffinate.imass[chem] = solvent_retained_ratio * Solvent.imass[chem]
            # Check if there is enough solvent to match the moisture content
            solvent_extract_plus_raffinate = (Extract.imass[chem] + Raffinate.imass[chem])
            if not np.isclose(solvent_extract_plus_raffinate, Solvent.imass[chem], rtol = 1e-5, atol = 1e-8):
               raise ValueError("There is not enough amount of {} in {} to match the moisture requeriments".format(chem, Solvent.ID))

    @property
    def kW_per_m3(self):
        """
        """
        if self._kW_per_m3 is None:
            self._kW_per_m3 = (0.79*1000*(1.417**3)*(0.373**5))/90  # using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kW_per_m3
    
    @kW_per_m3.setter
    def kW_per_m3(self,value):
        """
        """
        self._kW_per_m3 = value

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
        Ins1 = self.ins[0]
        Ins2 = self.ins[1]
        Load = bst.Stream(units = 'kg/hr')
        Load.mix_from([Ins1,Ins2], energy_balance = True)

        # Load the parameters
        V_wf = self.V_wf

        # Calculate the mixing tank volume
        Inputs_F_Vol = (Load.F_vol)
        V_0 = Inputs_F_Vol * self.tau

        # Add the reactor volume
        design['Mixing tank volume'] = V_0/V_wf

        # Calculate the filter area
        
    
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