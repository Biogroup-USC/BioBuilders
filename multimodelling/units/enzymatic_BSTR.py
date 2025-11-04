"""
"""
import biosteam as bst
import math

__all__ = ("BatchEnzymaticTreatment",)

class BatchEnzymaticTreatment(bst.Unit):
    """

    Create a BSTR to perform an enzymatic treatment.

    Create a Enzymatic BSTR which is modelled as a non-pressurize jacketed agitated 
    vessel. This class includes default reactions based on experimental data, but it
    also supports new reactions defined as bst.Reaction objects. The BSTR has 2 inputs
    streams which represent the substrate and the auxiliars like water, enzymes or buffers.

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

    reaction : dict | str
        Reaction performed in this reactor. There are 2 option: select one of the 
        reaction provided above by giving a string or create a new reaction using 
        the bst.Reaction object. 

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
    
    base_cost : float
        The cost (USD) of a reactor which volume corresponds to the base volume.

    base_n_cost : float
        The parameter n in the expression: base_cost * (Volume/Base_Volume)**n.

    base_volume : float
        The volume (m3) of a BSTR whose cost is the base_cost.

    CE_base : float
        The CEPCI which corresponds with the base_cost
    
    Default Reactions
    -----------------

            >>> "Prot_Lib_TS_Viscozyme" 
            >>> Structural_Protein -> Protein; Yield = 0.712; 
            >>> basis = 'wt'

            >>> "Prot_Lib_TS_Trypsin"
            >>> Structural_Protein -> Peptides; Yield = 0.12;
            >>> basis = 'wt'

            >>> "Prot_Hydrolysis_Trypsin"
            >>> Protein -> Peptides; Yield = 1;
            >>> basis = 'wt'


    """
    _N_ins = 2
    _N_outs = 1
    _units = {
        'Power': 'kW/m3',
        'Reactor volume (total)': 'm3',
        'Reactor volume (single)': 'm3',
        'Batch time': 'h',
        'Loading time': 'h',
        'CIP time': 'h'
    }
    

    Default_Reactions = {           # Reaction stoichiometry                                    # Yield-based Reactant              # Yield     # Weight or Mol
        "Prot_Lib_TS_Viscozyme" :   {"reaction":{'Structural_Protein' : -1,'Protein': 1},       "reactant": 'Structural_Protein',   "X": 0.712, "basis" : 'wt'},
        "Prot_Lib_TS_Trypsin" :     {"reaction":{'Structural_Protein' : -1, 'Peptides': 1},     "reactant": 'Structural_Protein',   "X": 0.38,  "basis": 'wt'},
        "Prot_Hydrolysis_Trypsin":  {"reaction": {'Protein': -1, 'Peptides': 1},                "reactant": 'Protein',              "X": 1.0,   "basis": 'wt'},
    }

    def _init(self, 
              reaction: dict | str = None, 
              time: float = None, 
              time_loading: float = None,
              time_CIP: float = None,
              operating_T: float = 298.15,
              operating_P: float = 101325
              ):
        """

        This method initialises the BatchEnzymaticTreatment object allowing to select
        a default reaction if reaction = str or a reaction system providing a BioSTEAM
        ReactionSystem object.

        """
        # The reaction parameter could be a new reaction provided by the user or 
        # a default reaction
        if reaction in self.Default_Reactions and isinstance(reaction, str): 
            self.reaction = bst.Reaction(
                reaction = self.Default_Reactions[reaction]["reaction"],
                reactant = self.Default_Reactions[reaction]["reactant"],
                X = self.Default_Reactions[reaction]["X"],
                basis = self.Default_Reactions[reaction]["basis"]
            )
        elif reaction not in self.Default_Reactions and isinstance(reaction, str):
            raise ValueError("Reaction {} is not defined. Use a predefined or provide a dictionary".format(reaction))
        elif isinstance(reaction, object):
            self.reaction = reaction
        else:
            raise ValueError("The reaction parameter must be provided as a bst.Reaction object or a string.")

        # The other parameters
        self.time = time
        self.time_loading = time_loading
        self.time_CIP = time_CIP
        self.operating_T = operating_T
        self.operating_P = operating_P
        self._kW_per_m3 = None
        self._V_wf = None
        self._V_max = None
        self._base_cost = None
        self._base_volume = None
        self._base_n_cost = None
        self._CE_base = None

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
            self._kW_per_m3 = ((0.79*1000*(1.417**3)*(0.373**5))/90)/1    #kW/m3       using 1 m3 data --> http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kW_per_m3
    
    @kW_per_m3.setter
    def kW_per_m3(self, value):
        """
        """
        self._kW_per_m3 = value

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
        Ins1, Ins2 = self.ins
        Out = self.outs
        Load = bst.Stream(units = 'kg/hr')
        Load.copy_like(Ins1)
        Load.mix_from([Ins1, Ins2], energy_balance = True)

        # Calculate the reactor volume
        Inputs_F_Vol = (Ins1.F_vol + Ins2.F_vol)
        Input_Flow = Inputs_F_Vol
        
        # Calculate the number of batches needed to operate in semi-continuous
        time = self.time                    # h
        time_loading = self.time_loading    # h
        time_CIP = self.time_CIP            # h
        V_wf = self.V_wf            
        V_max = self.V_max                  # m3
        V_0 = Input_Flow * (time + time_loading + time_CIP) # Volume needed for semicontinuous
        N = ((V_0)/(V_max * V_wf) + 1)      # One more reactor is always needed to ensure semicontinuos  

        # Minimum 2 reactor: There must be at least 2 reactor to operate in semicontinuous
        if N < 2:
            N = 2
        elif N >= 2 and not isinstance(N, int):
            
            # Recalculate the volume of each reactor to obtain an exact number
            N0 = math.trunc(N) + 1
            N = N0
        
        # Add the reactor volume, the number of reactors, batch time and loading+cleaning time
        Design['Reactor volume (total)'] = (V_0/V_wf)       # m3
        Design['Reactor volume (single)'] = (V_0/V_wf)/N    # m3
        Design['Batch time'] = time                         # h
        Design['Loading time'] = time_loading               # h
        Design['CIP time'] = time_CIP                       # h 
        self.parallel['Reactor'] = N
        
        # Add the power utility
        Power_Stirring = self.kW_per_m3 * Design["Reactor volume (total)"]
        self.add_power_utility(Power_Stirring)

        # Add the heat utility assuming that the process is adiabatic
        Tf = self.operating_T                   # K
        Ti = Load.T                             # K
        Duty = Load.Cp * (Tf-Ti) * Load.F_mass  # kJ/h
        self.add_heat_utility(Duty, T_in = Ti, T_out = Tf)
    
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
        CE_Base = self.CE_base
        self.baseline_purchase_costs['Reactor'] *= bst.CE/CE_Base