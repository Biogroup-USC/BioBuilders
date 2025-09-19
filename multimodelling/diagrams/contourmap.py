"""
"""
import biosteam as bst
import numpy as np
import pandas as pd
from dataclasses import dataclass

__all__ = (
    "ContourStudy",
)

@dataclass
class CSParameter:
    name: str
    setter: callable[[float], None]
    element: object = None
    units: str = None
    baseline: float = None
    bounds: tuple = None
    n: int = None
    levels: float = None
    coupled: bool = False
    description: str = None

@dataclass
class CSIndicator:
    name: str
    getter: callable[[], float]
    units: str = None
    element: object  = None

class ContourStudy:
    """
    """
    def __init__(self,
                 TEA: bst.TEA = None,
                 specification: callable = None,
                 *,
                 retry: bool = True):
        # Check if the object provided has a method called simulate
        if TEA is None or not hasattr(TEA, "system"):
            raise ValueError("The TEA object provided must include a system to simulate")
        if not hasattr(TEA.system, "simulate"):
            raise ValueError("The system has not .simulate()")

        # Parameters
        self.TEA = TEA
        self.system = TEA.system
        self.specification = specification
        self.retry = bool(retry)

        # Properties
        self._parameters = None
        self._indicators = None 

    @property
    def parameters(self):
        """
        """
        if self._parameters is None:
            self._parameters = []
            return self._parameters

    @property
    def indicators(self):
        """
        """
        if self._indicators is None:
            self._indicators = []
            return self._indicators

    # Define parameters using BioSTEAM conventions
    def parameter(self,*, name = None, element = None, units = None, baseline = None,
                  bounds = None, n = None, levels = None, coupled = False, description = None):
        def decorator(setter_fn: callable[[float], None]):
            p = CSParameter(
                name=name or setter_fn.__name__,
                setter=setter_fn, element=element, units=units, baseline=baseline,
                bounds=bounds,n=n, levels=levels, coupled=coupled,description=description 
            )
            # Validation to avoid mixing levels and n
            if p.levels is not None and p.bounds is not None:
                raise ValueError("Use bounds or levels, not both")
            self.parameters.append(p)
            return setter_fn
        return decorator
    
    # Define indicator using BioSTEAM conventions
    def indicator(self,*, name = None, units = None, element = None):
        def decorator(getter_fn: callable[[],float]):
            ind = CSIndicator(
                name=name or getter_fn.__name__,
                getter=getter_fn, units=units, element=element
            )
            self._indicators.append(ind)
            return getter_fn
        return decorator
    
    def build_grid():
        """
        """
