import json
from pathlib import Path
from .record import ChemicalRecord
from .validations import validate_chemical_record
from .exceptions import DuplicateChemicalError, ChemicalNotFoundError

class UserChemicalStorage:
    """
    """
    def __init__(self, root: str | Path | None = None):
        if root is None:
            package_dir = Path(__file__).resolve().parents[1]
            root = package_dir / "data"
        self.root = Path(root)
        self.chemicals_db_dir = self.root / "chemicals_db"
        self.chemicals_db_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_chemical_path(self, name: str) -> Path:
        if not isinstance(name,str):
            raise TypeError("chemical name must be a string.")
        return self.chemicals_db_dir / f"{name.lower()}.json"

    def save_chemical_record(
            self, 
            chemical_record: ChemicalRecord,
            overwrite: bool = False,
        ) -> None:
        # validate chemical record
        validate_chemical_record(chemical_record)

        # save chemical record
        chemical_path = self._get_chemical_path(chemical_record.name)

        if chemical_path.exists() and not overwrite:
            raise DuplicateChemicalError(chemical_record.name)
        
        with chemical_path.open("w",encoding="utf-8") as file:
            json.dump(
                chemical_record.to_dict(),
                file,
                indent = 4,
                ensure_ascii = False
            )
    
    def load_chemical_record(self, name: str) -> ChemicalRecord:
        """
        
        Load a ChemicalRecord from storage by its name.

        """

        chemical_path = self._get_chemical_path(name)

        if not chemical_path.exists():
            raise ChemicalNotFoundError
        
        with chemical_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return ChemicalRecord.from_dict(data)
    
    def has_chemical_record(self, name: str) -> bool:
        """
        
        Return True if a chemical record with the given name exists in the database.

        """
        chemical_path = self._get_chemical_path(name)
        return chemical_path.exists()
    
    def list_chemical_names(self) -> list[str]:
        """
        
        Return the names of all stored chemical records.

        """
        return sorted(path.stem for path in self.chemicals_db_dir.glob("*.json"))