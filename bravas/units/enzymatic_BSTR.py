"""
"""
import biosteam as bst
from .reactors import BatchAgitatedReactor
from ..tools.reactiontools import load_reaction_library, build_reaction_from_dict
from importlib.resources import files

__all__ = ("BatchEnzymaticTreatment",)

class BatchEnzymaticTreatment(BatchAgitatedReactor):
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
    
    reaction : str | bst.Reaction | bst.ReactionSystem
        Reaction(s) taking place inside the CSTR. To select one of
        the reaction preset above, provide a string with the desired
        reaction ID.

        - "Protein extraction (Viscozyme)": ``Protein -> Protein_Soluble``
        - "Protein extraction (Trypsin)": ``Protein -> Peptides``
        - "Protein hydrolysis (Trypsin)": ``Protein_Soluble -> Peptides``
    
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
    def _init(
            self, 
            reaction: str | bst.Reaction | bst.ParallelReaction | bst.SeriesReaction | bst.ReactionSystem = None, 
            time = None, 
            time_loading = None, 
            time_CIP = None, 
            operating_T = 298.15, 
            operating_P = 101325, 
            kW_per_m3 = None, 
            N_reactors = 2, 
            vent_out = False
        ):
        # Use default reactions when a str is provided
        if isinstance(reaction,str):
            # Load json library
            lib_path = files("bravas").joinpath("data","reactions.json")
            library = load_reaction_library(lib_path)
            
            # search if the reaction exists
            if reaction not in library:
                raise ValueError(
                    f"Unknown reaction preset '{reaction}'."
                    f"Available: {list(library.keys())}"
                )

            # build reaction
            reaction = build_reaction_from_dict(library[reaction])

        return super()._init(reaction, time, time_loading, time_CIP, operating_T, operating_P, kW_per_m3, N_reactors, vent_out)