"""
"""
import biosteam as bst
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from .diagramtools import simplify_labels

__all__ = (
    "Uncertainty_Plotter",
)

class Uncertainty_Plotter:
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
    
    def plot_correlation_matix(self, method = 'kendall'):
        """
        """
        # Compute the pairwise correlation using the method = method
        Correlation = self.uncertainty_df.corr(method = method)

        # Create the plot
        plt.figure(figsize = (8, 6))

        # Create a heat map
        sns.heatmap(Correlation, annot = True, cmap = 'coolwarm', fmt = ".2f")
        
        # Plot settings
        plt.title("Correlation Matrix ({})".format(method))
        plt.tight_layout()
        plt.xticks(fontsize = 4, rotation = 45)
        plt.yticks(fontsize = 4, rotation = 0)

        # Show the plot
        plt.show()

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

        fig, axes = plt.subplots(nrows = nrows, ncols = ncols, figsize = (10, 4 * nrows))
        axes = axes.flatten()

        # Get the stats of each indicator
        for i,ind in enumerate(indicators):
            Data = self.uncertainty_df[ind]
            
            # Create the KDE plot
            sns.kdeplot(data = Data, fill = True, ax = axes[i])
            axes[i].set_title("Distribution: {}".format(ind), fontsize = 8)
            axes[i].set_xlabel(ind)
            axes[i].set_ylabel("Density")
            axes[i].grid(True)

            # calculate the stats
            Stats[ind] = {
                "mean": Data.mean(),
                "median": Data.median(),
                "std": Data.std(),
            }
        
        # Eliminate empty subplots
        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])
        
        plt.tight_layout()

        # Save the figure
        if save_path:
            plt.savefig(save_path, dpi = 300)
        
        # Show
        plt.show()

        # Return the stats
        return pd.DataFrame(Stats).T