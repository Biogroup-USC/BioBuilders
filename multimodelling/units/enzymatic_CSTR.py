"""
"""
import biosteam as bst
import math

__all__ = ("BatchEnzymaticTreatment",)

class BatchEnzymaticTreatment(bst.Unit):
    """

    Create a Enzymatic CSTR inheriting from AbstractStirredTankReactor (BioSTEAM) which 
    represents an abstract CSTR modeled as a pressurised vessel. The input is set to 2, so
    the chemicals like water, NaOH or Enzyme have to be added using a second stream called 
    auxiliar stream.

    ARGUMENTS:                                                                                  #TODO document this better

    -   ID (str): This ID refers to the name of this unit.

    -   ins (list): List of input streams. In this case, there are 2 inputs. [Feed, Auxiliar]             

    -   outs(list): List of output streams. In this case, there is 1 possible outputs].

    -   time (float): Reaction time. Set to 5 h by default.

    -   loadCIPtime (float): Loading and CIP time. Set to 1 h by default.    

    -   reaction (dict or str): This argument is either a str or a ReactionSystem object
        from BioSTEAM. If the desired reaction is not in the pre-defined reactions, provide 
        it as {reactioname: Reaction object (BioSTEAM)}. When using the pre-defined ones, 
        provide one of the following list:

            >>> "Prot_Lib_TS_Viscozyme" 
            >>> Structural_Protein -> Protein; Yield = 0.712; 
            >>> basis = 'wt'

            >>> "Prot_Lib_TS_Trypsin"
            >>> Structural_Protein -> Peptides; Yield = 0.12;
            >>> basis = 'wt'

            >>> "Prot_Hydrolysis_Trypsin"
            >>> Protein -> Peptides; Yield = 1
            >>> basis = 'wt'

    -   operting_P (float): Pressure inside the reactor. Default to 101325 Pa.

    -   operating_T (float): Temperature inside the reactor. Default to 310.25 K.

    ATTRIBUTES:

    -   V_wf (float): Fraction of the reactor which corresponds to working volume. Default to 0.8.

    -   V_max (float): Maximum volume per reactor. Default to 200 m3.
    
    -   kW_per_m3 (float): Power consumption due to stirring. Default to 0.180 kW/m3.
    
    """
    _N_ins = 2
    _N_outs = 1
    _units = {
        'Power': 'kW/m3',
        'Reactor volume': 'm3',
        'Batch time': 'h',
        'Loading and cleaning time': 'h',
    }
    

    Predefined_Reactions = {        # Reaction stoichiometry                                    # Yield-based Reactant              # Yield     # Weight or Mol
        "Prot_Lib_TS_Viscozyme" :   {"reaction":{'Structural_Protein' : -1,'Protein': 1},       "reactant": 'Structural_Protein',   "X": 0.712, "basis" : 'wt'},
        "Prot_Lib_TS_Trypsin" :     {"reaction":{'Structural_Protein' : -1, 'Peptides': 1},     "reactant": 'Structural_Protein',   "X": 0.12,  "basis": 'wt'},
        "Prot_hydrolysis_Trypsin":  {"reaction": {'Protein': -1, 'Peptides': 1},                "reactant": 'Protein',              "X": 1.0,   "basis": 'wt'},
    }

    def _init(self, 
              reaction: dict | str = None, 
              time: float = None, 
              loadCIPtime: float = None,
              operating_T: float = None,
              operating_P: float = None
              ):
        """

        This method initialises the BatchEnzymaticTreatment object allowing to select
        a predefined reaction if reaction = str or a reaction system providing a BioSTEAM
        ReactionSystem object. Note that a Reaction object could be provided.

        """
        # The reaction attribute could be a new reaction provided by the user or 
        # a pre-defined reaction 
        if isinstance(reaction, str):
            if reaction in self.Predefined_Reactions:
                self.reaction = bst.Reaction(
                    reaction = self.Predefined_Reactions[reaction]["reaction"],
                    reactant = self.Predefined_Reactions[reaction]["reactant"],
                    X = self.Predefined_Reactions[reaction]["X"],
                    basis = self.Predefined_Reactions[reaction]["basis"]
                )
            else:
                raise ValueError("Reaction {} is not defined. Use a predefined or provide a dictionary".format(reaction))
        elif isinstance(reaction, object):
            self.reaction = reaction
        else:
            raise ValueError("A reaction must be provided")

        # The other parameters
        self.time = time
        self.loadCIPtime = loadCIPtime
        self._operating_T = operating_T
        self._operating_P = operating_P
        self._kW_per_m3 = None
        self._V_wf = None
        self._V_max = None

    def _run(self):
        """

        The mass balance is simulated as Out = In + Generation. The generation term
        corresponds to the enzymatic reaction.
        
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
    def kW_per_m3(self):
        """
        """
        if self._kW_per_m3 is None:
            self._kW_per_m3 = (0.79*1000*(1.417**3)*(0.373**5))/90    #kW/m3       using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kW_per_m3
    
    @kW_per_m3.setter
    def kW_per_m3(self, value):
        """
        """
        self._kW_per_m3 = value

    @property
    def operating_T(self):
        """
        """
        if self._operating_T is None:
            self._operating_T = 273.15 + 37.0
            print("")
            print("The temperature is {} K by default".format(self._operating_T))
            print("")
        return self._operating_T
    
    @property
    def operating_P(self):
        """
        """
        if self._operating_P is None:
            self._operating_P = 101325
            print("")    
            print("The Pressure is {} bar by default".format(self._operating_P))
            print("")
        return self._operating_P
    
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
        Design = self.design_results
        Ins1, Ins2 = self.ins
        Out = self.outs
        Load = bst.Stream(units = 'kg/hr')
        Load.copy_like(Ins1)
        Load.mix_from([Ins1, Ins2], energy_balance = True)

        # Calculate the reactor volume
        Inputs_F_Vol = (Ins1.F_vol + Ins2.F_vol)
        V_0 = Inputs_F_Vol
        
        # Calculate the number of batches needed to operate in semi-continuous
        tau = self.time             # h
        tau_0 = self.loadCIPtime    # h
        V_wf = self.V_wf            
        V_max = self.V_max          # m3
        N = (V_0 * (tau+tau_0))/ (V_max*V_wf) + 1 # One more reactor is always needed to ensure semicontinuos  
        
        # Minimum 2 reactor: There must be at least 2 reactor to operate in semicontinuous
        if N < 2:
            N = 2
        elif N >= 2 and not isinstance(N, int):
            
            # Recalculate the volume of each reactor to obtain an exact number
            N0 = math.trunc(N) + 1
            N = N0
        
        # Add the reactor volume, the number of reactors, batch time and loading+cleaning time
        Design['Reactor volume'] = (V_0/V_wf)/N     # m3
        Design['Batch time'] = tau                  # h
        Design['Loading and cleaning time'] = tau_0 # h
        self.parallel['Reactor'] = N
        print(Design['Reactor volume'])
        # Add the power utility
        Power_Stirring = self.kW_per_m3 * Design["Reactor volume"]
        self.add_power_utility(Power_Stirring)

        # Add the heat utility assuming that the process is adiabatic
        Tf = self.operating_T                   # K
        Ti = Load.T                             # K
        Duty = Load.Cp * (Tf-Ti) * Load.F_mass  # kJ/h
        self.add_heat_utility(Duty, T_in = Ti, T_out = Tf)
    
    def _cost(self):
        """
        """
        # Load all the design parameters
        V_reactor = self.design_results['Reactor volume']
        
        # Calculate the baseline purchase cost for each reactor
        ## The base cost accounts for jacketed agitated vessel. 
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Reactor_Purchase_Cost = 75000 * (V_reactor/3)**0.53        
        self.baseline_purchase_costs['Reactor'] = Reactor_Purchase_Cost
        
        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D['Reactor'] = self.F_M['Reactor'] = self.F_P['Reactor'] = 1

        ## The installation costs are assumed to be 0, so the bare module factor = 1
        self.F_BM['Reactor'] = 1

        ## Scale the costs using CEPCI
        CE_base = 100
        self.baseline_purchase_costs['Reactor'] *= bst.CE/CE_base