from .record import ChemicalRecord, SourceInfo

__all__ = (
    "validate_chemical_record",
)

def validate_chemical_record(chemical_record: ChemicalRecord):
    
    # Check object type
    if not isinstance(chemical_record, ChemicalRecord):
        raise TypeError(
            f"chemical_record must be a ChemicalRecord instance, "
            f"got {type(chemical_record).__name__}."
        )

    # Required fields
    if not isinstance(chemical_record.name, str):
        raise TypeError("name must be a str.")
    if not chemical_record.name.strip():
        raise ValueError("name must not be empty.")

    if not isinstance(chemical_record.source, SourceInfo):
        raise TypeError("source must be a SourceInfo instance.")

    if not isinstance(chemical_record.properties, dict):
        raise TypeError("properties must be a dict.")

    # Optional fields
    if chemical_record.CAS is not None and not isinstance(chemical_record.CAS, str):
        raise TypeError("CAS must be a str or None.")

    if chemical_record.formula is not None and not isinstance(chemical_record.formula, str):
        raise TypeError("formula must be a str or None.")

    if chemical_record.MW is not None:
        if not isinstance(chemical_record.MW, (int, float)):
            raise TypeError("MW must be a number or None.")
        if chemical_record.MW <= 0:
            raise ValueError("MW must be > 0.")

    if not isinstance(chemical_record.aliases, list):
        raise TypeError("aliases must be a list.")
    if not all(isinstance(alias, str) for alias in chemical_record.aliases):
        raise TypeError("all aliases must be strings.")

    if (
        chemical_record.copy_missing_from is not None
        and not isinstance(chemical_record.copy_missing_from, str)
    ):
        raise TypeError("copy_missing_from must be a str or None.")

    if chemical_record.notes is not None and not isinstance(chemical_record.notes, str):
        raise TypeError("notes must be a str or None.")

    if not isinstance(chemical_record.is_pseudochemical, bool):
        raise TypeError("is_pseudochemical must be a bool.")