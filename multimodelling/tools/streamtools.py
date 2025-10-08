"""

This script contains all the helpers used to
improve the handling of bst.Stream objects

"""
from __future__ import annotations
from typing import Literal, Sequence
import pandas as pd

__all__ = ()

class _Streamlike:
    available_chemicals: list[object]
    imass: object
    imol: object

def extract_components_flow(
       stream: _Streamlike,
       *,
       basis: Literal["mass","molar"] = "mass",
       components: Sequence[str] | None = None,
       as_series: bool = False,
)-> pd.Series | dict[str, float]:
    """
    """
    if not components:
        chems = stream