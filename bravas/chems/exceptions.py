__all__ = (
    "DuplicateChemicalError",
    "ChemicalNotFoundError",
)

class BRAVASChemError(Exception):
    """
    
    Base class for all BRAVAS chemical-related errors.

    """
    pass

class DuplicateChemicalError(BRAVASChemError):
    """
    
    Raised when attempting to store a chemical that already exists
    in the user chemical database.

    """

    def __init__(self, name: str):
        self.name = name
        msg = f"Chemical '{name}' already exists in the database."
        super().__init__(msg)

class ChemicalNotFoundError(BRAVASChemError):
    """
    
    Raised when a chemical does not exist in the chemical database.

    """

    def __init__(self, name: str, database: str = 'user'):
        self.name = name
        self.database = database
        msg = f"Chemical '{name}' not found in the {database} chemical database."
        super().__init__(msg)