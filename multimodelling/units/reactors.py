"""
"""
import biosteam as bst
from thermosteam import Reaction, SeriesReaction, ParallelReaction, ReactionSystem
from warnings import warn
from ..tools import sort_streams_by_phases

class ContinuousStirredTankReactor(bst.Unit):
    """

    Continuous stirred tank reactor (CSTR) with agitation power and heating/cooling duty.

    This unit mixes all inlet streams, applies a user-defined reaction model and reports
    reactor sizing and utilities for operation at a specified temperature. Reactor volume
    is estimated using the volumetric flow rate of solid and liquid streams and hydraulic 
    retention time. Gas-phase stream are not included in volume nor duty determination. 
    Agitation power is scaled using the volumetric power.

    Parameters
    ----------
    ID : str 
        This ID refers to the name of this unit.

    ins : tuple
        Inlet streams. At least a minimun of 2 streams must be provided.
        Typical convention:
        - ins[0] substrate
        - ins[1] reactives
        - ins[2] air or gas stream (optional)
        - ...

    outs : tuple
        Outlet streams.
        - outs[0] effluent
        - outs[1] vent-out (only when `vent_out=True`)
    
    tau : float
        Hydraulic retention time [h] used for reactor sizing.
    
    reaction : bst.Reaction | bst.ReactionSystem
        Reaction(s) taking place inside the CSTR.
    
    operting_P : float 
        Pressure inside the reactor [Pa]. Default to 101325 Pa.
    
    operating_T : float 
        Temperature inside the reactor [K]. Default to 298.15 K.
    
    kW_per_m3 : float
        Volumetric power used to scale-up electricity consumption [kW/m^3].
    
    vent_out : bool
        True when air/gas is being supplied. Default to False.
        
    Attributes
    ----------
    reactor_load : bst.Stream
        Mixture of input streams used for reactor sizing (typically solids and liquids
        excluding gas when `vent_out=True`).
    
    V_wf : float
        Fraction of the reactor which corresponds to working volume. Default to 0.8.
    
    V_max : float
        Maximum volume per reactor. Default to 200 m3.
    
    base_cost : float
        The cost (USD) of a reactor which volume corresponds to base_volume.
    
    base_n_cost : float
        The parameter n in the expression: base_cost * (Volume/Base_Volume)**n.
    
    base_volume : float
        The volume (m3) of a BSTR whose cost is the base_cost.
    
    CE_base : float
        The CEPCI which corresponds with the base_cost.
    
    Notes
    -----
        - Reactor sizing is based on liquid and solid phases only. Gas-phase streams are
        excluded from volume and duty calculations.

        - When `vent_out=True`, gas-phase material is separated into vent stream, while
        liquid and solids leave as effluent.
    
    """
    _N_ins = 2
    _ins_size_is_fixed = False
    _N_outs = 2
    _outs_size_is_fixed = False
    _units = {
        'Power': 'kW/m3',
        'Reactor volume (total)': 'm3',
        'Reactor volume (single)': 'm3',
        'Hydraulic retention time': 'h',
    }

    def _init(self, 
              reaction: bst.Reaction | bst.ReactionSystem = None,
              tau: float = None,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              kW_per_m3: float = None,
              vent_out: bool = False,
              ):
        """
        """
        # Parameters
        self.reaction = reaction
        self.tau = tau
        self.operating_T = operating_T
        self.operating_P = operating_P
        self.kW_per_m3 = kW_per_m3
        self.vent_out = vent_out
        
        # Properties
        self._reactor_load = None
        self._V_wf = None
        self._V_max = None
        self._base_cost = None
        self._base_volume = None
        self._base_n_cost = None
        self._CE_base = None

    @property
    def reactor_load(self):
        """
        """
        return self._reactor_load
    
    @reactor_load.setter
    def reactor_load(self,value):
        """
        """
        self._reactor_load = value

    def _run(self):
        """
        """
        # Define the input streams
        ins = list(self.ins)
        self.reactor_load = feed = bst.Stream()

        if self.vent_out:
            # Get solid and liquid streams
            liquid_solid_ins = sort_streams_by_phases(ins,('l','s'))
            feed.mix_from(liquid_solid_ins)

            # Get gas stream(s)
            gases = sort_streams_by_phases(ins,('g',))

            # Create a MultiStream
            all_inputs = gases + [feed]

            mixture = bst.Stream()
            mixture.phases = 'gl'
            mixture.mix_from(all_inputs)

            # React
            mixture.T = self.operating_T
            mixture.P = self.operating_P
            self.reaction(mixture)

            # Separate by phases
            effluent, vent = self.outs
            bst.separations.phase_split(mixture,(vent, effluent))
        else:
            # Mix all input streams
            feed.mix_from(ins)

            # React
            effluent = self.outs[0]
            effluent.copy_like(feed)
            effluent.T = self.operating_T
            effluent.P = self.operating_P
            self.reaction(effluent)
    
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

        # Calculate the reactor volume
        load = self.reactor_load
        Input_Flow = load.F_vol
        tau = self.tau                      # h
        V_wf = self.V_wf            
        V_max = self.V_max                  # m3
        V_0 = Input_Flow * tau              # Working volume of the reactor
        if V_0 > V_max:
            unit = self.ID
            warn('The cost correlation parameters for tank volume have a maximum volume of {} m3. The current volume of {} is {} m3'.format(V_max, unit, V_0))

        # Add the reactor volume, the number of reactors, batch time and loading+cleaning time
        Design['Reactor volume (total)'] = (V_0/V_wf)       # m3
        Design['Hydraulic retention time'] = tau            # h
        
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
        Tf = self.operating_T               # K
        Ti = load.T                         # K
        Cp = load.Cp                        # kJ/(kg*K)
        duty = Cp * (Tf-Ti) * load.F_mass   # kJ/h
        self.add_heat_utility(duty, T_in = Ti, T_out = Tf)

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

    Batch agitated reactor with agitation power and heating/cooling duty.

    This unit mixes all inlet streams, applies a user-defined reaction model and reports
    reactor sizing and utilities for operation at a specified temperature. Reactor volume
    is estimated using the volumetric flow rate of solid and liquid streams and the combination
    of `time`, `time_loading` and `time_CIP`. Gas-phase stream are not included in volume nor 
    duty determination. Agitation power is scaled using the volumetric power.

    Parameters
    ----------
    ID : str 
        This ID refers to the name of this unit.

    ins : tuple
        Inlet streams. At least a minimun of 2 streams must be provided.
        Typical convention:
        - ins[0] substrate
        - ins[1] reactives
        - ins[2] air or gas stream (optional)
        - ...

    outs : tuple
        Outlet streams.
        - outs[0] effluent
        - outs[1] vent-out (only when `vent_out=True`)
    
    reaction : bst.Reaction | bst.ReactionSystem
        Reaction(s) taking place inside the CSTR.
    
    time : float
        time [h] used for reactor sizing.

    time_loading : float
        loading time of the reactor [h] used for reactor sizing.
    
    time_CIP : float
        Cleaning in place time of the reactor [h] used for reactor sizing.
            
    operting_P : float 
        Pressure inside the reactor [Pa]. Default to 101325 Pa.
    
    operating_T : float 
        Temperature inside the reactor [K]. Default to 298.15 K.
    
    kW_per_m3 : float
        Volumetric power used to scale-up electricity consumption [kW/m^3].
    
    N_reactors : int
        Number of reactors used. Default to 2 ensuring semicontinuous operation.
    
    vent_out : bool
        True when air/gas is being supplied. Default to False.
        
    Attributes
    ----------
    reactor_load : bst.Stream
        Mixture of input streams used for reactor sizing (typically solids and liquids
        excluding gas when `vent_out=True`).
    
    V_wf : float
        Fraction of the reactor which corresponds to working volume. Default to 0.8.
    
    V_max : float
        Maximum volume per reactor. Default to 200 m3.
    
    base_cost : float
        The cost (USD) of a reactor which volume corresponds to base_volume.
    
    base_n_cost : float
        The parameter n in the expression: base_cost * (Volume/Base_Volume)**n.
    
    base_volume : float
        The volume (m3) of a BSTR whose cost is the base_cost.
    
    CE_base : float
        The CEPCI which corresponds with the base_cost.
    
    Notes
    -----
        - Reactor sizing is based on liquid and solid phases only. Gas-phase streams are
        excluded from volume and duty calculations.

        - When `vent_out=True`, gas-phase material is separated into vent stream, while
        liquid and solids leave as effluent.
    
    """
    _N_ins = 3
    _ins_size_is_fixed = False
    _N_outs = 2
    _outs_size_is_fixed = False
    _units = {
        'Power': 'kW/m3',
        'Reactor volume (total)': 'm3',
        'Reactor volume (single)': 'm3',
        'Batch time': 'h',
        'Loading time': 'h',
        'CIP time': 'h'
    }

    def _init(self, 
              reaction: Reaction | SeriesReaction | ParallelReaction | ReactionSystem = None, 
              time: float = None, 
              time_loading: float = None,
              time_CIP: float = None,
              operating_T: float = 298.15,
              operating_P: float = 101325,
              kW_per_m3: float = None,
              N_reactors: int = 2,
              vent_out: bool = False
              ):
        """
        """
        # parameters
        self.reaction = reaction
        self.time = time
        self.time_loading = time_loading
        self.time_CIP = time_CIP
        self.operating_T = operating_T
        self.operating_P = operating_P
        self.N_reactors = N_reactors
        self.kW_per_m3 = kW_per_m3
        self.vent_out = vent_out
        
        # Attributes
        self._reactor_load = None
        self._V_wf = None
        self._V_max = None
        self._base_cost = None
        self._base_volume = None
        self._base_n_cost = None
        self._CE_base = None

    @property
    def reactor_load(self):
        """
        """
        return self._reactor_load
    
    @reactor_load.setter
    def reactor_load(self,value):
        """
        """
        self._reactor_load = value

    def _run(self):
        """
        """
        ins = list(self.ins)
        self.reactor_load = feed = bst.Stream()

        if self.vent_out:
            # Solid and liquid stream
            solid_liquid_ins = sort_streams_by_phases(ins,('s','l'))
            feed.mix_from(solid_liquid_ins)

            # Gas stream
            gases = sort_streams_by_phases(ins,('g',))

            # MultiStream
            mixture = bst.Stream()
            mixture.phases = 'gl'
            
            all_ins = gases +  [feed]

            mixture.mix_from(all_ins)

            # Reaction
            self.reaction(mixture)

            # Split phases
            effluent, vent = self.outs
            bst.separations.phase_split(mixture, (vent, effluent))
        else:
            # Ensure no gas stream was provided
            if any('g' in s.phase for s in ins):
                phases_found = [(getattr(s, 'ID', None), s.phase) for s in ins]
                raise ValueError(
                    "vent_out is False, but gas phase ('g') was found in input streams"
                    f"Phases found: {phases_found}"
                )

            # Mix all streams
            feed.mix_from(ins)

            # Reaction
            self.reaction(feed)

            # output
            effluent = self.outs[0]
            effluent.copy_like(feed)
    
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
        design = self.design_results

        # Calculate liquid and solid inputs flow
        feed = self.reactor_load
        inputs_F_vol = feed.F_vol

        # Calculate the number of batches needed to operate in semi-continuous
        time = self.time                                    # h
        time_loading = self.time_loading                    # h
        time_CIP = self.time_CIP                            # h
        
        # Total time
        total_time = time + time_loading + time_CIP         # h
        
        V_wf = self.V_wf        
        V_max = self.V_max                                  # m3
        N_reactors = self.N_reactors
        
        # Verify minimun 2 reactores
        if N_reactors < 2:
            raise ValueError("Minimum 2 reactors needed to semicontinuous mode. current: '{}'".format(N_reactors))
        
        # Liquid volume of each reactor
        V_0 = inputs_F_vol * total_time * 1/(N_reactors-1)
        
        # Total volume of each reactor
        V_total = V_0/V_wf
        if V_total > V_max:
            warn("The volume of each reactor exceeds V_max. Increase 'N_reactors': {} (current)".format(N_reactors))
        
        # Add the reactor volume, the number of reactors, batch time and loading+cleaning time
        design['Reactor volume (total)'] = V_total * N_reactors # m3
        design['Reactor volume (single)'] = V_total             # m3
        design['Batch time'] = time                             # h
        design['Loading time'] = time_loading                   # h
        design['CIP time'] = time_CIP                           # h 
        self.parallel['Reactor'] = N_reactors

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
        Ti = feed.T                             # K
        Duty = feed.Cp * (Tf-Ti) * feed.F_mass  # kJ/h
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
        V_reactor = self.design_results['Reactor volume (single)']
        
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