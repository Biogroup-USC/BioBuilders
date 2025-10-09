"""
"""

import pandas as pd
import re

__all__ = (
    "simplify_labels",
    "keep_multiindex_last_level",
    "get_dataframe_positions",
    "sanitize_filename",
)

def simplify_labels(full_labels: list = None, keywords: list | dict = None):
    """
    """
    # if keywords are not provided, give back the original labels
    if keywords is None:
        return list(full_labels)
    
    Simplified_Labels = []
    for label in full_labels:
        # Avoid error with upper/lower letters
        Lower_Label = label.lower()

        # Add the new label and its units if keywords is a dict
        if isinstance(keywords, dict):
            Match = next(
                ("{} {}".format(key, units) for key, units in keywords.items() if key.lower() in Lower_Label), label
            )

        # Add only the new label if keywords is a list
        else:
            Match = next(
                (key for key in keywords if key.lower() in Lower_Label), label
            )

        # Append the label
        Simplified_Labels.append(Match)

    # Return the list of simplified labels
    return Simplified_Labels

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
    if isinstance(df_copy, pd.MultiIndex):
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