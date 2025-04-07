"""
"""
import biosteam as bst

__all__ = ("Dryer",)

class Dryer(bst.Unit):
    """

    This class creates a Dryer object which simulates the drying process of 
    solids considering the split factor of each volatile. This factor is 
    considered as the remaining fraction of each chemical in the solid.

    ARGUMENTS:

    - ID (str): This ID refers to the name of this unit.

    - ins (list): List of input streams. In this case, there is 2 inputs.
    [Wet_Solids, Hot_Gas]

    - outs (list): List of output streams. In this case, there is 2 outputs. 
    However, the losses stream could be avoided when no losses are being considering.
    [Dry_Solids, Vapor]

    - splitfactor (dict): This dictionary contains a pair "chemical": value which
    value refers to the amount of chemical remaining in the solids after the drying.
    So, the key-value pair "Water": 0.8 g/g indicates that 20% of the water remains in
    the solid after this stage. Note that the values of the non volatiles can be 
    omitted

    - gascomposition (list): the gas composition parameter is a list of tuples with the
    following structure: gascomposition = [('N2', 0.79),('O2', 0.21)]. This example is 
    the default value for Hot_Gas and corresponds to air composition.

    - gsration (float): the gas-solids ratio represents the ratio between the Hot_Gas mass
    flow and the Wet_Solids mass flow. This is used to calculate the amount of Hot_Gas used

    Note that the Wet_Solids is the only stream which has to contain values for the mass flow
    of each chemical. 

    """

    _N_ins = 2
    _N_outs = 2
    _units = {'Mass flow':'kg/hr'}
    
    def _init(self, splitfactor: dict = None, gascomposition = None, gsratio = 5.0):
        # The _init method is used to add input parameters to the AbstractUnit
        self.sfi = splitfactor
        self.gas_composition = gascomposition
        self.gas_solids_ratio = gsratio
        self._energy_consumption = None

    def _run(self):
        """
        
        This method runs the unit. The Dryer mass balance is simulated following the next equation:
        Output = sfi * Input {sfi = sfi for Dry_Solids and sfi = (1-sfi) for Vapor}
        

        """
        # Defining the inlet
        Feed, Hot_Gas = self.ins
        if self.gas_composition is None:
            self.gas_composition = [('N2', 0.79), ('O2', 0.21)]
        Hot_Gas_Flow = self.gas_solids_ratio * Feed.get_total_flow('kg/hr')
        for ID, x in self.gas_composition:
            Hot_Gas.imass[ID] = x * Hot_Gas_Flow
        #Defining the Outlet
        Dry_Solids = self.outs[0]
        Vapor = self.outs[1]
        Vapor.copy_like(Hot_Gas)

        # Running the Unit
        ## This Unit is simulated basically as OUT = sfi * IN where the sfi represents the amount of volatiles remaining
        Dry_Solids.copy_like(Feed)
        for chem in self.sfi.keys():
            Dry_Solids.imass[chem] = self.sfi[chem] * Feed.imass[chem]
            Vapor.imass[chem] = (1-self.sfi[chem]) * Feed.imass[chem] + Hot_Gas.imass[chem]
        
        ## Calculating the energy requirements                              #TODO Add the energy balance --> Hvap and Cp of mixture 

    @property
    def energy_consumption(self):
        """
        
        """
        if self._energy_consumption is None:
            self._energy_consumption = []
        return self._energy_consumption
        
    def _design(self):
        # Add heat utility requirement
        #self.heat_utilities[0]()                                            #TODO Add the heat utility
        pass

    def _cost(self):
        pass