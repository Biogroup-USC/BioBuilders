"""
"""
import biosteam as bst
from typing import Optional

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

class SLECbySplit(bst.Unit):                    #TODO change the documentation                                                
    """ 

    Create a Solid-Liquid extraction modelled as a CSTR for mixing the solid with the solvent and a 
    pressure filter that separates the two phases. The extraction is modelled based on the split
    factor which represents the mass of certain compound extracted per its input mass. Moreover, 
    it is important to remark that the amount of washing stream used in the filtration, which is 
    retained by te solid, is calculated using the moisture parameter.           

    - ID (str): Name of the unit.
    

    - ins (list): List of input streams (BioSTEAM object). This unit has 2 inputs. [Feed, Solvent]
    

    - outs (list): List of output streams (BioSTEAM object). This unit has 2 outputs. [Extract, Raffinate]
    

    - sfi (dict): Dictionary with the following structure: {"A": 0.5, "B": 0.9}. This means that 50% of A and 90% of B will be extracted by the 
    solvent.  
   

    - moisture_content (float): percentage of solvent retained in the solids. Default to 0.40 kg of solvent per kg of dry solids.
   

    - tau (float):Residence time in h.

    
    - kW_per_m3 (float): The power consumption due to stirring. The default is set to 0.1803 kW/m3 using the Piccino calculation for 1 m3 reactor: 
    http://dx.doi.org/10.1016/j.jclepro.2016.06.164.
    

    - operating_T (float): The operating temperature is set to 298.15 K by default.
    

    """
    # Inlets
    _N_ins = 2

    # Outlets
    _N_outs = 2

    # Set the default moisture_content (kg solvent / kg dry solids)                                     
    moisture_content_default: Optional[float] = 0.40

    # Default operating temperature (k)
    T_default: Optional[float] = 273.15 + 25

    # Default residence time (tau)
    tau_default: Optional[float] = None

    # Default power consumption by agitation (kW/m3)
    kW_per_m3_default: Optional[float] = (0.79*1000*(1.417**3)*(0.373**5))/90      # using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164

    # Default power consumption by centrifuge (kWh/kg)
    kW_per_kg_default: Optional[float] = 0.01                                      # kWh/ton = 10 --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164 

    def _init(self,
              sfi: dict = None,
              moisture_content: float = None,
              tau: float = None,
              kW_per_m3: Optional[float] = None,
              kW_centrifuge: Optional[float] = None,
              operating_T: Optional[float] = None
              ):
        """
        """
        self.sfi = sfi
        self.moisture = self.moisture_content_default if moisture_content is None else moisture_content
        self.tau = self.tau_default if tau is None else tau
        self.operating_T = self.T_default if operating_T is None else operating_T
        self.kW_per_m3 = self.kW_per_m3_default if kW_per_m3 is None else kW_per_m3
        self.kW_per_kg = self.kW_per_kg_default if kW_centrifuge is None else kW_centrifuge
        
    def _run(self):
        """
        """
        # Define the inlet streams
        Feed = self.ins[0]
        Solvent = self.ins[1]

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
            Raffinate.imass[chem] = (1-self.sfi[chem])* Feed.imass[chem]                    
        
        # Run the centrifugation 
        ## Calculate the ratio of solvent retained
        Solvent_Retained_Ratio = (self.moisture * Raffinate.get_total_flow('kg/hr'))/Solvent.get_total_flow('kg/hr')
        
        ## Create a mock stream to store the chemicals retained
        Solvent_Retained = bst.Stream('Mock', units = 'kg/hr')
        Solvent_Retained.copy_like(Solvent)
        Solvent_Retained.F_mass = Solvent_Retained_Ratio * Solvent.F_mass

        ## Add the solvent retained to the raffinate
        Chems_ID_Solvent = []
        for element in Solvent_Retained.available_chemicals:
            Chem_ID = element.ID
            Chems_ID_Solvent.append(Chem_ID)
        for chem in Chems_ID_Solvent:
            Raffinate.imass[chem] = Raffinate.imass[chem] + Solvent_Retained.imass[chem]
            Extract.imass[chem] = Extract.imass[chem] - Solvent_Retained.imass[chem]
            if Solvent.imass[chem] != Raffinate.imass[chem] + Extract.imass[chem]:
                raise ValueError("The amount of {} in {} is not enough to match the moisture content provided".format(chem, Solvent.ID))
            elif Raffinate.imass[chem] or Extract.imass[chem] > 0:
                continue
            else:
                raise ValueError("There is negative flows in this units because the solvent is not enough to match the moisture content")

    def _design(self):
        pass

    def _cost(self):
        pass
