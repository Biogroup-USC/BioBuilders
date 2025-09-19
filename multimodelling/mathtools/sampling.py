"""
"""
import numpy as np
from typing import Iterable, Sequence, Tuple, Callable, Optional
from scipy.interpolate import griddata

__all__ = (
    
)

def build_cartesian_grid(
        xbounds, 
        ybounds, 
        nx, 
        ny, 
        return_pairs, 
        order
    ):
    """
    """
    # Validate nx and ny value
    if not isinstance(nx, int) or not isinstance(ny, int):
        raise TypeError("nx and ny must be intergers")
    if nx < 1 or ny < 1:
        raise ValueError("nx and ny must be >= 1")
    
    # Get xbounds separately
    xlb, xub = xbounds

    # Get ybounds separately
    ylb, yub = ybounds

    # Ensure bounds are well defined, otherwise reorganise them
    if xlb > xub: xlb, xub = xub, xlb
    if ylb > yub: ylb, yub = yub, ylb

    # create 1D vectors
    x = np.linspace(xlb, xub, nx)
    y = np.linspace(ylb, yub, ny)

    # Create 2D grid
    X,Y = np.meshgrid(x, y)
        
    if not return_pairs:    
        return X,Y
    
    # Build pairs based on the order given
    if order == "row":
        # File by file, from left to right
        pairs = [(float(xx), float(yy)) for yy in y for xx in x]
    elif order == "serpentine":
        # Alternating files; inverting x direction
        pairs = []
        for j, yy in enumerate(y):
            xs = x if (j % 2 == 0) else x[::1]
            pairs.extend((float(xx), float(yy)) for xx in xs)
    else:
        raise ValueError("Order must be either 'row' or 'serpentine'")
    
    return X, Y, pairs

def build_disperse_grid():
    """
    """
    