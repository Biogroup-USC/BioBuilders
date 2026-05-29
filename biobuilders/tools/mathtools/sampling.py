"""
Sampling tools
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
    Construct a Cartesian grid (X, Y) and optionally ordered (x, y) pairs.

    The grid is created with ``np.meshgrid(x, y, indexing="xy")``, so
    ``X`` and ``Y`` have shape ``(ny, nx)``. If ``return_pairs=True``,
    the points are flattened in either row-major order or serpentine order.

    Parameters
    ----------
    xbounds : tuple[float, float]
        Lower and upper bounds of the x-axis. If ``xbounds[0] > xbounds[1]``,
        they are swapped.
    ybounds : tuple[float, float]
        Lower and upper bounds of the y-axis. If ``ybounds[0] > ybounds[1]``,
        they are swapped.
    nx : int, default=20
        Number of samples along the x-axis. Must be >= 1.
    ny : int, default=20
        Number of samples along the y-axis. Must be >= 1.
    return_pairs : bool, default=True
        If True, also return the flattened array of ``(x, y)`` pairs.
    return_idx : bool, default=True
        If True and ``return_pairs=True``, also return the corresponding
        ``(i, j)`` index pairs.
    order : {'row', 'serpentine'}, default='row'
        Order used to flatten the grid.

        * ``'row'``: row-major order, left-to-right for every row.
        * ``'serpentine'``: alternate direction on each row.

    Returns
    -------
    X, Y : np.ndarray
        Coordinate matrices with shape ``(ny, nx)``.

    pairs : np.ndarray, optional
        Flattened ``(x, y)`` coordinate pairs with shape ``(nx * ny, 2)``.

    idx_pairs : np.ndarray, optional
        Flattened ``(i, j)`` index pairs with shape ``(nx * ny, 2)``.
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
        raise ValueError("xbounds and ybounds must be length-2 numeric iterables") from e

    # Ensure bounds are well defined, otherwise reorganise them
    if xlb > xub: xlb, xub = xub, xlb
    if ylb > yub: ylb, yub = yub, ylb

    # create 1D vectors
    x = np.linspace(xlb, xub, nx)
    y = np.linspace(ylb, yub, ny)

    # Create 2D grid
    X,Y = np.meshgrid(x, y, indexing="xy")
        
    if not return_pairs:    
        return X,Y
    
    # Build pairs based on the order given
    order = str(order).lower()

    if order == "row":
        # Row by row, from left to right
        ii = np.tile(np.arange(nx), ny)
        jj = np.repeat(np.arange(ny), nx)
    elif order == "serpentine":
        # Alternating rows; reversing x direction in odd rows
        ii_matrix = np.tile(np.arange(nx), (ny,1))
        ii_matrix[1::2] = ii_matrix[1::2, ::-1]

        jj_matrix = np.repeat(np.arange(ny)[:, None], nx, axis=1)

        ii = ii_matrix.ravel()
        jj = jj_matrix.ravel()
    else:
        raise ValueError("Order must be either 'row' or 'serpentine'")

    pairs = np.column_stack((x[ii], y[jj]))

    if return_idx:
        idx_pairs = np.column_stack((ii, jj))
        return X, Y, pairs, idx_pairs
    else:
        return X, Y, pairs