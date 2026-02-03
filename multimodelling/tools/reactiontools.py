import json
import biosteam as bst
from pathlib import Path

def load_reaction_library(json_path: str | Path) -> dict:
    """

    Load a reaction library from a JSON file.

    This functions reads a JSON file containing predefined reaction
    definitions and returns them as a Python dictionary. Each top-level
    key corresponds to a reaction preset definition and each value contains
    the data required to construct a BioSTEAM reaction object (e.g., Reaction
    or ReactionSystem).

    Parameters
    ----------
    json_path : str or pathlib.Path
        Path to the JSON file containing the reaction library
    
    Returns
    -------
    dict
        Dictionary with reaction preset definitions loaded from a JSON file.
    
    Notes
    -----
    This function performs no validation of the reaction definitions.
    Structural and chemical consistency checks should be performed
    separately before constructing BioSTEAM reaction objects.

    """
    json_path = Path(json_path)
    with json_path.open("r",encoding="utf-8") as file:
        return json.load(file)

def _validate_reaction_arguments(d: dict):
    """

    Validate a reaction preset definition.

    This functions performs a validation of a reaction definition
    dictionary (typically loaded from a JSON reaction library). It
    checks that required keys are present and that key values satisfy
    basic constraints (e.g., conversion bounds, basis options).

    Parameters
    ----------
    d: dict
        Reaction definition dictionary. Expected keys (for type="Reaction"):

        - basis : {"mol", "wt"}
        - type : {"Reaction"}
        - reactant : str
        - conversion : float
        - stroichiometry : dict[str, float]
    
    Notes
    -----
    This function does not verify that species IDs exist in the current
    BioSTEAM/thermosteam chemicals object. Chemical consistency should
    be checked separately (e.g., before constructing the reaction object)

    """
    if "basis" not in d:
        raise ValueError("Missing key 'basis'. Expected 'mol' or 'wt'")
    
    if d["basis"] not in ("mol","wt"):
        raise ValueError(f"Invalid basis: {d['basis']}. Use 'mol' or 'wt'")
    
    if d["type"] == "Reaction":
        for k in ("reactant","conversion","stoichiometry"):
            if k not in d:
                raise ValueError(f"Missing key: '{k}' in reaction definition.")
        
        X = d["conversion"]
        if not (0 <= X <= 1):
            raise ValueError(f"Conversion must be between 0 and 1. Got {X}.")
        
        if d["reactant"] not in d["stoichiometry"]:
            raise ValueError("reactant must appear in stoichiometry dict.")
    else:
        raise ValueError("Only Reaction supported by now.")

def build_reaction_from_dict(d: dict) -> bst.Reaction:
    """
    """
    _validate_reaction_arguments(d)

    react_type = d["type"]
    if react_type == "Reaction":

        stoich = d["stoichiometry"]

        reactants = [f"{-nu} {ID}" for ID, nu in stoich.items() if nu < 0]
        products = [f"{-nu} {ID}" for ID, nu in stoich.items() if nu > 0]

        react_string = "+".join(reactants) + "->" "+".join(products)

        reaction = bst.Reaction(
            reaction=react_string,
            reactant=d["reactant"],
            X=d["conversion"],
            basis=d["basis"]
        )

        return reaction
    
    else:
        raise ValueError("Only Reaction supported by now")