"""
"""
import json
from pathlib import Path
from typing import Any, Mapping

def _load_json(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    """

    Load a JSON from a file path or return a copy of an already-loaded mapping.

    This function returns a dictionary with all unit operation parameters,
    techno-economic parameters and stream prices. The information related to
    each process can be stored in a JSON file, facilitating the implementation
    of any change required.

    Parameters
    ----------
    source : str, pathlib.Path or Mapping
        Either a Path to a JSON file or a dictionary-like object containing the
        already-loaded specification.

    Returns
    -------
    A dictionary containing the parsed JSON data.

    Notes
    -----
    This function performs no validation of keys, value types or schema consistency.
    Validation is expected to be handled by higher-level parsing function.

    """
    if isinstance(source, Mapping):
        return dict(source)
    path = Path(source)
    with path.open("r",encoding="utf-8") as file:
        return json.load(file)

def parse_case_spec(source: str | Path | Mapping[str,Any]) -> dict[str,Any]:
    """

    Parse a user-defined case specification and extract normalised parameter
    dictionaries.

    This function reads a JSON-based case specification and returns plain
    Python dictionaries containing:
        
        - unit operation parameters
        - techno-economic analysis (TEA) parameters
        - stream price definition
    
    Parameters
    ----------
    source : str, pathlib.Path or Mappping
        Path to a JSON file defining the case study or a dictionary containing the
        already-loaded specification.
    
    Expected JSON structure
    -----------------------
    The input specification must contain the following top-level keys:

    - ``"unit_operations"``: dict
        Mapping of unit IDs to dictionaries of unit-specific parameters.
    - ``"techno_economic"``: dict
        Dictionary containing TEA-related parameters.
    - ``"stream_prices"``: dict
        Mapping of stream identifiers to numeric price values.
    
    Returns
    -------
    dict
        A dictionary with following keys:

        - ``"unit_operations"`` : dict
            Mapping of unit_IDs to parameter dictionaries.
        -``"techno_economic"`` : dict
            Techno-economic analysis parameters.
        -```"stream_prices"`` : dict
            Mapping of stream identifiers to prices (converted to ``float``).
    
    Raises
    ------
    ValueError
        If required section are missing or if any section does not have the expected
        dictionary structure.

    """
    # Load JSON file
    spec = _load_json(source)

    # Unit operation related parameters
    units = spec.get("unit_operations")
    if units is None or not isinstance(units,dict):
        raise ValueError("'unit operations' must be provided")
    
    units_params: dict[str,dict[str,Any]] = {}
    
    for unit_id, u in units.items():
        # Check if a dict with unit parameters was provided
        if not isinstance(u, dict):
            raise ValueError(f"Unit '{unit_id}' must be a dict")
        
        units_params[unit_id] = u
    
    # TEA related parameters
    tea_params = spec.get("techno_economic")
    if not isinstance(tea_params, dict):
        raise ValueError("'techno-economic' must be a dict")
    
    # Stream prices
    stream_prices = spec.get("stream_prices")
    if not isinstance(stream_prices, dict):
        raise ValueError("'stream prices' must be a dict")
    
    stream_prices = {str(k): float(v) for k,v in stream_prices.items()}

    return {
        "unit_operations": units_params,
        "techno-economic": tea_params,
        "stream_prices": stream_prices,
    }