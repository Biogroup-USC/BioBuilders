"""
"""
from __future__ import annotations

class BRAVASChemError(Exception):
    """Base class for all BRAVAS chemical database / connector errors"""

class ChemicalNotFound(BRAVASChemError, LookupError):
    """
    
    Raised when a chemical cannot be resolved in:
    - User DB
    - BRAVAS embedded DB
    - BioSTEAM/ThermoSTEAM/ChEDL

    """
    def __init__(self, identifier: str, where: str | None = None):
        self.identifier = identifier
        self.where = where
        msg = f"Chemical '{identifier}' was not found"
        if where:
            msg += f" ({where})"
        super().__init__(msg)

class UnsupportedProperty(BRAVASChemError, KeyError):
    """
    
    

    """
