from biosteam import Chemical, Chemicals, settings, Mixture, IdealMixture
from .storage import UserChemicalStorage
from typing import Iterable
from .exceptions import ChemicalNotFoundError

class ChemicalsManager:
    """
    """
    def __init__(self, chemical_list: Iterable[str | Chemical], storage: UserChemicalStorage = None):
        self.chemical_list = list(chemical_list)
        self.db = storage if storage is not None else UserChemicalStorage()

    def _resolve_chemical_from_storage(self, chemical_id: str) -> Chemical:
        """
        """
        if not self.db.has_chemical_record(chemical_id):
            raise ChemicalNotFoundError(chemical_id)
        
        record = self.db.load_chemical_record(chemical_id)
        
        chemical = Chemical(
            ID = record.name,
            CAS = record.CAS,
            search_ID = False,
            search_db = False,
            MW = record.MW,
            formula = record.formula,
            aliases = sorted(record.aliases),
            phase = record.phase,
            phase_ref = record.phase_ref,
            Cp = record.Cp,
            rho = record.rho,
            V = record.V,
            **record.properties
        )
        return chemical

    def _resolve_chemical_from_biosteam(self, chemical_id: str) -> Chemical:
        try:
            chemical = Chemical(chemical_id)
            return chemical
        except LookupError as e:
            raise ChemicalNotFoundError(chemical_id,'BioSTEAM/ChEDL')
    
    def get_chemical_object(self, chemical: str | Chemical) -> Chemical:
        if isinstance(chemical, Chemical):
            return chemical
        
        try:
            return self._resolve_chemical_from_storage(chemical)
        except ChemicalNotFoundError:
            return self._resolve_chemical_from_biosteam(chemical)

    def get_chemicals_object(self):
        chemicals_list = []
        seen = set()

        for chemical in self.chemical_list:
            chem = self.get_chemical_object(chemical)
            if chem.ID not in seen:
                chemicals_list.append(chem)
                seen.add(chem)

        return Chemicals(chemicals_list)

    def compile_chemicals(self, skip_checks: bool = False):
        chemicals = self.get_chemicals_object()
        chemicals.compile(skip_checks=skip_checks)
        return chemicals

    def set_thermodynamics(self, skip_checks: bool = False, mixture_class: Mixture = IdealMixture):
        chemicals = self.compile_chemicals(skip_checks=skip_checks)
        settings.set_thermo(
            thermo = chemicals,
            mixture = mixture_class.from_chemicals(chemicals)
        )
        settings.thermo.show()
        return chemicals