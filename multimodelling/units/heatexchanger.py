"""
"""
import biosteam as bst

__all__ = ["ShellHeatExchanger"]

class ShellHeatExchanger(bst.Unit):
    """
    
    Create a Shell heat exchanger object which is modeled as a vessel. This unit increments the         #TODO redefine the model when the design is completed 
    temperature of the inlet stream. The energy consumed to cool down the stream or to heat it up 
    is calculated as kWh or kWh/kg using the hydraulic residence time which is 10 min by default.

    ARGUMENTS:

    - ID (str): This refers to the name of the unit.

    - ins (list): List of input streams. In this case, there is only 1 input.

    - outs (list): List of output streams. In this case, there is 1 output.
    
    - Tout (float): This parameter is the temperature of the cold fluid in the output of the heat exchanger.
    Thet temperature must be K.
    
    - Cp (float): The Calorific Power is used when BioSTEAM cannot get the Cp from the Chemicals of each stream.
    This is important because sometimes, there is no data for certain compounds. The units must be
    kJ/(kg*K).

    """                            
    _N_ins = 1
    _N_outs = 1

    def _init(self, Tout: float = None, Cp: float = None):      
        if Tout is None:
            raise ValueError("A Tout must be provided")        
        self.Cp = Cp
        self.Tout = Tout            
        self._energy_balance_type = None
        self._tau = None
        self._heat_consumption = None
        self._cool_consumption = None
                                           
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
            self._tau = 10/60   # h --> 2 times the time defined by UNIBO data
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
            Mass = self.tau * Cold_Fluid.get_total_flow('kg/hr')
            Heat_Consumption = Fluid_Cp * Mass * Dif_Temp / 3600

        # Define the results of the energy balance depending on the temperature difference
        if Cold_Fluid.T < self.Tout:
            self._heat_consumption = Heat_Consumption
            self._cool_consumption = "This unit is heating the stream. The energy consumption is stored in heat_consumption"
        elif Cold_Fluid.T > self.Tout:
            self._heat_consumption = "This unit is cooling the stream. The energy consumption is stored in cool_consumption"
            self._cool_consumption = Heat_Consumption

    def _design(self):
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
            Energy_Flow = Energy/self.tau * 3600                                # from kWh to kJ/hr
        else:
            raise ValueError("Invalid energy balance type. Use 'kWh/kg or kWh")
        
        # Add the heat utility
        self.heat_utilities[0](Energy_Flow, self.ins[0].T, self.outs[0].T)

    def _cost(self):                # El consumo en kWh encaja en costes operativos. El balance de energía lo puedo resolver en run
        pass