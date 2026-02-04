"""
"""
import matplotlib.pyplot as plt
import pandas as pd
from ..tools.diagramtools import simplify_labels, sanitize_filename
import os

__all__ = (
    "plot_spearman_1d",
)

def plot_spearman_1d(
        spearman_dataframe: pd.DataFrame = None, 
        indicator: list | str = None,
        file_path: str = None,
        show_plot: bool = False,
        simplified_index: dict = None, 
        height_per_var: float = 0.5, 
        fig_width: float = 6,
    ):
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
    file_path : str
        Path of the folder where the results are stored.
    show_plot : bool
        True for displaying each plot, False for not.
    simplified_index : dict
        Dictionary with the structure {simplified_label : units_label}.
    height_per_var : float
        Height (in inches) per variable. Default is 0.5.
    fig_width : float
        Width (in inches) of the figure. Default is 6.

    """
    # Copy to avoid modifying caller's DataFrame
    Df = spearman_dataframe.copy()
    
    # Flatten MultiIndex columns to their last level if needed
    if isinstance(Df.columns, pd.MultiIndex):
        Df.columns = Df.columns.get_level_values(-1)
    
    # Flatten MultiIndex index
    if isinstance(Df.index, pd.MultiIndex):
        Df.index = Df.index.get_level_values(-1)
    
    # Change the index for the simplified index
    Df.index = simplify_labels(Df.index, keywords = simplified_index)
    
    # Helper function to plot a single indicator
    def _plot_single(ind, path):

        # Check if the indicator is in the dataframe columns
        if ind not in Df.columns:
            raise KeyError("Indicator '{}' not found in the DataFrame.".format(indicator))
        Coeffs = Df[ind].dropna()

        # Sort by absolute value descending
        Coeffs = Coeffs.reindex(Coeffs.abs().sort_values(ascending=False).index)

        # Plot settings
        N_Vars = Df[ind].shape[0]
        fig, ax = plt.subplots(figsize=(fig_width,N_Vars * height_per_var))
        ax.barh(Coeffs.index, Coeffs.values, color='skyblue', edgecolor='k')
        ax.invert_yaxis()
        ax.axvline(0, color='red', linewidth=0.8)
        ax.set_xlabel("Spearman Correlation Coefficient", fontsize = 7)
        ax.set_ylabel("Parameter", fontsize = 7)
        ax.set_title(f"Spearman Sensitivity for '{ind}'", fontsize = 8)
        ax.tick_params(axis = 'y', labelsize = 6)
        ax.tick_params(axis = 'x', labelsize = 6)
        plt.subplots_adjust(bottom = 0.10, top = 0.95, left = 0.25, right = 0.95)
        if show_plot is True:
            plt.show()

        # Save the figure
        if path is not None:
            safe_ind = sanitize_filename(ind)
            file_path = os.path.join(path, 'spearman_{}.png'.format(safe_ind))
            fig.savefig(file_path)
            plt.close(fig)

    # Handle list of indicators
    if isinstance(indicator, list):
        for ind in indicator:
            _plot_single(ind, path = file_path)
    else:
        _plot_single(indicator)