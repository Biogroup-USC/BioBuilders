"""

This script contains all the helpers used to
improve the handling of bst.Stream objects

"""
from __future__ import annotations
from typing import Literal, Sequence, Protocol, runtime_checkable
import pandas as pd

__all__ = (
    "extract_components_flow",
)

@runtime_checkable
class _StreamLike(Protocol):
    available_chemicals: list[object]
    @property
    def imass(self): ...
    @property
    def imol(self): ...

def _get_available_chemicals_ID(chemicals: list[object]) -> list[str]:
    """
    """
    return [str(chem.ID) for chem in chemicals]

def extract_components_flow(
       stream: _StreamLike,
       *,
       basis: Literal["mass","molar"] = "mass",
       components: Sequence[str] | None = None,
       as_series: bool = False,
)-> pd.Series | dict[str, float]:
    """
    """
    # If no components given, use available chemicals
    chems = (
        _get_available_chemicals_ID(stream.available_chemicals)
        if not components else list(components)
    )

    # Validate basis
    if basis not in ("mass","molar"):
        raise ValueError("basis must be either 'mass' or 'molar'")
    # get the proper accesor
    acc = stream.imass if basis == "mass" else stream.imol
    label = "mass_flow" if basis == "mass" else "molar_flow"

    # Get the flows depending on basis
    comp_flows: dict[str, float] = {}
    for comp in chems:
        try:
            val = acc[comp]
        except KeyError as e:
            raise KeyError("Component not found: {}".format(comp)) from e
        comp_flows[comp] = float(val)
    
    # transform it to pandas Series if requested
    if as_series:
        return pd.Series(comp_flows,name=label)
    return comp_flows