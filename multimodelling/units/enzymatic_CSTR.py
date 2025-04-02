"""
"""
import biosteam as bst

__all__ = ["BatchEnzymaticTreatment"]

class BatchEnzymaticTreatment(bst.AbstractStirredTankReactor):
    """

    Create a Enzymatic CSTR inheriting from AbstractStirredTankReactor (BioSTEAM) which 
    represents an abstract CSTR modeled as a pressurised vessel. The input is set to 2, so
    the chemicals like water, NaOH or Enzyme have to be added using a second stream called 
    auxiliar stream.

    ARGUMENTS:

    -   ID (str): This ID refers to the name of this unit.

    -   ins (list): List of input streams. In this case, there are 2 inputs. [Feed, Auxiliar]             

    -   outs(list): List of output streams. In this case, there is 1 possible outputs].

    -   time (float): Reaction time. set to 5 h by default.

    -   loadingtime (float): Loading time. set to 15 min by default.    

    -   reaction (dict or str): This argument is either a dict or a str. If the 
        desired reaction is not in the pre-defined reactions, provide it as 
        {reactioname: Reaction object (BioSTEAM)}. When using the pre-defined ones, 
        provide one of the following list:

            "Prot_Lib_TS_Viscozyme" 
            Structural_Protein -> Protein; Yield = 0.712; 
            basis = 'wt'

            "Prot_Lib_TS_Trypsin"
            Structural_Protein -> Peptides; Yield = 0.12;
            basis = 'wt'
        
    Notes: 
    Only 1 reaction is supported at this moment. Implementing more than one 
    in the same CSTR will be further added.

    """
    _N_ins = 2
    _N_outs = 1
    kW_per_m3_default = (0.79*1000*(1.417**3)*(0.373**5))/90    #kW/m3       using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164
    V_wf_default = 0.8      
    tau_default = 5         #h
    tau_0_default = 15/60   #h
    batch_default = True
    _units = 'kg/hr'
    
    Pre_Defined_Reactions = {       # Reaction stoichiometry                                    # Yield-based Reactant              # Yield     # Weight or Mol
        "Prot_Lib_TS_Viscozyme" :   {"reaction":{'Structural_Protein' : -1,'Protein': 1},       "reactant": 'Structural_Protein',   "X": 0.712, "basis" : 'wt'},
        "Prot_Lib_TS_Trypsin" :     {"reaction":{'Structural_Protein' : -1, 'Peptides': 1},     "reactant": 'Structural_Protein',   "X": 0.12,  "basis": 'wt'},
        "Prot_hydrolysis_Trypsin":  {"reaction": {'Protein': -1, 'Peptides': 1},                "reactant": 'Protein',              "X": 1.0,   "basis": 'wt'},
    }

    def _init(self, reaction: dict | str = None, time: float = None, loadingtime: float = None):
        """

        This method initializes the unit chosing the reaction from the pre-defined
        reactions dictionary if reaction = str or creating a new reaction attribute
        if reaction = dict. The dictionary must have the following structure: 
        {"reaction name" : Reaction object (BioSTEAM)} 

        Notes: 
        Only 1 reaction is supported at this moment. Implementing more than one                 
        in the same CSTR will be further added.

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
        elif isinstance(reaction, dict):
            if reaction.values() > 1:
                raise ValueError("More than 1 reaction is not yet supported")
            else:
                self.reaction = reaction.values()   #TODO: add parallel reactions and series reaction. For now, only one works
        else:
            raise ValueError("A reaction must be provided")
        
        # If not time provided, default to 5 h
        self.tau_default = time if time is not None else self.tau_default

        # If not loading_time provided, default to 15 min
        self.tau_0_default = loadingtime if loadingtime is not None else self.tau_0_default
                
    def _run(self):
        """
        
                                                #TODO Document the run function explaining how the mass balance is simulated

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
        Product.copy_flow(Load)
        self.reaction(Product) 

    def _design(self):
        #self.heat_utilities[0]()                                #TODO Use this method to add the heat utility
        pass

    def _cost(self):
        pass