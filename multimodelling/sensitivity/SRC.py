import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

__all__ = (
    "SRC",
)

class SRC:
    """

    Class for performing Standardized Regression Coefficients (SRC) sensitivity analysis.

    """

    def __init__(self, df: pd.DataFrame, parameter_cols: list[str], indicators_cols: list[str]):
        """

        Initialize SRC analysis with data and column names.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing BioSTEAM Monte Carlo simulation results.
        parameter_cols : list[str]
            List of column names for input parameters.
        indicator_cols : list[str]
            List of column names for output indicators.
        
        """
        self.df = df
        self.parameters = parameter_cols
        self.indicators = indicators_cols

    def calculate_src(self) -> pd.DataFrame:
        """

        Calculates the Standardized Regression Coefficients (SRC) for
        a set of input parameters and output indicators.

        Parameters
        ----------
        df : pd.DataFrame
            Dataframe containing BioSTEAM results of the Monte Carlo simulation.
        parameter_cols : list[str]
            List of column names for input parameters.
        indicator_cols : list[str]
            List of column names for output metrics.
        
        Returns
        -------
        pd.DataFrame
            DataFrame of SRC values: rows correspond to input parameters, columns
            correspond to output metrics.

        """
        # Standarize all variables (mean = 0, std = 1)
        df_std = (self.df - self.df.mean()) / self.df.std(ddof = 0)

        # Build design matrix X (n samples x p parameters)
        X = df_std[self.parameters].values

        # Compute inverse of (X^T X)
        XTX = X.T @ X               
        XTX_inv = np.linalg.inv(XTX)

        results = {}
        for out in self.indicators:
            # Extract standardized output vector y
            y = df_std[out].values

            # Compute X^T y
            XTy = X.T @ y

            # Compute B = (X^T X)^{-1} X^T y
            beta = XTX_inv @ XTy
            results[out] = beta
        
        # Return SRC DataFrame
        src_df = pd.DataFrame(results, index = self.parameters)
        return src_df
    
    def plot_src(self, src: pd.DataFrame, path : str) -> None:
        """

        Plot a separate bar chart of SRC for each output indicator.

        Parameters
        ----------
        src : pd.DataFrame
            DataFrame returned by calculate_src, with parameters as index
            and indicators as columns.
        path : str
            Path to the folder where plot images will be saved
            
        """
        # Ensure output directory exists
        os.makedirs(path, exist_ok = True)

        for indicator in self.indicators:
            fig, ax = plt.subplots()
            # Plot a bar chart for this indicator
            src[indicator].plot(kind = 'bar')
            ax.set_ylabel('Standardized Regression Coefficients')
            ax.set_title('SRC Sensitivity Analysis: {}'.format(indicator))
            plt.xticks(rotation = 45, ha = 'right')
            plt.tight_layout()
            plt.show()

            # Save the figure
            file_path = os.path.join(path, 'src_{}.png'.format(indicator))
            fig.savefig(file_path)
            plt.close(fig)
        
        print("Plots saved to {}".format(path))