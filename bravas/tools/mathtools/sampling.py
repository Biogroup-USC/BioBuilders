"""
"""
import numpy as np

__all__ = (
    "build_cartesian_grid",
)

def build_cartesian_grid(
        xbounds: tuple[float, float] = None, 
        ybounds: tuple[float, float] = None, 
        nx: int = 20, 
        ny: int = 20, 
        return_pairs: bool = True,
        return_idx: bool = True,
        order: str = "row"
    ):
    """

    Construct a cartesian grid (X, Y) and optionally an ordered
    list of (X, Y) pairs.

    The grid is created with `np.meshgrid(x, y)` using the default `indexing='xy'`,
    so `X` and `Y` have shape `(ny, nx)`. If `return_pairs=True`, the (x, y) points
    are flattened in either **row-major** order ("row") or **serpentine** order
    (alternating left-to-right and right-to-left rows), starting from the first y.

    Parameters
    ----------
    xbounds : tuple[float, float]
        Lower and upper bounds of the X axis (inclusive). If `xbounds[0] > xbounds[1]`
        they are swapped.
    ybounds : tuple[float, float]
        Lower and upper bounds of the Y axis (inclusive). If `ybounds[0] > ybounds[1]`
        they are swapped.
    nx : int, default = 20
        Number of samples along the X axis (must be >= 1).
    ny : int, default = 20
        Number of samples along the Y axis (must be >= 1).
    return_pairs : bool, default = True
        If True, also return the flattened list of (x, y) pairs in the specified order.
    order : {'row', 'serpentine'}, default = 'row'
        - 'row': row-major order, left-to-right for every row (y fixed, x sweeps ascending).
        - 'serpentine': alternate direction each row (even rows left→right, odd rows right←left).

    """
    # Validate nx and ny value
    if not isinstance(nx, int) or not isinstance(ny, int):
        raise TypeError("nx and ny must be integers")
    if nx < 1 or ny < 1:
        raise ValueError("nx and ny must be >= 1")
    
    if xbounds is None or ybounds is None:
        raise ValueError("xbounds and ybounds must be provided.")

    try:
        # Get xbounds separately
        xlb, xub = xbounds
        # Get ybounds separately
        ylb, yub = ybounds
    except Exception as e:
        raise ValueError("xbounds and ybounds must be length-2 iterables") from e

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
    order = str(order).lower()
    if order == "row":
        # File by file, from left to right
        idx_pairs = [(i,j) for j in range(ny) for i in range(nx)]
        pairs = [(x[i], y[j]) for (i,j) in idx_pairs]
    elif order == "serpentine":
        # Alternating files; inverting x direction
        idx_pairs = []
        pairs = []
        for j in range(ny):
            if (j % 2) == 0:
                idx_pairs.extend((i, j) for i in range(nx))
            else:
                idx_pairs.extend((i, j) for i in range(nx - 1, -1, -1))
        pairs = [(float(x[i]), float(y[j])) for (i,j) in idx_pairs]
    else:
        raise ValueError("Order must be either 'row' or 'serpentine'")
    
    if return_idx:
        return X, Y, pairs, idx_pairs
    else:
        return X, Y, pairs