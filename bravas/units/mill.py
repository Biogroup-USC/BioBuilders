"""
"""
import biosteam as bst

__all__ = (
    "BallMill", "AttritionMill"
    )

class BallMill(bst.Unit):
    """
    Create a ball mill for size reduction.

    This class simulates a mill, accounting for its energy consumption, design and cost.
    The mass balance assumes that the output is equal to the input.

    Parameters
    ----------
    ID: str
        Name of the unit operation.
    
    ins: tuple
        List of input streams:
        * [0] solid
    
    outs: tuple
        List of output streams.
        * [0] ground solid
    
    Attributes
    ----------
    power_consumption: float
        Specific power consumption of the mill [kWh/kg].
    """

    _N_ins = 1
    _N_outs = 1
    _units = {
        'Power': 'kW',
        'Specific Power': 'kWh/kg'
    }

    def _init(self):
        """
        Initialize the properties.
        """
        self._power_consumption = None
        self._base_cost = None
        self._base_power = None
        self._base_n_cost = None
        self._CE_base = None
    
    def _run(self):
        """
        This method runs the unit. 
        The mill mass balance is simulated with inflow equal to outflow.
        """

        # Defining the inlet
        Feed = self.ins[0]
        Feed.phase = 's'

        # Defining the oulet
        Out = self.outs[0]
        Out.phase = 's'

        # Running the unit
        Out.copy_like(Feed)
        Out.F_mass = Feed.F_mass  
    
    @property
    def power_consumption(self):
        """
        This property refers to the power consumption as kWh/kg.
        """
        if self._power_consumption is None:
            self._power_consumption = 0.016 # kWh upper value for grinding from: http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._power_consumption
    
    def _design(self):
        """
        """
        Feed, = self.ins

        # Power
        Power = self.power_consumption * Feed.F_mass
        self.design_results['Specific Power'] = self.power_consumption
        self.design_results['Power'] = Power

        # Add the power utility
        self.add_power_utility(Power)

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 285000 # USD from: Rules of Thumb
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value
    
    @property
    def base_power(self):
        """
        """
        if self._base_power is None:
            self._base_power = 75 # kW from: Rules of Thumb
        return self._base_power
    
    @base_power.setter
    def base_power(self, value):
        """
        """
        self._base_power = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.70 # From: Rules of Thumb
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
        # Load all the design parameters needed
        Power = self.design_results['Power']

        # Calculate the baseline purchase cost for the ball mill: Excluding liner, drive, motor, guard and ball load
        Mill_Baseline_Cost = self.base_cost * (Power/self.base_power) ** self.base_n_cost
        self.baseline_purchase_costs['Mill equipment'] = Mill_Baseline_Cost
        
        # The material, pressure and temperature factor are assumed to be 1
        self.F_D['Mill equipment'] = self.F_M['Mill equipment'] = self.F_P['Mill equipment'] = 1

        # The bare module factor which account for installation cost is calculated as the sum of delivery, installation, piping, instrumentation and controls
        Delivery = 0.10
        Installation = 0.50 # Assumed
        Instrumentation_Control = 0.50 
        Piping = 0.16 # Solid

        # Calculate the bare module with percentages from Peters: Plant Design and Economics for Chemical Engineers
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Mill equipment'] = Bare_Module

        # Scale the costs using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Mill equipment'] *= bst.CE/CE_base


class AttritionMill(bst.Unit):
    """

    Create a mill for size-reduction.

    This class simulates a mill, accounting for its energy consumption,
    design and cost. The mass balance assumes that the output is equal
    to the input.

    Parameters
    ----------
    ID : str
        Name of the unit operation.

    ins : tuple
        List of input streams:
        * [0] solid

    - outs : tuple
        List of output streams. 
        * [0] ground solid

    Attributes
    ----------
    power_consumption : float
        Specific power consumption of the mill [kWh/kg]

    """

    _N_ins = 1
    _N_outs = 1
    _units = {
        'Power': 'kW',
        'Specific Power': 'kWh/kg'
    }
    
    def _init(self):
        """
        """
        # Initialize the properties
        self._power_consumption = None
        self._base_cost = None
        self._base_power = None
        self._base_n_cost = None
        self._CE_base = None

    def _run(self):
        """
        
        This method runs the unit. The milla mass balance is simulated following the next equation:
        Output = sfi * Input {sfi = losses for Losses stream and sfi = (1-losses) for Out stream} 
        

        """
        # Defining the inlet
        feed = self.ins[0]

        #Defining the Outlet
        Out = self.outs[0]

        # Running the Unit
        ## This Unit is simulated basically as OUT = sfi * IN where the sfi represents the losses
        Out.copy_like(feed)
        Out.F_mass = feed.F_mass

    @property
    def power_consumption(self):
        """

        This property refers to the power consumption as kWh/kg

        """
        if self._power_consumption is None:
            self._power_consumption = 0.016     # kWh/kg from http://dx.doi.org/10.1016/j.jclepro.2016.06.164 / 16 kWh/ton is the upper value for grinding
        return self._power_consumption

    def _design(self):
        """
        """
        Design = self.design_results
        Ins1, = self.ins

        # Power
        Power = self.power_consumption * Ins1.F_mass
        Design['Specific Power'] = self.power_consumption
        Design['Power'] = Power

        # Add the power utility
        self.add_power_utility(Power)

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 30000.0   # USD
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self,value):
        """
        """
        self._base_cost = value
    
    @property
    def base_power(self):
        """
        """
        if self._base_power is None:
            self._base_power = 23.0    # Power
        return self._base_power

    @base_power.setter
    def base_power(self,value):
        """
        """
        self._base_power = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.63
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
        # Load all the design parameters needed
        Power = self.design_results['Power']

        # Calculate the baseline purchase cost for the attrition mill
        ## The base cost accounts for the attrition mill. Rule of the Thumb: DOI: 10.1002/9783527611119. Appendix D
        Mill_baseline_Cost = self.base_cost * (Power/self.base_power)**self.base_n_cost # Mill costs includes auxiliar equipment and drive but motor
        self.baseline_purchase_costs['Mill equipment'] = Mill_baseline_Cost
        Motor_baseline_Cost = 0

        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D['Mill equipment'] = self.F_M['Mill equipment'] = self.F_P['Mill equipment'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.50             # Assumed
        Instrumentation_Control = 0.50
        Piping = 0.16                   # Solid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Mill equipment'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Mill equipment'] *= bst.CE/CE_base