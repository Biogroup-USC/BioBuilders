import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from ..tools.diagramtools import simplify_labels, keep_multiindex_last_level, get_dataframe_positions, sanitize_filename, filename_to_save

__all__ = (
    "StandRegCoeffs",
)

class StandRegCoeffs:
    """

    Class for performing Standardized Regression Coefficients (SRC) sensitivity analysis.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing BioSTEAM Monte Carlo simulation results.
    parameter_cols : list[str]
        List of column names for input parameters.
    indicator_cols : list[str]
        List of column names for output indicators.

    """

    def __init__(
            self, 
            df: pd.DataFrame, 
            parameter_cols: list[str], 
            indicator_cols: list[str], 
            simplified_labels: dict | list = None, 
            label_sep: str = "auto"
            ,*, 
            check_unique: bool = True
        ):
        """

        Initialize SRC analysis with data and column names.

        """
        # Get the last level if Multiindex
        df_flatten = keep_multiindex_last_level(df = df, check_unique = check_unique)

        # Compute positions based on original last-level labels
        parameter_positions = get_dataframe_positions(df = df_flatten, labels = parameter_cols, axis = 1, allow_ambiguous = False)
        indicator_positions = get_dataframe_positions(df = df_flatten, labels = indicator_cols, axis = 1, allow_ambiguous = False)

        if simplified_labels:
            df_simple = df_flatten.copy()
            try:
                df_simple.columns = simplify_labels(
                    full_labels = df_simple.columns.tolist(), 
                    keywords = simplified_labels,
                    sep = label_sep
                )
            except ValueError as e:
                raise ValueError(f"simplify_labels failed for StandRegCoeffs: {e}") from e
            self.df = df_simple
    
        else:    
            self.df = df_flatten
        
        # Store parameter and indicator column names (flattened)
        self.parameters = [self.df.columns[i] for i in parameter_positions]
        self.indicators = [self.df.columns[i] for i in indicator_positions]

    def calculate_src(self,*,tol = 1e-12) -> pd.DataFrame:
        """

        Calculates the Standardized Regression Coefficients (SRC) for the selected
        input parameters and output indicators.

        The method standardises each column (zero mean, unit variance; using ``ddof=0``)
        and then fits an ordinary least-square model for each indicator to obtain standardised
        regression coefficients.

        Parameters
        ----------
        tol : float
            Tolerance for detecting invalid (near-zero) standard deviations when standardising columns.
            Columns with ``std < tol`` raise a ``ValueError``.
        
        Returns
        -------
        pd.DataFrame
            DSRC values, rows correspond to input parameters and columns
            correspond to output metrics.

        """
        # Standarize all variables (mean = 0, std = 1)
        std = self.df.std(ddof=0)
        invalid_values = std[std < tol]
        if not invalid_values.empty:
            raise ValueError(f"Columns with zero std (cannot standardise): {invalid_values.index.tolist()}")
        
        df_std = (self.df - self.df.mean()) / std

        # Build design matrix X (n samples x p parameters)
        X = df_std[self.parameters].values

        results = {}
        for out in self.indicators:
            # Extract standardized output vector y
            y = df_std[out].values

            # Solve least-squares without explicitly inverting (X^T X)
            beta,*_ = np.linalg.lstsq(X, y,rcond=None)
            results[out] = beta
        
        # Return SRC DataFrame
        src_df = pd.DataFrame(results, index = self.parameters)
        
        return src_df
    
    def plot_src(self, src: pd.DataFrame, path : str = None, show_plot: bool = False) -> None:
        """

        Plot a separate bar chart of SRC for each output indicator.

        Parameters
        ----------
        src : pd.DataFrame
            DataFrame returned by calculate_src, with parameters as index
            and indicators as columns.
        path : str
            Path to the folder where plot images will be saved
        show_plot : bool
            True for displaying the plot. False for not.
            
        """
        # Ensure output directory exists
        if path:
            os.makedirs(path, exist_ok = True)

        for indicator in self.indicators:
            # Sort by absolute value descending
            coeffs = src[indicator].dropna()
            coeffs = coeffs.reindex(coeffs.abs().sort_values(ascending = True).index)
            
            # Plot
            N_var = len(coeffs)
            fig, ax = plt.subplots(figsize = (6, N_var * 0.5), constrained_layout = True)
            
            # Plot a bar chart for this indicator
            ax.barh(coeffs.index, coeffs.values, color = 'skyblue', edgecolor = 'k')
            ax.set_title('SRC Sensitivity Analysis: {}'.format(indicator), fontsize = 8)
            ax.set_xlabel("Standardized Regression Coefficients", fontsize = 7)
            ax.axvline(0, color = 'red', linewidth = 0.8)
            ax.tick_params(axis = 'y', labelsize = 6)
            ax.tick_params(axis = 'x', labelsize = 6)
            plt.xticks(rotation = 45, ha = 'right')
            if show_plot is True:
                plt.show()

            # Save the figure
            if path:
                file_path = filename_to_save(
                    path=path,
                    filename=f"src_{indicator}",
                    default_filename="src",
                    extension=".png"
                )
                if file_path:
                    fig.savefig(file_path,bbox_inches="tight",pad_inches=0.2)