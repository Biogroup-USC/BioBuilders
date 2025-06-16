"""
"""
import biosteam as bst
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from .diagramtools import simplify_labels
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
    
    def plot_correlation_matix(self, method = 'kendall', path: str = None):
        """
        """
        # Compute the pairwise correlation using the method = method
        Correlation = self.uncertainty_df.corr(method = method)

        # Create the plot
        N_Vars = self.uncertainty_df.shape[1]
        fig, ax = plt.subplots(figsize = (N_Vars * 0.55, N_Vars * 0.55))

        # Create a heat map
        sns.heatmap(
            Correlation, annot = True, cmap = 'coolwarm', fmt = ".2f", annot_kws = {"size": 6},
        )
        
        # Plot settings
        ax.set_title("Correlation Matrix ({})".format(method), fontsize = 8)
        ax.tick_params(axis = 'x',labelsize = 4, rotation = 55)
        ax.tick_params(axis = 'y',labelsize = 4, rotation = 0)
        plt.subplots_adjust(top = 0.95, bottom = 0.25, left = 0.20, right = 1.0)

        # Show the plot
        plt.show()

        # Save the figure
        if path:
            file_path = os.path.join(path, '{}.png'.format(method))
            fig.savefig(file_path)
            print("")

        plt.close(fig)

    def plot_distribution_and_stats(self, indicators: list, save_path: str = None):
        """
        """
        # Check if all indicators given are in the dataframe
        if not all(ind in self.uncertainty_df.columns for ind in indicators):
            Missing = [ind for ind in indicators if ind not in self.uncertainty_df.columns]
            raise ValueError("The next indicators are not in the uncertainty dataframe: {}".format(Missing))
        
        # Dict to store all the stats
        Stats = {}

        # Calculate the number os subplots
        n = len(indicators)
        ncols = 2
        nrows = (n + 1) // ncols

        fig, axes = plt.subplots(nrows = nrows, ncols = ncols, figsize = (6,5))
        axes = axes.flatten()

        # Get the stats of each indicator
        for i,ind in enumerate(indicators):
            Data = self.uncertainty_df[ind]
            
            # Create the KDE plot
            sns.kdeplot(data = Data, fill = True, ax = axes[i])
            axes[i].set_title("Distribution: {}".format(ind), fontsize = 8)
            axes[i].set_xlabel(ind, fontsize = 6)
            axes[i].set_ylabel("Density", fontsize = 6)
            axes[i].tick_params(axis='both', which='major', labelsize=6)
            axes[i].grid(True, linestyle='--', alpha=0.5)

            # calculate the stats
            Stats[ind] = {
                "mean": Data.mean(),
                "median": Data.median(),
                "std": Data.std(),
            }
        
        # Eliminate empty subplots
        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        # Adjust layout
        plt.tight_layout(pad = 1.20, h_pad = 0.6, w_pad = 0.8)

        # Save the figure
        if save_path:
            plt.savefig(save_path, dpi = 300)
        
        # Show
        plt.show()

        # Return the stats
        return pd.DataFrame(Stats).T