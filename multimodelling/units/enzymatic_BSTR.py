"""
"""
import biosteam as bst
from warnings import warn
from .reactors import BatchAgitatedReactor
from ..tools.reactiontools import load_reaction_library, build_reaction_from_dict
from pathlib import Path

__all__ = ("BatchEnzymaticTreatment",)

class BatchEnzymaticTreatment(BatchAgitatedReactor):
    """
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
            lib_path = Path(__file__).with_name("reactions.json")
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