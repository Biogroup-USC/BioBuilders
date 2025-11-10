"""
"""
import re
import warnings
import numbers

__all__ = (
    "normalise_key",
    "coerce_value",
    "warn_unknown_keys",
)

ALIAS = {
    "Rho": "rho", "density": "rho",
    "hvap": "Hvap", "h_vap": "Hvap", "hvap": "Hvap",
    "mw": "MW", "mw_g_per_mol": "MW", "mol_weight": "MW",
    "Phase_ref": "phase_ref", "Phase_Ref": "phase_ref", "phase": "phase_ref", "Phase": "phase_ref",
    "cp": "Cp", "psat": "Psat", "hf": "Hf", "v": "V", "Formula": "formula",
}

VALID_KEYS = ["rho","Hvap","MW","phase_ref","Cp","Psat","Hf","V","formula"]

def normalise_key(raw_key: str) -> str:
    """

    Normalise chemical property keys to BioSTEAM-compatible names.

    Parameters
    ----------
    raw_key : str
        Property name from database, file or user input.

    Returns
    -------
    str
        Normalised property name recognised by BioSTEAM.

    """
    # Basic cleaning
    key = raw_key.strip().lower()
    key = key.replace("-", "_").replace(" ", "_")
    key = re.sub(r"\(.*?\)", "", key)

    # Apply ALIAS
    normalised = ALIAS.get(key,key)

    # Check valid key
    if normalised not in VALID_KEYS:
        warnings.warn("Unrecognised property key '{}' (interpreted as '{}')".format(raw_key,normalised))

    return normalised

def coerce_value(key: str, v):
    """

    Coerce (convert) a raw value from DB or user input into the
    correct Python type expected by BioSTEAM for a given chemical
    property

    """
    # Nothing to do if type is already correct
    if v is None or isinstance(v,(bool,numbers.Number,callable)):
        return v
    
    # Take away spaces and not essential characters
    if isinstance(v, str):
        val = v.strip()
        # Empty or null
        if val in ("","none","null","nan","NA","N/A"):
            return None

        # Normalise text
        if key in ("phase","phase_ref"):
            val = val.lower().strip()
            if val in ("l","liquid","liq"): return "l"
            if val in ("g","gas","vapour","vapor"): return "g"
            if val in ("s","solid"): return "s"
        
        if key == "formula":
            return val
        
        # Try to convert to number
        try:
            return float(val)
        except ValueError:
            # Cannot convert it
            return v
    
    # If the value has another type, return it
    return v

def validate_minimums(kwargs: dict, *, strict: bool=True) -> None:
    """
    """
    MW = kwargs.get("MW")
    rho = kwargs.get("rho")
    V = kwargs.get("V")

    missing = []

    # Basic checks
    if MW is None: missing.append("MW")
    if rho is None and V is None: missing.append("rho or V")

    # Validate
    if rho is not None and MW is not None and V is not None:
        rho_calc = (MW/1000)/V
        diff = abs(rho_calc - rho) /rho
        if diff > 0.2:
            msg = (f"Inconsistent rho-V-MW relationship for '{kwargs.get('ID')}'."
                   f"Expected rho={rho_calc:.1f} kg/m3, got {rho:.1f} kg/m3.")
            if strict:
                raise ValueError(msg)
            else:
                warnings.warn(msg)
    
    # Missing properties
    if missing:
        msg = (f"Chemical '{kwargs.get("ID")}' is missing required properties: "
               f"{', '.join(missing)}")
        if strict:
            raise ValueError(msg)
        else:
            warnings.warn(msg)

def warn_unknown_keys(kwargs: dict, *, valid_keys: list[str] = VALID_KEYS, strict: bool = False) -> None:
    """
    """
    keys = set(kwargs.keys())
    unknown = []
    for key in valid_keys:
        if key not in keys:
            unknown.append(key)
        else:
            continue
    
    msg = (
        f"Chemical '{kwargs.get('ID')}' includes unrecognized keys: "
        f"{', '.join(sorted(unknown))}. "
        "These will be ignored unless handled explicitly."
    )

    if strict:
        raise ValueError(msg)
    else:
        warnings.warn(msg)