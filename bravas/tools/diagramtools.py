"""
"""
import os
import pandas as pd
import re
from collections import Counter
from typing import Literal

__all__ = (
    "simplify_labels",
    "keep_multiindex_last_level",
    "get_dataframe_positions",
    "sanitize_filename",
    "filename_to_save",
)

def build_pattern(key: str, label: str, sep: Literal["auto","underscore","space"] = "auto") -> str:
    """

    Build a regex pattern to match `key` inside `label`.

    Parameters
    ----------
    key : str
        Keyword to search.
    label : str
        Label where keyword will be searched.
    sep : {"auto", "underscore", "space"}
        - "auto": detect based on label content.
        - "underscore": treat "_" and spaces as separators.
        - "space": use word boundaries (\b).

    """
    key_esc = re.escape(str(key).lower())
    label = str(label).lower()

    if sep == "auto":
        if "_" in label:
            sep = "underscore"
        else:
            sep = "space"

    if sep == "underscore":
        return rf"(^|[_\s]){key_esc}([_\s]|$)"
    elif sep == "space":
        return rf"\b{key_esc}\b"
    else:
        raise ValueError("sep must be 'auto', 'underscore' or 'space'")

def simplify_labels(full_labels: list = None, keywords: list | dict = None, sep: str = "space"):
    """

    Simplify column labels based on provided keywords.

    If keyword is:
        - dict: returns "key units",
        - list: retunrs "key",
        - None: returns original labels
    
    Parameters
    ----------
    full_labels : list
        List of original labels (Typically a `df.columns`).
    keywords : list | dict
        Keywords to search for within each label (case-insensitive).

        - if a list is provided, the first keyword found is used as the simplified label.
        - if a dict is provided, the simplified label is the dict key and units are appended
        as `"key units"`.
    sep : {'space','underscore', 'auto'}
        Separator logic used to build the regex pattern:

        - 'space': matches whole words using word boundaries.
        - 'underscore': treats '_' and whitespaces as separators.
        - 'auto': if the string contains '_' the function uses 'underscore' as `sep`.

    """

    # if keywords are not provided, give back the original labels
    if keywords is None:
        return list(full_labels)
    
    simplified_labels = []
    for label in full_labels:
        # Avoid error with upper/lower letters
        lower_label = str(label).lower()

        # Robust matching using word boundaries
        def match_key(key):
            pattern = build_pattern(key, lower_label, sep)
            return re.search(pattern, lower_label)

        if isinstance(keywords, dict):
            match = next(
                (
                    f"{key} {units}"
                    for key,units in keywords.items()
                    if match_key(key)
                ),
                label
            )
        else:
            match = next(
                (
                    key for key in keywords if match_key(key)
                ),
                label
            )

        # append simplified label
        simplified_labels.append(match)
    
    # Count labels that may be duplicated
    counts = Counter(simplified_labels)
    duplicates = [label for label, n in counts.items() if n > 1]
    if duplicates:
        raise ValueError(
            f"Some duplicated labels encountered: {duplicates} "
            "Adjust 'keywords' to avoid collisions."
        )

    # Return the list of simplified labels
    return simplified_labels

def keep_multiindex_last_level(df: pd.DataFrame) -> pd.DataFrame:
    """

    Keep only the last level of a Multiindex on both row index and columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame which may have Multiindex on rows and/or columns
    
    Returns
    -------
    A new DataFrame with its rows and columns replaced by their last level values

    """
    df_copy = df.copy()

    # Keep last level for columns
    if isinstance(df_copy.columns, pd.MultiIndex):
        last_col = df_copy.columns.get_level_values(-1)
        last_col_name = df_copy.columns.names[-1]
        df_copy.columns = pd.Index(last_col, name = last_col_name)
    
    # Keep last level for index
    if isinstance(df_copy.index, pd.MultiIndex):
        last_idx = df_copy.index.get_level_values(-1)
        last_idx_name = df_copy.index.names[-1]
        df_copy.index = pd.Index(last_idx, name = last_idx_name)
    
    return df_copy

def get_dataframe_positions(df: pd.DataFrame, labels: list[str], axis: int = 1) -> list[int]:
    """

    Get interger positions of given labels in the last level of a Multiindex (or flat index) on
    a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing the data.
    labels : list[str]
        List of label names to locate in the index or columns.
    axis : int
        1 for columns, 0 for index.        
    """
    # Select the axis
    obj = df.columns if axis == 1 else df.index

    # Extract last level
    if isinstance(obj, pd.MultiIndex):
        values = list(obj.get_level_values(-1))
    else:
        values = list(obj)

    # Map input labels to their last-level string representation
    mapped_labels = []
    for lab in labels:
        if isinstance(lab,(tuple, list)):
            mapped_labels.append(lab[-1])
        else:
            mapped_labels.append(lab)

    positions = []
    for lab_val in mapped_labels:
        if lab_val in values:
            positions.append(values.index(lab_val))
        else:
            raise KeyError("Label '{}' not found in {}. Available: {}".format(lab_val, 'columns' if axis == 1 else 'index', values))
    
    return positions

def sanitize_filename(filename: str) -> str:
    """

    Change every character besides letter, number, hyphen or underscore for
    underscore avoiding slash, spaces, etc.

    Parameters
    ----------
    filename : str
        Name of the file to sanitize.

    Return
        Sanitized filename.

    """
    return re.sub(r'[^A-Za-z0-9\-_]+','_',filename).strip('_')

def filename_to_save(path: str, filename: str, default_filename: str, extension: str, create_new: bool = True):
    """
    """
    # Check if path exists
    os.makedirs(path,exist_ok=create_new)

    # check if filename is provided or use default
    if filename is None:
        filename = default_filename
    
    # check if the extension was provided in the filename
    if extension is None:
        raise ValueError("An extension must be provided.")
    
    if not filename.lower().endswith(extension):
        filename += extension
    
    # Build file path
    file_path = os.path.join(path,filename)
    return file_path