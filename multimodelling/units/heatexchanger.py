"""
"""
import biosteam as bst
from ..tools.mathtools.logmean import log_mean

__all__ = ("ShellHeatExchanger",)

class ShellHeatExchanger(bst.Unit):
    """
    
    Create a Shell heat exchanger object which is modeled as a vessel. This unit increments the         #TODO redefine the model when the design is completed 
    temperature of the inlet stream. The energy consumed to cool down the stream or to heat it up 
    is calculated as kWh or kWh/kg using the hydraulic residence time which is 10 min by default.

    Parameters
    ----------
    ID : str
        This refers to the name of the unit.

    ins : list
        List of input streams. In this case, there is only 1 input.

    outs : list 
        List of output streams. In this case, there is 1 output.
    
    Tout : float
        This parameter is the temperature of the cold fluid in the output of the heat exchanger.
    
    Cp : float
        The Calorific Power is used when BioSTEAM cannot get the Cp from the Chemicals of each stream.
        This is important because sometimes, there is no data for certain compounds. [kJ/(kg*K)]
    
    U : float
        Overall heat-transfer coefficient. The value is 1500 by default. [W/(m2*ºC)]    # https://doi.org/10.1016/B978-0-08-102599-4.00012-6

    Attributes
    ----------
    energy_balance_type : str
        Calculate how the energy consumption is calculated:
            - 'kWh/kg'
            - 'kWh'

    tau : float
        Time of residence inside the heat exchanger.
    
    heat_consumption : float
        Heating consumption. The units are either kWh or kWh/kg.
    
    cool_consumption : float
        Cooling consumption. The units are either kWh or kWh/kg.
    
    base_cost : float
        The cost (USD) of a reactor which volume corresponds to the base volume.

    base_n_cost : float
        The parameter n in the expression: base_cost * (area/base_area)**n.

    base_area : float
        The area (m2) of a heat exchanger whose cost is the base_cost.

    CE_base : float
        The CEPCI which corresponds with the base_cost
    

    """                            
    _N_ins = 1
    _N_outs = 1
    _units = {
        'Area': 'm2'
    }

    def _init(self, Tout: float = None, Cp: float = None, U: float = None): #TODO document U parameter    
        if Tout is None:
            raise ValueError("A Tout must be provided")        
        self.Cp = Cp
        self.Tout = Tout
        self.U = U if U is not None else 1500 # set by default to steam (hot) - water (cold) https://doi.org/10.1016/B978-0-08-102599-4.00012-6 
        self._energy_balance_type = None
        self._tau = None
        self._heat_consumption = None
        self._cool_consumption = None
        self._base_cost = None
        self._base_n_cost = None
        self._CE_base = None
        self._base_area = None
                                           
    @property
    def energy_balance_type(self):
        if self._energy_balance_type is None:
            self._energy_balance_type = 'kWh/kg'
        return self._energy_balance_type
    
    @energy_balance_type.setter
    def energy_balance_type(self, units: str = None):
        """
        
        This setter is used to choose between calculating the energy consumption
        in kWh/kg or kWh.

        """
        if units is None:
            raise ValueError("{} is not an accepted value.".format(units))
        elif not isinstance(units, str):
            raise ValueError("The new value must be a string: 'kWh/kg' or 'kWh'")
        else:
            self._energy_balance_type = units

    @property
    def tau(self):
        if self._tau is None:
            self._tau = 10/60   # h (2 times the defined by UNIBO)
        return self._tau
    
    @tau.setter
    def tau(self, tau: float = None):
        """
        
        This setter is used to provide the residence time of the fluid in the 
        Shell Heat Exchanger.
        
        """
        if tau is None:
            raise ValueError("The hydraulic residence time must be provided")
        elif tau <= 0:
            raise ValueError("The hydraulic residence time cannot be a negative number or 0")
        self._tau = tau
    
    @property
    def heat_consumption(self):
        if self._heat_consumption is None:
            print("The run method must be passed to get the heat consumption")
        return self._heat_consumption
    
    @property
    def cool_consumption(self):
        if self._cool_consumption is None:
            print("The run method must be passed to get the cool consumption")

    def _run(self):
        """
        
        This method runs the unit. The ShellHeatExchanger mass balance is simulated following the next equation:
        Output = Input
        

        """
        # Define the inlet streams
        Cold_Fluid = self.ins[0]

        # Define the outlet streams 
        Heated_Fluid = self.outs[0]

        # Perform the mass balance
        Heated_Fluid.copy_like(Cold_Fluid)  #This Stream object method is equivalent to out = in

        # Get the Cold_Fluid Cp. If BioSTEAM cannot calculate it, the Cp must be provided by the user.
        try:
            Fluid_Cp = Cold_Fluid.Cp
        
        except RuntimeError:
            if self.Cp is None:
                raise ValueError("Cp must be provided because BioSTEAM cannot calculated it.")
            if not isinstance(self.Cp, (int, float)):
                raise TypeError("Cp must be a numeric value")
            Fluid_Cp = self.Cp

        # Calculate the diference of temperature
        Dif_Temp = self.Tout - Cold_Fluid.T

        # Set Tout as the Temperature of the outlet stream
        Heated_Fluid.T = self.Tout

        # Energy Balance equations
        if self.energy_balance_type == 'kWh/kg':
            Heat_Consumption = Fluid_Cp * Dif_Temp / 3600
        elif self.energy_balance_type == 'kWh':
            Mass = Cold_Fluid.get_total_flow('kg/hr')
            Heat_Consumption = Fluid_Cp * Mass * Dif_Temp / 3600

        # Define the results of the energy balance depending on the temperature difference
        if Cold_Fluid.T < self.Tout:
            self._heat_consumption = Heat_Consumption
            self._cool_consumption = "This unit is heating the stream. The energy consumption is stored in heat_consumption"
        elif Cold_Fluid.T > self.Tout:
            self._heat_consumption = "This unit is cooling the stream. The energy consumption is stored in cool_consumption"
            self._cool_consumption = Heat_Consumption

    def _design(self):
        """
        """
        # Load the dictionary of results
        Design = self.design_results
        Ins1 = self.ins[0]
        Out1 = self.outs[0]
        
        # Check if the utilities have been initialized
        if not self.heat_utilities:
            self.heat_utilities = [bst.HeatUtility()]

        # Calculate if there is heating or cooling
        if isinstance(self.heat_consumption, (float, int)):
            Energy = self.heat_consumption
        elif isinstance(self.cool_consumption, (float, int)):
            Energy = self.cool_consumption
        else:
            raise ValueError("Heat utilities cannot be added because there is neither heating nor cooling")
        
        # Convert the energy to kJ/kg
        if self.energy_balance_type == 'kWh/kg':
            Energy_Flow = Energy * self.ins[0].get_total_flow('kg/hr') * 3600   # from kWh/kg to kJ/hr
        elif self.energy_balance_type == 'kWh':
            Energy_Flow = Energy * 3600                                         # from kWh to kJ/hr
        else:
            raise ValueError("Invalid energy balance type. Use 'kWh/kg or kWh")

        # Add the heat utility
        self.heat_utilities[0](Energy_Flow, self.ins[0].T, self.outs[0].T)
        
        # Heat utility Tin and Tout
        Hot_Fluid = self.heat_utilities[0].inlet_utility_stream
        T_Hot_Fluid_in = Hot_Fluid.T
        Flow = Hot_Fluid.get_total_flow('kg/hr')
        Cp = Hot_Fluid.Cp
        Hcond = Hot_Fluid.Hvap
        T_Hot_Fluid_out = (Energy_Flow - Hcond) / (Cp * Flow) + T_Hot_Fluid_in

        # Get the difference of temperature
        dTin = T_Hot_Fluid_out - Ins1.T
        dTout = T_Hot_Fluid_in - self.Tout
        
        # Calculate the exchange area
        Area = (Energy_Flow*1000/(3600))/(self.U*log_mean(dTin,dTout))
        
        # Add the Area to the results dictionary
        Design['Area'] = Area                                                      #TODO Create another heat exchanger for area < 20 m2 

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 70000     # USD
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_Cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            self._base_area = 100       # m2
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
            self._base_n_cost = 0.71
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
        """
        """
        # Load all the design parameters
        Area = self.design_results['Area']

        # Calculate the baseline purchase cost
        ## The base cost accounts for floating head, shell and bare tube
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Exchanger_Purchase_Cost = self.base_cost * (Area/self.base_area)**self.base_n_cost
        self.baseline_purchase_costs['Heat Exchanger'] = Exchanger_Purchase_Cost

        ## Material, pressure and temperature factors are assumed to be 1
        self.F_D['Heat Exchanger'] = self.F_M['Heat Exchanger'] = self.F_P['Heat Exchanger'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.60             # Heat Exchangers
        Instrumentation_Control = 0.50
        Piping = 0.68                   # Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Heat Exchanger'] = Bare_Module

        ## Scale the costs using the CEPCI
        CE_Base = self.CE_base
        self.baseline_purchase_costs['Heat Exchanger'] *= bst.CE/CE_Base