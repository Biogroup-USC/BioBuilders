"""
"""
import biosteam as bst
from typing import Optional
import numpy as np

__all__ = (
    "SLEPFbySplit",
    "SLECbySplit"
)

class SLEPFbySplit(bst.Unit):
    """

    Create a Solid-Liquid extraction modelled as a CSTR for mixing the solid with the solvent and a 
    pressure filter that separates the two phases. The extraction is modelled based on the split
    factor which represents the mass of certain compound extracted per its input mass. Moreover, 
    it is important to remark that the amount of washing stream used in the filtration, which is 
    retained by te solid, is calculated using the moisture parameter.           

    - ID (str): Name of the unit.

    - ins (list): List of input streams (BioSTEAM object). This unit has 3 inputs. Note that the Filter_Washing stream must be an empty one.
    [Feed, Solvent, Filter_Washing]

    - outs (list): List of output streams (BioSTEAM object). This unit has 2 outputs. [Extract, Raffinate]

    - sfi (dict): Dictionary with the following structure: {"A": 0.5, "B": 0.9}. This means that 50% of A and 90% of B will be extracted by the 
    solvent.

    - moisture_content (float): percentage of washing stream retained in the solids. Default to 0.40 kg of washing stream per kg of dry solids.

    - washing_chem (dict): Dictionary with the following structure:  {"C": 2, "D": 4}. This means that the steam used to wash the solids during the filtration
    will have a flow of C and D which is 2 and 4 times the flow of Feed, respectively.

    - tau (float): Residence time in h.

    - kW_per_m3 (float): The power consumption due to stirring. The default is set to 0.1803 kW/m3 using the Piccino calculation for 1 m3 reactor: 
    http://dx.doi.org/10.1016/j.jclepro.2016.06.164.

    - operating_T (float): The operating temperature is set to 298.15 K by default.

    """
    # Inlets
    _N_ins = 3

    # Outlets
    _N_outs = 2

    # Set the default moisture content (kg washing stream / kg dry solids)
    moisture_content_default: Optional[float] = 0.40

    # Set the default washing chem and its kg / kg solids 
    wash_chem_default = {'Ethanol': 80}                                   #TODO ITBQ is probably not using pure ethanol --> get more info about it for setting the default

    # Default operating temperature (k)
    T_default: Optional[float] = 273.15 + 25

    # Default residence time (tau)
    tau_default: Optional[float] = None

    # Default power consumption by agitation (kW/m3)
    kW_per_m3_default: Optional[float] = (0.79*1000*(1.417**3)*(0.373**5))/90      # using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164

    def _init(self,
              sfi: dict = None,
              moisture_content: float = None,
              washing_chem: dict = None,
              tau: float = None,
              kW_per_m3: Optional[float] = None,
              operating_T: Optional[float] = None
              ):
        """
        """
        self.sfi = sfi
        self.moisture = self.moisture_content_default if moisture_content is None else moisture_content
        self.wash_chem = self.wash_chem_default if washing_chem is None else washing_chem
        self.tau = self.tau_default if tau is None else tau
        self.operating_T = self.T_default if operating_T is None else operating_T
        self.kW_per_m3 = self.kW_per_m3_default if kW_per_m3 is None else kW_per_m3
        
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

        # Run the solid liquid extraction using split factors
        Extract.copy_flow(Solvent)
        Extract.T = self.operating_T
        Raffinate.copy_flow(Feed)
        Raffinate.phase = Feed.phase
        Raffinate.T = self.operating_T
        for chem in self.sfi.keys():
            Extract.imass[chem] = self.sfi[chem] * Feed.imass[chem] + Solvent.imass[chem]   # It takes into account if there is any chemical in both Solvent and Feed
            Raffinate.imass[chem] = (1-self.sfi[chem])* Feed.imass[chem]                    # assuming all the solvent and solutes are washed during the filtration 
        
        # Run the pressure filtration assuming all the solvent phase is washed from the solids
        ## Calculate the remaining chemical from Filter_Washing stream in the solids using the moisture
        ### Create a mock stream to manage the retained chemicals
        Washing_Fluid_Retained = bst.Stream('Mock')
        Washing_Fluid_Retained.copy_like(Filter_Washing)

        ### Retained flow as RF = moisture * Feed (Dry solids)
        Retained_Flow = self.moisture * Raffinate.get_total_flow('kg/hr')

        ### The retained ratio is calculated as (retained flow)/(total washing flow)
        Retained_Ratio = Retained_Flow/Filter_Washing.get_total_flow('kg/hr')

        ### Get the amount of each chemical retained 
        Washing_Fluid_Retained.F_mass = Filter_Washing.F_mass * Retained_Ratio
        
        ## Once the amount of retained washing stream is calculated, the flow of each chemical is set in both outlets
        for chem in self.wash_chem.keys():
            Raffinate.imass[chem] = Washing_Fluid_Retained.imass[chem]
            Extract.imass[chem] = Filter_Washing.imass[chem] - Raffinate.imass[chem] + Extract.imass[chem]

            # Check if there is enough amount in the Filter_Washing stream to satisfy the moisture content
            if Extract.imass[chem] <= 0:
                raise ValueError("The amount of {} from {} is not enough to achieve the moisture provided {}". format(chem, Filter_Washing.ID, self.moisture))

    def _design(self):
        pass

    def _cost(self):
        pass

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
            
    """
    # Inlets
    _N_ins = 2

    # Outlets
    _N_outs = 2

    def _init(self,
              sfi: dict = None,
              moisture_content: float = 0.40,
              tau: float = None,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              kW_per_m3_reactor: float = None,
              kWh_per_kg_centrifuge: float = None,
              V_wf: float = None,
              V_max: float = None
              ):
        """
        """
        self.sfi = sfi
        self.moisture = moisture_content
        self.tau = tau
        self.operating_T = operating_T
        self.operating_P = operating_P
        self._kW_per_m3 = kW_per_m3_reactor
        self._kWh_per_kg = kWh_per_kg_centrifuge
        self._V_wf = V_wf
        self._V_max = V_max
        self._Base_Cost_Tank = None
        self._Base_Cost_Centrifuge = None
        self._Base_Volume_Tank = None
        self._Base_Diameter_Centrifuge = None
        self._Base_n_Cost_Tank = None
        self._Base_n_Cost_Centrifuge = None
        self._CE_Base_Tank = None
        self._CE_Base_Centrifuge = None

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

    def _design(self):
        """
        """
        # Load the dictionary of results
        Design = self.design_results

        # Load the streams of the unit and mix them
        Ins1, Ins2 = self.ins
        Outs1, Outs1 = self.outs
        Load = bst.Stream(units = 'kg/hr')
        Load.mix_from([Ins1,Ins2], energy_balance = True)

        # Load the parameters
        V_wf = self.V_wf

        # Calculate the mixing tank volume
        Inputs_F_Vol = (Load.F_vol)
        V_0 = Inputs_F_Vol * self.tau

        # Add the reactor volume
        Design['Mixing tank volume'] = V_0/V_wf

        # Calculate the flow rate and the number of centrifuges
        Centrifuge_Flow_Rate = Load.F_vol

        # Calculate the number of centrifuges
        Maximum_Flow_Rate = 2.2 * (60/100)                  #Change it based on the new centrifuge
        if Centrifuge_Flow_Rate > Maximum_Flow_Rate:
            N = Centrifuge_Flow_Rate/Maximum_Flow_Rate
            Design['Centrifuge flow rate'] = Centrifuge_Flow_Rate/N
            self.parallel['Centrifuge'] = N
        else:
            Design['Centrifuge flow rate'] = Centrifuge_Flow_Rate

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
    def Base_Cost_Tank(self):
        """
        """
        if self._Base_Cost_Tank is None:
            self._Base_Cost_Tank = 75000     # USD
        return self._Base_Cost_Tank   

    @Base_Cost_Tank.setter
    def Base_Cost_Tank(self, value):
        """
        """
        self._Base_Cost_Tank = value

    @property
    def Base_Volume_Tank(self):
        """
        """
        if self._Base_Volume_Tank is None:
            self._Base_Volume_Tank = 3.0    # m3
        return self._Base_Volume_Tank
    
    @Base_Volume_Tank.setter
    def Base_Volume_Tank(self, value):
        """
        """
        self._Base_Volume_Tank = value

    @property
    def Base_n_Cost_Tank(self):
        """
        """
        if self._Base_n_Cost_Tank is None:
            self._Base_n_Cost_Tank = 0.53
        return self._Base_n_Cost_Tank
    
    @Base_n_Cost_Tank.setter
    def Base_n_Cost_Tank(self, value):
        """
        """
        self._Base_n_Cost_Tank = value
    
    @property
    def CE_Base_Tank(self):
        """
        """
        if self._CE_Base_Tank is None:
            self._CE_Base_Tank = 1000.0
        return self._CE_Base_Tank
    
    @CE_Base_Tank.setter
    def CE_Base_Tank(self, value):
        """
        """
        self._CE_Base_Tank = value

    @property
    def Base_Cost_Centrifuge(self):
        """
        """
        if self._Base_Cost_Centrifuge is None:
            self._Base_Cost_Centrifuge = 0     #TODO add it
        return self._Base_Cost_Centrifuge   

    @Base_Cost_Centrifuge.setter
    def Base_Cost_Centrifuge(self, value):
        """
        """
        self._Base_Cost_Centrifuge = value

    @property
    def Base_Diameter_Centrifuge(self):
        """
        """
        if self._Base_Diameter_Centrifuge is None:
            self._Base_Diameter_Centrifuge = 0    #TODO add it
        return self._Base_Diameter_Centrifuge
    
    @Base_Diameter_Centrifuge.setter
    def Base_Diameter_Centrifuge(self, value):
        """
        """
        self._Base_Diameter_Centrifuge = value

    @property
    def Base_n_Cost_Centrifuge(self):
        """
        """
        if self._Base_n_Cost_Centrifuge is None:
            self._Base_n_Cost_Centrifuge = 0    #TODO add it
        return self._Base_n_Cost_Centrifuge
    
    @Base_n_Cost_Centrifuge.setter
    def Base_n_Cost_Centrifuge(self, value):
        """
        """
        self._Base_n_Cost_Centrifuge = value
    
    @property
    def CE_Base_Centrifuge(self):
        """
        """
        if self._CE_Base_Centrifuge is None:
            self._CE_Base_Centrifuge = 0       #TODO add it
        return self._CE_Base_Centrifuge    

    def _cost(self):
        """
        """
        # Load all the design parameters needed to calculate the costs
        V_Tank = self.design_results['Mixing tank volume']
        Flow_Centrifuge = self.design_results['Centrifuge flow rate']

        # Calculate the baseline purchase cost for the mixing tank
        ## The base cost accounts for jacketed agitated vessel.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Mixing_Tank_Purchase_Cost = 75000 * (V_Tank/3)**0.53
        self.baseline_purchase_costs['Mixing Tank'] = Mixing_Tank_Purchase_Cost

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Mixing Tank'] = self.F_M['Mixing Tank'] = self.F_P['Mixing Tank'] = 1

        ## The installation costs are assumed to be 0
        self.F_BM['Mixing Tank'] = 1

        ## Scale the costs using CEPCI
        CE_Base = 1000
        self.baseline_purchase_costs['Mixing Tank'] *= bst.CE/CE_Base

        # Calculate the baseline purchase costs for the centrifuge
        ## The base cost accounts for a centrifuge used in continuous extraction including flexible connections,
        ## explosion-proof motor, variable speed drive, ammeter and tachometer.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Flow_Centrifuge_L_s = Flow_Centrifuge * (1000/60)                       #TODO change it
        Centrifuge_Purchase_Cost = 220000 * (Flow_Centrifuge_L_s/2.2)**0.25     #TODO change it for Basket centrifuge
        self.baseline_purchase_costs['Centrifuge'] = Centrifuge_Purchase_Cost

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Centrifuge'] = self.F_M['Centrifuge'] = self.F_P['Centrifuge'] = 1

        ## The installation costs are assumed to be 0
        self.F_BM['Centrifuge'] = 1

        ## Scale the costs using CEPCI
        CE_Base = 1000
        self.baseline_purchase_costs['Centrifuge'] *= bst.CE/CE_Base