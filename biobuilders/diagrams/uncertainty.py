"""
"""
import biosteam as bst
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from ..tools.diagramtools import simplify_labels, sanitize_filename, filename_to_save
import os

__all__ = (
    "UncertaintyPlotter",
)

class UncertaintyPlotter:
    """

    Class for analysing and visualising uncertainty in a set of variables
    stored in a ``pandas.DataFrame``.

    During the initialisation, the class applies a label simplification procedure via ``simplify_labels``
    function and removes the ```'Element'``` level from a column ``MultiIndex`` if present.

    Parameters
    ----------
    uncertainty_df : pandas.DataFrame
        DataFrame containing uncertainty simulations (Monte Carlo method). Each column represents a variable and
        each row a simulation.
    simplified_index : list[str]
        List of simplified labels used to rename the column.

    """
    def __init__(self, uncertainty_df : pd.DataFrame = None, simplified_index : list = None):
        """

        Initialise an ``UncertaintyPlotter`` class with an uncertainty DataFrame and a set of simplified
        column labels.

        """
        # Check the parameters
        if uncertainty_df is None: raise ValueError("A pandas DataFrame must be provided")
        if simplified_index is None: raise ValueError("The simplified index must be provided")
        
        # Copy the DataFrame
        Df_Copy = uncertainty_df.copy()

        # Delete the first level of the multi index
        if isinstance(Df_Copy.columns, pd.MultiIndex):
            if 'Element' in Df_Copy.columns.names:
                Df_Copy.columns = Df_Copy.columns.droplevel('Element')

        # Change the index for the simplified index
        Df_Copy.columns = simplify_labels(Df_Copy.columns, simplified_index)

        self.uncertainty_df = Df_Copy
        self.index = simplified_index
        self._stats = None

    def plot_correlation_matrix(self, method = 'kendall', path: str = None, filename: str | None = None, show_plot: bool = False, indicators: list[str] = None):
        """

        Compute and visualise a correlation matrix of the variables contained in the uncertainty DataFrame.

        Pairwise correlations are computed using the method specified (default: ```'kendall'```). The resulting matrix
        is displayed as a heatmap using ``seaborn.heatmap``.

        If a list of indicators is provided, the correlation matrix is subset so that only the specified indicators appear as rows,
        while the remaining variables appear as columns.

        Parameters
        ----------
        method : {'pearson', 'spearman', 'kendall'}, default 'kendall'
            Correlation method passed directly to ``DataFrame.corr``.
        path : str
            Directory path where the figure will be saved.
        filename : str
            name of the figure to save it as `filename.png`.
        show_plot : bool, default=False
            If ``True``, the plot is displayed using ``plt.show()``.
        indicators : list[str]
            Subset of column names considered as key indicators. when provided, the resulting matrix shows correlations between these
            indicators (rows) and all other non-indicator variables (columns).

        """
        # Compute the pairwise correlation using the method = method
        correlation = self.uncertainty_df.corr(method = method)

        # Subset matrix if only indicators should be shown
        if indicators:
            indicators_ok = [c for c in indicators if c in correlation.index]
            if not indicators_ok:
                raise ValueError("None of the provided indicators are present in the Dataframe columns")
            non_indicator_cols = [col for col in correlation.columns if col not in indicators_ok]
            correlation = correlation.loc[indicators_ok, non_indicator_cols]

        # n_cols and n_rows
        n_cols = correlation.shape[1]
        n_rows = correlation.shape[0]

        # Create fig, ax
        fig, ax = plt.subplots(figsize = (max(10, n_cols * 0.55), max(5, n_rows * 0.55)), constrained_layout = True)

        # Create a heat map
        sns.heatmap(
            correlation, annot = True, cmap = 'coolwarm', fmt = ".2f", annot_kws = {"size": 6},
        )
        
        # Plot settings
        ax.set_title("Correlation Matrix ({})".format(method), fontsize = 8)
        ax.tick_params(axis = 'x',labelsize = 4, rotation = 55)
        ax.tick_params(axis = 'y',labelsize = 4, rotation = 0)

        # Show the plot
        if show_plot:
            plt.show()

        # Save the figure
        if path:
            # Default filename
            default_filename = "{}_correlation".format(method)            

            file_path = filename_to_save(
                path, filename, default_filename, ".png"
            )
            fig.savefig(file_path, dpi = 300, bbox_inches = "tight")

        plt.close(fig)

    def plot_distribution_and_stats(self, indicators: list, save_path: str = None, show_plot = False):
        """

        Plot the distribution of selected indicators and compute descriptive statistics for each of them.

        Parameters
        ----------
        indicators : list[str]
            List of column names to analyse. Each element must exist in ``uncertainty_df``.
        save_path : str
            Directory where figures will be saved as ``.png`` files. Filenames follow the pattern 
            ```'distribution_<indicator>.png'``. If ``None``, figures are not written in the disk.
        show_plot : bool, default=False
            If ``True``, each figure is shown using ``plt.show()``.
            if ``False``, figures are closed after saving.

        """
        # Check if all indicators given are in the dataframe
        if not all(ind in self.uncertainty_df.columns for ind in indicators):
            Missing = [ind for ind in indicators if ind not in self.uncertainty_df.columns]
            raise ValueError("The next indicators are not in the uncertainty dataframe: {}".format(Missing))
        
        # Dict to store all the stats
        Stats = {}

        # Get the stats of each indicator and plot the distribution
        for ind in indicators:
            Data = self.uncertainty_df[ind]
            # Create the subplot
            fig, ax = plt.subplots(figsize = (6,5)) 

            # Create the KDE plot
            sns.kdeplot(data = Data, fill = True, ax = ax)
            ax.set_title("Distribution: {}".format(ind), fontsize = 8)
            ax.set_xlabel(ind, fontsize = 6)
            ax.set_ylabel("Density", fontsize = 6)
            ax.tick_params(axis='both', which='major', labelsize=6)
            ax.grid(True, linestyle='--', alpha=0.5)

            # calculate the stats
            mean_val = Data.mean()
            median_val = Data.median()
            std_val = Data.std()
            Stats[ind] = {
                "mean": mean_val,
                "median": median_val,
                "std": std_val,
            }
            
            # Statistic lines
            ax.axvline(mean_val, color = 'red', linestyle = '--', linewidth = 1, label = f"Mean = {mean_val:.2f}")
            ax.axvline(median_val, color = 'green', linestyle = ':', linewidth = 1, label = f"Median = {median_val:.2f}")
            ax.axvline(mean_val + std_val, color = 'blue', linestyle = '--', linewidth = 0.8, label = f"+1$\sigma$ = {mean_val + std_val:.2f}")
            ax.axvline(mean_val - std_val, color = 'blue', linestyle = '--', linewidth = 0.8, label = f"-1$\sigma$ = {mean_val - std_val:.2f}")

            # Legend
            ax.legend(fontsize = 6, loc = 'upper right')

            # Adjust subplots
            plt.subplots_adjust(bottom = 0.10, top = 0.95, left = 0.10, right = 0.95)

            # Show
            if show_plot is True:
                plt.show()

            # Save the figure
            if save_path:
                safe_ind = sanitize_filename(ind)
                file_path = os.path.join(save_path,'distribution_{}.png'.format(safe_ind))
                fig.savefig(file_path)
                plt.close(fig)

        # Return the stats
        return pd.DataFrame(Stats).T