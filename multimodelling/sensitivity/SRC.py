import pandas as pd
import numpy as np

__all__ = (
    "calculate_src",
)

def calculate_src(df: pd.DataFrame, input_cols, output_cols):
    """
    """
    # Standarize all the variables
    df_std = (df - df.mean() / df.std(ddof = 0))

    # Build X
    X = df_std[input_cols].values

    # Calculate (X^T X)^{-1}
    XTX = X.T @ X               
    XTX_inv = np.linalg.inv(XTX)

    results = {}
    for out in output_cols:
        # Vector y
        y = df_std[out].values

        # Calculate X^T y
        XTy = X.T @ y

        # Calculate B = (X^T X)^{-1} X^T y
        beta = XTX_inv @ XTy
        results[out] = beta
    
    # Return the Dataframe with SRC
    src_df = pd.DataFrame(results, index = input_cols, columns = [])