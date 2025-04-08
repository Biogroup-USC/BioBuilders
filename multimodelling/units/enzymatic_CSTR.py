"""
"""
import biosteam as bst

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
    
    -   V_wf (float): Fraction of the reactor which corresponds to working volume. Default to 0.8.

    -   V_max (float): Maximum volume per reactor. Default to 200 m3.
    
    -   kW_per_m3 (float): Power consumption due to stirring. Default to 0.180 kW/m3.

    -   opertaing_P (float): Pressure inside the reactor. Default to 101325 Pa.

    -   length_to_diameter (float): length-diameter ratio of the reactor for design purpouses.
        default to 2.
    
    """
    _N_ins = 2
    _N_outs = 1
    _units = {
        'Power': 'kW/m3',
    }

    Pre_Defined_Reactions = {       # Reaction stoichiometry                                    # Yield-based Reactant              # Yield     # Weight or Mol
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
        a predifined reaction if reaction = str or a reaction system providing a BioSTEAM
        ReactionSystem object. Note that a Reaction object could be provided.

        """
        # The reaction attribute could be a new reaction provided by the user or 
        # a pre-defined reaction 
        if isinstance(reaction, str):
            if reaction in self.Pre_Defined_Reactions:
                self.reaction = bst.Reaction(
                    reaction = self.Pre_Defined_Reactions[reaction]["reaction"],
                    reactant = self.Pre_Defined_Reactions[reaction]["reactant"],
                    X = self.Pre_Defined_Reactions[reaction]["X"],
                    basis = self.Pre_Defined_Reactions[reaction]["basis"]
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
        Load = bst.Stream('Ghost', units = 'kg/hr')
        Load.mix_from([Feed, Aux], energy_balance = False)
       
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
    
    @property
    def operating_T(self):
        """
        """
        if self._operating_T is None:
            self._operating_T = 273.15 + 37.0
            raise Warning("The temperature is {} K by default".format(self._operating_T))
        return self._operating_T
    
    @property
    def operating_P(self):
        """
        """
        if self._operating_P is None:
            self._operating_P = 101325
            raise Warning("The Pressure is {} bar by default".format(self._operating_P))
        return self._operating_P
    
    @property
    def V_wf(self):
        """
        """
        if self._V_wf is None:
            self._V_wf = 0.80
        return self._V_wf
    
    @property
    def V_max(self):
        """
        """
        if self._V_max is None:
            self._V_max = 200   #m3
        return self._V_max

    def _desing(self):
        """
        """
        Design = self.design_results
        Ins1, Ins2 = self.ins
        Out = self.outs

        # Calculate the reactor volume
        Inputs_F_Vol = (Ins1.F_vol + Ins2.F_vol)
        V_0 = Inputs_F_Vol

        # Calculate the number of batches needed to operate in semi-continuous
        tau = self.time
        tau_0 = self.loadCIPtime
        V_wf = self.V_wf
        V_max = self.V_max
        N = V_0 / (V_max*V_wf) * (tau+tau_0) + 1
        
        # Minimum 2 reactor
        if N < 2:
            N = 2
        
        # Design tools from BioSTEAM to get the batch size
        Design.update(bst.design_tools.size_batch(V_0,tau,tau_0,N,V_wf))
        print(Design)
        V_reactor = Design['Reactor volume']