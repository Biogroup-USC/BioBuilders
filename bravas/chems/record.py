from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

@dataclass(slots=True)
class SourceInfo:
    """
    
    Metadata about the source from which the chemical definition comes. 

    """
    origin: str
    identifier: str
    notes: str | None = None

@dataclass(slots=True)
class ChemicalRecord:
    """
    
    Canonical internal representation of a chemical definition.

    """
    name: str
    source: SourceInfo

    CAS: str | None = None
    formula: str | None = None
    MW: float | None = None
    aliases: list[str] = field(default_factory=list)

    phase: Literal['s','l','g'] = 'l'
    phase_ref: Literal['s','l','g'] = 'l'
    Cp: float | None = None
    rho: float | None = None
    V: float | None = None

    properties: dict[str,Any] = field(default_factory=dict)
    copy_missing_from: str | None = None
    notes: str | None = None

    is_pseudochemical: bool = False

    def to_dict(self)->dict[str,Any]:
        return {
            "name": self.name,
            "source": {
                "origin": self.source.origin,
                "identifier": self.source.identifier,
                "notes": self.source.notes
            },
            "CAS": self.CAS,
            "formula": self.formula,
            "MW": self.MW,
            "aliases": self.aliases,
            # Common properties
            "phase": self.phase,
            "phase_ref": self.phase_ref,
            "Cp": self.Cp,
            "rho": self.rho,
            "V": self.V,
            # Other properties
            "properties": self.properties,
            "copy_missing_from": self.copy_missing_from,
            "notes": self.notes,
            "is_pseudochemical": self.is_pseudochemical,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str,Any]) -> "ChemicalRecord":
        source_data = data["source"]
        return cls(
            name=data["name"],
            source=SourceInfo(
                origin=source_data["origin"],
                identifier=source_data["identifier"],
                notes=source_data.get("notes"),
            ),
            CAS=data.get("CAS"),
            formula=data.get("formula"),
            MW=data.get("MW"),
            aliases=data.get("aliases", []),
            phase=data.get("phase","l"),
            phase_ref=data.get("phase_ref","l"),
            Cp=data.get("Cp"),
            rho=data.get("rho"),
            V=data.get("V"),
            properties=data.get("properties", {}),
            copy_missing_from=data.get("copy_missing_from"),
            notes=data.get("notes"),
            is_pseudochemical=data.get("is_pseudochemical", False),
        )