"""

This script contains all the helpers used to
improve the handling of bst.Stream objects

"""
from __future__ import annotations
from typing import Literal, Sequence, Protocol, runtime_checkable
import pandas as pd

__all__ = (
    "extract_components_flow",
    "calculate_stream_price",
)

@runtime_checkable
class _StreamLike(Protocol):
    available_chemicals: list[object]
    @property
    def imass(self): ...
    @property
    def imol(self): ...
    @property
    def F_mass(self): ...

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

def calculate_stream_price(composition_price: dict = None, *,stream: _StreamLike = None, chems_price: dict = None, basis: Literal["mass", "molar"] = "mass"):
    """
    """
    if (stream or chems_price) is not None:
        # Check if all parmeters are provided
        if chems_price is None: raise ValueError("A price dictionary of each chemical must be given")
        if stream is None: raise ValueError("A bst.Stream object must be provided")

        # Get a dict with each chemical and its flow
        flows = extract_components_flow(stream, basis)
        total = stream.F_mass

        # Calculate the price of the stream per kg as the composition of each chemical multiplied by its price
        stream_price = 0
        for key, value in flows.items():
            if key in chems_price:
                mass_composition = value/total
                stream_price += mass_composition * chems_price[key]
            else:
                raise KeyError("The next chemical could not be found in the chems_price dictionary: {}".format(key))

        return stream_price
    elif composition_price is not None:
        # Get the stream price as composition multiplied by price
        stream_price = 0
        for key, value in composition_price.items():
            stream_price += key * value
        
        return stream_price
    else:
        raise ValueError("Either composition_price or stream and chems_price must be provided.")