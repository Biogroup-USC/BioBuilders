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

def keep_multiindex_last_level(df: pd.DataFrame,*,check_unique:bool = True) -> pd.DataFrame:
    """

    Keep only the last level of a Multiindex on both row index and columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame which may have Multiindex on rows and/or columns.
    check_unique : bool
        If True, raise an error if flattening creates duplicate labels.
    
    Returns
    -------
    A new DataFrame with its rows and columns replaced by their last level values

    """
    df_copy = df.copy()

    # Columns
    if isinstance(df_copy.columns, pd.MultiIndex):
        last_col = df_copy.columns.get_level_values(-1)
        last_col_name = df_copy.columns.names[-1]
        df_copy.columns = pd.Index(last_col, name = last_col_name)

        if check_unique and not df_copy.columns.is_unique:
            duplicates = df_copy.columns[df_copy.columns.duplicated()].unique().tolist()
            raise ValueError(
                "Flattening MultiIndex columns to the last level produced duplicate labels: "
                f"{duplicates}. Provide full MultiIndex labels upstream or rename to avoid collisions."
            )

    # Keep last level for index
    if isinstance(df_copy.index, pd.MultiIndex):
        last_idx = df_copy.index.get_level_values(-1)
        last_idx_name = df_copy.index.names[-1]
        df_copy.index = pd.Index(last_idx, name = last_idx_name)
    
        if check_unique and not df_copy.index.is_unique:
            duplicates = df_copy.index[df_copy.index.duplicated()].unique().tolist()
            raise ValueError(
                "Flattening MultiIndex index to the last level produced duplicate labels: "
                f"{duplicates}. Provide full MultiIndex labels upstream or rename to avoid collisions."
            )

    return df_copy

def get_dataframe_positions(
        df: pd.DataFrame, 
        labels: list[str], 
        axis: int = 1,
        *,
        allow_ambiguous: bool = False,
        preview: int = 50,
    ) -> list[int]:
    """

    Get interger positions of given labels in the last level of a Multiindex (or flat index) on
    a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing the data.
    labels : list[str]
        List of label names to locate in the index or columns. If a label is a tuple/list, its last
        element is used (MultiIndex-friendly).
    axis : int
        1 for columns, 0 for index.
    allow_ambiguous : bool
        if False, raise an error when the searched axis contains duplicates in the
        last level (to avoid silently returning the first match).
    preview : int
        Number of available label to show in error messages.
    """
    # Select the axis
    if axis not in (0, 1):
        raise ValueError("axis must be 0 (index) or 1 (columns).")
    
    obj = df.columns if axis == 1 else df.index
    axis_name = "columns" if axis == 1 else "index"

    # Extract last level
    if isinstance(obj, pd.MultiIndex):
        values = list(obj.get_level_values(-1))
    else:
        values = list(obj)

    # Ambiguity check (duplicates)
    if not allow_ambiguous:
        seen = set()
        duplicates = set()
        for v in values:
            if v in seen:
                duplicates.add(v)
            else:
                seen.add(v)
        if duplicates:
            duplicates_list = sorted(list(duplicates))[:preview]
            raise ValueError(
                f"Ambiguous {axis_name}: duplicates found in the last level labels (showing up to {preview}): "
                f"{duplicates_list}. Provide full MultiIndex labels upstream or ensure last-level labels are unique."
            )

    # fast lookup map
    pos_map = {v: i for i,v in enumerate(values)}

    # Map labels to last element
    mapped_labels = [
        lab[-1] if isinstance(lab, (tuple, list)) else labels
        for lab in labels
    ]

    positions = []
    for lab_val in mapped_labels:
        if lab_val in pos_map:
            positions.append(pos_map[lab_val])
        else:
            available_preview = values[:preview]
            raise KeyError(
                f"Label '{lab_val}' not found in {axis_name}. "
                f"First {preview} available: {available_preview} ..."
            )
    
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
    if filename is None:
        raise ValueError("filename cannot be None")
    clean = re.sub(r"[^\w\-]+","_",str(filename))
    clean = clean.strip("_")

    return clean or "file"

def filename_to_save(
        path: str | None, 
        filename: str | None, 
        default_filename: str, 
        extension: str,
        *, 
        create_dir: bool = True,
        sanitise: bool = True,
    ) -> str | None:
    """
    """
    if path is None:
        return None
    
    if extension is None:
        raise ValueError("An extension must be provided.")

    if filename is None:
        filename = default_filename
    
    if sanitise:
        filename = sanitize_filename(filename)

    if not filename.lower().endswith(extension):
        filename += extension
    
    if create_dir:
        os.makedirs(path,exist_ok=True)
    else:
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Directory does not exist: {path}")

    return os.path.join(path,filename)