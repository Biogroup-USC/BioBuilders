from biosteam import Chemical, Chemicals, settings, Mixture, IdealMixture, ActivityCoefficients, FugacityCoefficients, PoyintingCorrectionFactors
from .storage import UserChemicalStorage
from typing import Iterable, Literal
from .exceptions import ChemicalNotFoundError

class ChemicalsManager:
    """
    """
    def __init__(self, chemical_list: Iterable[str | Chemical], storage: UserChemicalStorage = None, skip_checks: bool = False):
        self.chemical_list = list(chemical_list)
        self.db = storage if storage is not None else UserChemicalStorage()

        self._compiled_chemicals = None
        self._skip_checks = skip_checks

    def _resolve_chemical_from_storage(self, chemical_id: str) -> Chemical:
        """
        """
        if not self.db.has_chemical_record(chemical_id):
            raise ChemicalNotFoundError(chemical_id)
        
        record = self.db.load_chemical_record(chemical_id)
        
        if record.aliases is None:
            aliases = None
        else:
            aliases = sorted(record.aliases)

        if record.copy_missing_from.strip().lower() == "water":
            default = True
        else:
            default = False

        chemical = Chemical(
            ID = record.name,
            CAS = record.CAS,
            search_ID = False,
            search_db = False,
            default = default,
            MW = record.MW,
            formula = record.formula,
            aliases = aliases,
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
        except LookupError:
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
                seen.add(chem.ID)

        return Chemicals(chemicals_list)

    def _compile_chemicals(self):
        chemicals = self.get_chemicals_object()
        chemicals.compile(skip_checks=self.skip_checks)
        return chemicals

    @property
    def skip_checks(self):
        return self._skip_checks

    @skip_checks.setter
    def skip_checks(self, value: bool):
        value = bool(value)
        if value != self._skip_checks:
            self._skip_checks = value
            self.reset_chemicals()

    @property
    def compiled_chemicals(self):
        if self._compiled_chemicals is None:
            self._compiled_chemicals = self._compile_chemicals()
        return self._compiled_chemicals

    def reset_chemicals(self):
        self._compiled_chemicals = None

    def add_chemical(self, chemical: str | Chemical):
        self.chemical_list.append(chemical)
        self.reset_chemicals()

    def remove_chemical(self, chemical: str | Chemical):
        if isinstance(chemical, str):
            chemical_id = chemical
        elif isinstance(chemical, Chemical):
            chemical_id = chemical.ID
        else:
            raise ValueError(
                f"Only 'str' or 'bst.Chemical' is supported."
            )
        
        new_list = []
        removed = False

        for chem in self.chemical_list:
            current_id = chem if isinstance(chem, str) else chem.ID
            if current_id == chemical_id and not removed:
                removed = True
                continue
            new_list.append(chem)
        
        if not removed:
            raise ChemicalNotFoundError(chemical_id)
        
        self.chemical_list = new_list
        self.reset_chemicals()

    def set_thermodynamics(
            self,
            mixture_class: Mixture = IdealMixture, 
            activity_coeff: ActivityCoefficients  = None,
            fugacity_coeff: FugacityCoefficients = None,
            poyinting_coeff: PoyintingCorrectionFactors = None,
            package: Literal['ideal gas','Peng Robinson', 'Dortmund-UNIFAC', 'Peng Robinson | Dortmund-UNIFAC'] = None
        ):
        # cached chemicals
        chemicals = self.compiled_chemicals

        settings.set_thermo(
            thermo = chemicals,
            mixture = mixture_class.from_chemicals(chemicals),
            Gamma = activity_coeff,
            Phi = fugacity_coeff,
            PCF = poyinting_coeff,
            pkg = package,
        )
        settings.thermo.show()
        return chemicals