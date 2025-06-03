"""
"""
import matplotlib.pyplot as plt
import pandas as pd

__all__ = (
    "plot_spearman_1d",
)

def plot_spearman_1d(spearman_dataframe: pd.DataFrame = None, indicator: list | str = None, figsize_scale: tuple = (0.75, 0.5)):
    """
    Plot Spearman correlation coefficients as horizontal bar charts.

    Parameters
    ----------
    spearman_dataframe : pd.DataFrame
        DataFrame of Spearman correlation results. Rows are parameters,
        columns are indicators.
    indicator : str or list of str
        Name(s) of the indicator(s) (column) to plot. If a list is provided,
        a separate plot is generated for each indicator.
    figsize_scale : float
        scaling factor for figure size. Default is 0.5.

    """
    # Copy to avoid modifying caller's DataFrame
    Df = spearman_dataframe.copy()
    
    # Flatten MultiIndex columns to their last level if needed
    if isinstance(Df.columns, pd.MultiIndex):
        Df.columns = Df.columns.get_level_values(-1)
    
    # Flatten MultiIndex index
    if isinstance(Df.index, pd.MultiIndex):
        Df.index = Df.index.get_level_values(-1)
    
    # Helper function to plot a single indicator
    def _plot_single(ind):

        # Check if the indicator is in the dataframe columns
        if ind not in Df.columns:
            raise KeyError("Indicator '{}' not found in the DataFrame.".format(indicator))
        Coeffs = Df[ind].dropna()

        # Sort by absolute value descending
        Coeffs = Coeffs.reindex(Coeffs.abs().sort_values(ascending=False).index)

        # Plot settings
        N_Vars = Df[ind].shape[0]
        Fig, Ax = plt.subplots(figsize=(N_Vars * figsize_scale[0], N_Vars * figsize_scale[1]))
        Ax.barh(Coeffs.index, Coeffs.values, color='skyblue', edgecolor='k')
        Ax.invert_yaxis()
        Ax.axvline(0, color='red', linewidth=0.8)
        Ax.set_xlabel("Spearman Correlation Coefficient")
        Ax.set_ylabel("Parameter")
        Ax.set_title(f"Spearman Sensitivity for '{ind}'")
        plt.tight_layout()
        plt.show()

    # Handle list of indicators
    if isinstance(indicator, list):
        for ind in indicator:
            _plot_single(ind)
    else:
        _plot_single(indicator)