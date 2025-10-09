"""
"""
import biosteam as bst
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from ..tools.diagramtools import simplify_labels, sanitize_filename
import os

__all__ = (
    "UncertaintyPlotter",
)

class UncertaintyPlotter:
    """
    """
    def __init__(self, uncertainty_df : pd.DataFrame = None, simplified_index : list = None):
        """
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
    
    def plot_correlation_matix(self, method = 'kendall', path: str = None, show_plot: bool = False, indicators: list[str] = None):
        """
        """
        # Compute the pairwise correlation using the method = method
        correlation = self.uncertainty_df.corr(method = method)

        # Subset matrix if only indicators should be shown
        if indicators:
            non_indicator_cols = [col for col in correlation.columns if col not in indicators]
            correlation = correlation.loc[indicators, non_indicator_cols]

        # Create the plot
        N_Vars = self.uncertainty_df.shape[1]
        if indicators:
            fig, ax = plt.subplots(figsize = (N_Vars * 0.55, len(indicators) * 0.90))
            plt.subplots_adjust(top = 0.90, bottom = 0.35, left = 0.20, right = 1.0)
        else:
            fig, ax = plt.subplots(figsize = (N_Vars * 0.55, N_Vars * 0.55))
            plt.subplots_adjust(top = 0.90, bottom = 0.25, left = 0.20, right = 1.0)

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
            file_path = os.path.join(path, '{}.png'.format(method))
            fig.savefig(file_path)

        plt.close(fig)

    def plot_distribution_and_stats(self, indicators: list, save_path: str = None, show_plot = False):
        """
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