"""
"""
import biosteam as bst

class ContinuousStirredTankReactor(bst.Unit):
    """

    Create a CSTR.

    Parameters
    ----------
    ID : str 
        This ID refers to the name of this unit.

    ins : list
        List of input streams. In this case, there are 2 inputs. [Feed, Auxiliar]             

    outs : list
        List of output streams. In this case, there is 1 possible outputs].

    time : float
        Reaction time. Set to 5 h by default.

    time_loading : float
        Loading time. Set to 0.5 h by default.    

    time_CIP : float
        Clean-in-place time. Set to 1 h by default.

    reaction : bst.Reaction | bst.ReactionSystem
        Reaction taking place inside the CSTR.     
    
    operting_P : float 
        Pressure inside the reactor. Default to 101325 Pa.

    operating_T : float 
        Temperature inside the reactor. Default to 298.15 K.
    
    Attributes
    ----------
    V_wf : float
        Fraction of the reactor which corresponds to working volume. Default to 0.8.

    V_max : float
        Maximum volume per reactor. Default to 200 m3.
    
    kW_per_m3 : float
        Power consumption due to stirring. Default to 0.180 kW/m3.
    
    Base_Cost : float
        The cost (USD) of a reactor which volume corresponds to the base volume.

    Base_n_Cost : float
        The parameter n in the expression: Base_Cost * (Volume/Base_Volume)**n.

    Base_Volume : float
        The volume (m3) of a BSTR whose cost is the Base_Cost.

    CE_Base : float
        The CEPCI which corresponds with the Base_Cost
    
    """
    _N_ins = 2
    _N_outs = 1
    _units = {
        'Power': 'kW/m3',
        'Reactor volume (total)': 'm3',
        'Reactor volume (single)': 'm3',
        'Residence time': 'h',
    }

    def _init(self, 
              reaction: bst.Reaction | bst.ReactionSystem = None,
              tau: float = None,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              kW_per_m3: float = None,
              ):
        """
        """
        self.reaction = reaction
        self.tau = tau
        self.operating_T = operating_T
        self.operating_P = operating_P
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
        # Define the input streams
        Feed = self.ins[0]
        Aux = self.ins[1]
       
        # Define output streams
        Product = self.outs[0]

        # Mix both streams
        Load = bst.Stream(units = 'kg/hr')
        Load.mix_from([Feed, Aux], energy_balance = True)
       
        # Perform the reaction
        Product.T = self.operating_T
        Product.copy_flow(Load)
        self.reaction(Product)
    
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
        ins1, ins2 = self.ins
        load = bst.Stream(units = 'kg/hr')
        load.mix_from([ins1, ins2], energy_balance = True)

        # Calculate the reactor volume
        Input_Flow = load.F_vol
        tau = self.tau                      # h
        V_wf = self.V_wf            
        V_max = self.V_max                  # m3
        V_0 = Input_Flow * tau              # Working volume of the reactor
        if V_0 > V_max:
            unit = self.ID
            Warning('The cost correlation parameters for tank volume have a maximum volume of {} m3. The current volume of {} is {} m3'.format(V_max, unit, V_0))

        # Add the reactor volume, the number of reactors, batch time and loading+cleaning time
        Design['Reactor volume (total)'] = (V_0/V_wf)       # m3
        Design['Residence time'] = tau                      # h
        
        # Add the power utility
        if self.kW_per_m3 is not None:
            volumetric_power = self.kW_per_m3
            power = volumetric_power * V_0
        else:
            raise ValueError("kW_per_m3 must be provided to calculate power requirements."
                             "In case you have no data, use `agitator_volumetric_power_determination`"
                             "to stimate the volumetric power.")
        
        self.add_power_utility(power)

        # Add the heat utility assuming that the process is adiabatic
        Tf = self.operating_T                   # K
        Ti = load.T                             # K
        if load.F_mass > 0 and load.MW > 0:
            Cp = load.Cp
            duty = Cp * (Tf-Ti) * load.F_mass  # kJ/h
            self.add_heat_utility(duty, T_in = Ti, T_out = Tf)
        else:
            Warning("[{}] Empty or undefined stream: skipping heat duty".format(self.ID))
            self.add_heat_utility(0.0, Ti, Tf)

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 75000.0   # USD
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self,value):
        """
        """
        self._base_cost = value
    
    @property
    def base_volume(self):
        """
        """
        if self._base_volume is None:
            self._base_volume = 3.0     # m3
        return self._base_volume

    @base_volume.setter
    def base_volume(self,value):
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
        # Load all the design parameters
        V_reactor = self.design_results['Reactor volume (total)']
        
        # Calculate the baseline purchase cost for each reactor
        ## The base cost accounts for jacketed agitated vessel. 
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Reactor_Purchase_Cost = self.base_cost * (V_reactor/self.base_volume)**self.base_n_cost        
        self.baseline_purchase_costs['Reactor'] = Reactor_Purchase_Cost
        
        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D['Reactor'] = self.F_M['Reactor'] = self.F_P['Reactor'] = 1

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
        self.F_BM['Reactor'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_base = self.CE_base
        self.baseline_purchase_costs['Reactor'] *= bst.CE/CE_base

class BatchAgitatedReactor(bst.Unit):
    """
    """