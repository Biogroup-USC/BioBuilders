"""
"""
import biosteam as bst
import numpy as np
import pandas as pd
from dataclasses import dataclass
from ..tools.mathtools.sampling import build_cartesian_grid
from typing import Callable
import matplotlib.pyplot as plt
import time
from tqdm import tqdm

__all__ = (
    "ContourStudy",
)

@dataclass
class CSParameter:
    name: str
    setter: Callable[[float],None]
    element: object = None
    units: str = None
    baseline: float = None
    bounds: tuple[float, float] = None
    n: int = None
    levels: int | np.ndarray = None
    coupled: bool = False
    description: str = None

@dataclass
class CSIndicator:
    name: str
    getter: Callable[[],None]
    units: str = None
    element: object  = None

class ContourStudy:
    """

    Construct and evaluate 2-parameter contour maps over BioSTEAM process
    simulation.

    This class provides the infrastructure required to perform systematic
    parametric evaluations on a `bst.TEA` object, with the aim of visualizing
    how economic or process indicators are influenced in a two-dimensional design
    space. Parameters and indicators are registered through decorators, following
    BioSTEAM conventions. This enables a clean separation between model definition
    and the numerical exploration of the design space.

    Parameters
    ----------
    TEA : bst.TEA
        A BioSTEAM TEA object associated with a system capable of being simulated. The
        TEA must expose a ``system`` attribute and the system must provide ``simulate()``
        method. The economic or process outputs (indicators) are assumed to be consistent
        with the state of this system.

    """
    def __init__(self,
                 TEA: bst.TEA = None,
                 ):
        # Check if the object provided has a method called simulate
        if TEA is None or not hasattr(TEA, "system"):
            raise ValueError("The TEA object provided must include a system to simulate")
        if not hasattr(TEA.system, "simulate"):
            raise ValueError("The system has not .simulate()")

        # Parameters
        self.TEA = TEA
        self.system = TEA.system

        # Properties
        self._parameters = []
        self._indicators = [] 

    @property
    def parameters(self):
        """

        List of registered model parameters.

        """
        return self._parameters

    @property
    def indicators(self):
        """

        List of registered model indicators.

        """
        return self._indicators

    # Define parameters using BioSTEAM conventions
    def parameter(self,*, name = None, element = None, units = None, baseline = None,
                  bounds = None, n = None, levels = None, coupled = False, description = None):
        """

        Register a model parameter for contour mapping and parametric studies.

        This method is a decorator that converts a setter function into a `CSParameter` object.
        A parameter defines how a model variable is perturbed during this parametric study.

        Parameters
        ----------
        name : str, optional
            Name of the parameter. Defaults to the setter function name.
        element : object, optional
            Optional reference to the model element that the parameter modifies
            (e.g., a BioSTEAM 'Unit', 'Stream' or a 'Specification'). Used only
            for annotation purposes.
        units : str, optional
            Physical units of the parameter (e.g., `"kg/h"`). Used for plotting and
            reporting.
        baseline : float
            Baseline value assigned to the parameter which represents its current value.
        bounds : tuple[float, float]
            Minimum and maximum values for uniform sampling. Mutually exclusive with `levels`.
            Required when generating grids for contour maps unless discretization is given explicitly
            through `levels`.
        n : int
            Number of evenly spaced samples between ``bounds`` when creating a grid. If omitted, the grid
            constructor must apply its own discretization.
        levels : array_like of float
            Explicit values at which the parameter is evaluated. Cannot be combined with ``bounds``. Use this
            when user-defined sampling is required.
        coupled : bool, default=False
            Flag for parameters that conceptually depend on other parameters or are part of a coupled design (not           #TODO
            implemented yet).
        description : str, optional                                                                                         #TODO
            Human-readable description of the parameter, useful for plots, reports and documentation (not implemented
            yet)
            
        """
        def decorator(setter_fn: Callable[[float], None]):
            p = CSParameter(
                name=name or setter_fn.__name__,
                setter=setter_fn, element=element, units=units, baseline=baseline,
                bounds=bounds,n=n, levels=levels, coupled=coupled,description=description 
            )
            # Validation to avoid mixing levels and n
            if p.levels is not None and p.bounds is not None:
                raise ValueError("Use bounds or levels, not both")
            self.parameters.append(p)
            return setter_fn
        return decorator
    
    # Define indicator using BioSTEAM conventions
    def indicator(self,*, name = None, units = None, element = None):
        """
        
        Register an indicator (scalar output metric) evaluated after each run.
        This method is a decorator that converts a setter function into a `CSIndicator` object.
        Indicators are evaluated after every succesfull simulation during a contour study and
        their values are stored on a 2D grid for visualisation.
        Parameters
        ----------
        name : str, optional
            Name of the indicator. Defaults to the name of the getter function.
        units : str, optional
            Physical units of the indicator.
        element: object, optional
            Optional reference to the model element from which the indicator is derived.
        
        """
        def decorator(getter_fn: Callable[[],float]):
            ind = CSIndicator(
                name=name or getter_fn.__name__,
                getter=getter_fn, units=units, element=element
            )
            self._indicators.append(ind)
            return getter_fn
        return decorator
    
    def build_grid(self, param_x: str, param_y: str, nx: int, ny: int, order: str = "row"):
        """

        Build a Cartesian grid for two registered parameters.

        This method locates the two parameters by name, reads their bounds and calls
        `build_cartesian_grid` function to generate a regular 2D grid of (x, y) values
        which will be used as input in `run_on_grid` method.

        Parameters
        ----------
        param_x : str
            Name of the parameter to be placed on the x-axis.
        param_y : str
            Name of the parameter to be placed on the y-axis.
        nx : int
            Number of grid points along the x-axis.
        ny : int
            Number of grid points along the y-axis.
        order : {"row", "column"}, default="row"
            Returned coordinate pairs order which will be directly passed to `build_cartesian_grid`.
            This affects the order in which simulations are performed but not the shape of ``X`` and
            ``Y``.

        """
        px = next((p for p in self.parameters if p.name == param_x), None)
        py = next((p for p in self.parameters if p.name == param_y), None)
        if px is None or py is None:
            missing_p = [n for n,p in [(param_x, px),(param_y, py)] if p is None]
            raise ValueError("Parameters not found: {}".format(missing_p))
        
        X,Y,pairs = build_cartesian_grid(xbounds=px.bounds, ybounds=py.bounds, nx=nx, ny=ny,return_pairs=True,order=order)
        return X, Y, pairs, px, py
    
    @staticmethod
    def _ix(v, arr):
        """

        Return the index of the grid value closest to a given scalar.

        The search first attempts to match values using `numpy.isclose` with a tight tolerance; if no
        element is considered close, the index of the nearest value (in absolute difference) is returned.

        Parameters
        ----------
        V : float
            Target value to locate in the array.
        arr : array_like
            One-dimensional array of grid coordinates.

        """
        idx = np.where(np.isclose(arr, v, rtol=1e-10, atol=1e-12))[0]
        return int(idx[0]) if idx.size else int(np.argmin(np.abs(arr-v)))

    def run_on_grid(
            self, X, Y, pairs, px, py,
            indicators = None,
            x_display_fn = None, 
            y_display_fn = None):
        """

        Evaluate the BioSTEAM system over a 2D grid of parameter values.

        For each (x, y) pair in ``pairs``, this method assigns the corresponding
        parameter values through ``px.setter`` and ``py.setter``, calls ``self.system.simulate()``
        and records the values of the selected indicators on a 2D array. Simulation failures are logged
        but do not interrupt the execution.

        Parameters
        ----------
        X, Y : ndarray
            2D arrays representing the x- and y- coordinates of the grid, returned by `CountourStudy.build_grid`.
        pairs : iterable of tuple[float, float]
            Iterable of (x, y) values indicating the parameter values for each simulation.
        px, py : CSParameter
            Parameter objects corresponding to the x and y axes, returned by `ContourStudy.build_grid`.
        indicators : str or sequence of str
            Names of the indicators to evaluate, if `None`, all registered indicators are used. Raises an error
            if any requested indicator is not found.
        x_display_fn, y_display_fn : callable, optional
            Optional functions ``f(vx, vy, self) -> float`` used to transform the x and/or y coordinates stored in
            the plotting grids. This is useful when the design variable is defined in one space but plots should be
            shown in another (e.g., logarithmic scaling,...)

        """
        # 1D axis of the grid
        x_vals = X[0,:]
        y_vals = Y[:,0]
        ny, nx = Y.shape

        # Create one z per indicator
        if indicators is None:
            selected_inds = list(self.indicators)
        else:
            if isinstance(indicators, str):
                requested = {indicators}
            else:
                requested = set(indicators)
            
            name_to_ind = {ind.name: ind for ind in self.indicators}
            missing = [name for name in requested if name not in name_to_ind]
            if missing:
                raise ValueError("Indicators not found: {}".format(missing))
            selected_inds = [name_to_ind[name] for name in requested]
        
        # initialise zs array (ny, nx) for each indicator selected
        zs = {ind.name: np.full((ny, nx), np.nan, dtype = float) for ind in selected_inds}
        
        # X_plot and Y_plot
        X_plot = X.copy()
        Y_plot = Y.copy()

        # time 0
        t0 = time.perf_counter()
        
        # Progress bar
        try:
            total = len(pairs)
        except TypeError:
            total = ny*nx 
        bar = tqdm(pairs, total=total, desc="Contour mapping", unit="sim", smoothing=0.0, miniters=1, mininterval=0.0,dynamic_ncols=True)

        # Simulate each pair
        failures = []
        for vx, vy in pairs:
            # Simulation time 0
            s0 = time.perf_counter()

            # Get the cordinates of each point
            i = self._ix(vx, x_vals)
            j = self._ix(vy, y_vals)
            
            try:
                # Change the parameters
                px.setter(float(vx))
                py.setter(float(vy))
                try:
                    # Simulate the system
                    self.system.simulate()
                except Exception as e:
                    failures.append(((vx, vy), repr(e)))
                    continue
                
                # Read and save only the requested indicators
                for ind in selected_inds:
                    zs[ind.name][j, i] = float(ind.getter())

                if x_display_fn is not None:
                    X_plot[j, i] = float(x_display_fn(vx, vy, self))
                if y_display_fn is not None:
                    Y_plot[j, i] = float(y_display_fn(vx, vy, self))
                        
            except Exception:
                # Keep NaN and continue
                pass
            
            finally:
                # Update bar progress
                iter_dt = time.perf_counter() - s0
                bar.set_postfix_str(f"t/it={iter_dt:.2f}s | fails = {len(failures)}")
                bar.update(1)
                bar.refresh()
        
        bar.close()
        print("")
        print(f"Finished at {time.perf_counter()-t0:.1f}s | failures = {len(failures)}")
        return zs, failures, X_plot, Y_plot
    
    def _get_param(self, name_or_param):
        """

        Resolve a parameter from its name or return the object directly.

        Parameters
        ----------
        name_or_param : str or CSParameter
            Either the name of a registered parameter of an existing
            `CSParameter` instance.

        """
        if isinstance(name_or_param, CSParameter):
            return name_or_param
        if isinstance(name_or_param, str):
            for p in self.parameters:
                if p.name == name_or_param:
                    return p
            available = [p.name for p in self.parameters]
            raise ValueError("Parameter '{}' not found. Availables: {}".format(name_or_param, available))
        raise TypeError("name_or_param must be a CSParameter or str (name of the parameter)")

    def compute_baseline(self, px: str, py: str, indicators = None, x_display_fn = None , y_display_fn = None):
        """

        Evaluate indicator at the baseline point of two parameters.

        This method sets both parameters to their baseline values, runs ``self.system.simulate()``
        and returns the resulting indicator values along with the (x, y) coordinates used for plotting.

        Parameters
        ----------
        px, py : str or CSParameter
            Names or objects of the parameters defining the x and y axis. Both must have a ``baseline`` defined
            value.
        indicators : str or sequence of str, optional
            Names of the indicators to evaluate. If ``None``, all registered indicators are used. Raises an error
            if any requested indicator is not found.
        x_display_fn, y_display_fn : callable, optional
            Optional transformation functions applied to the baseline coordinates before returning them, consistent
            with those used in ``ContourStudy.run_on_grid``.

        """
        px = self._get_param(px)
        py = self._get_param(py)

        if px.baseline is None or py.baseline is None:
            raise ValueError("px.baseline and py.baseline must be defined to compute baseline case")
        
        if indicators is None:
            selected_inds = list(self.indicators)
        else:
            name_to_inds = {ind.name: ind for ind in self.indicators}
            if isinstance(indicators, str):
                indicators = [indicators]
                missing = [name for name in indicators if name not in name_to_inds]
                if missing:
                    raise ValueError("Indicators not found: {}. Availables: {}".format(missing,list(name_to_inds)))
            selected_inds = [name_to_inds[name] for name in indicators]
        
        px.setter(float(px.baseline))
        py.setter(float(py.baseline))
        self.system.simulate()

        x_plot = px.baseline
        y_plot = py.baseline
        if x_display_fn is not None:
            x_plot = x_display_fn(px.baseline, py.baseline, self)
        if y_display_fn is not None:
            y_plot = y_display_fn(px.baseline, py.baseline, self)

        values = {ind.name: float(ind.getter()) for ind in selected_inds}
        return{"point": (float(x_plot), float(y_plot)), "values": values}

    def plot_contourf(self,
                      X,
                      Y,
                      zs: dict = None,
                      indicators: str | list[str] = None,
                      title: str = None,
                      xlabel: str = None,
                      ylabel: str = None,
                      levels: int | np.ndarray = None,
                      n_round_ind: int = 1,
                      cmap: str = 'RdBu_r',
                      path: str = None,
                      baseline: dict | None = None,
                      desired_ind: dict | None = None,
                      marker_color: str = None,
                      crosshair: bool = True,
                      show_baseline_marker: bool = True,
                      show_baseline_contour: bool = True,
                      baseline_ind_color: str = "White",
                      baseline_ind_linestyle: str = '--',
                      desired_ind_color: str = "Green",
                      desired_ind_linestyle: str = "--"
                      ):
        """

        Generate filled contour plots for one or more indicators.

        This method takes precomputed indicator surfaces (returned by `ContourStudy.run_on_grid`) and
        creates filled contour plots using `matplotlib.pyplot.contourf`. Additional features include 
        optional baseline markers, crosshair lines and target-value contours for desired indicator levels.

        Parameters
        ----------
        X, Y : ndarray
            2D arrays of x- and y-coordinates of the grid.
        zs : dict[str, ndarray]
            Mapping from indicator names to 2D arrays of the same shape as ``X`` and ``Y``.
        indicators : str or list[str], optional
            Indicator(s) to plot. If ``None``, all keys in ``zs`` are used. Raises an error if any requested
            name is missing.
        title : str, optional
            Common title for all generated plots. if ``None``, each figure is titled with the indicator name.   #TODO allow to add a title for each figure
        x_label, y_label : str, optional
            Labels for the x and y axes.
        levels : int or array_like, optional
            * if an integer is given, the number of contour levels to generate.
            * if an array is given, explicit contour levels.
            * if `None` levels are generated automatically inferred from the data.
        n_round_ind : int, default=1
            Number of decimals to use when rounding generated contour levels.
        cmap : str, default="RdBu_r"
            Colormap name passed to `matplotlib.pyplot.contourf`.
        path : str, optional
            File path to save each figure. If ``None``, figures are not saved to disk.
        baseline : dict, optional
            Baseline information returned by `ContourStudy.compute_baseline`. If provided, a marker, crosshair and/or indicator contour line can be
            drawn at the baseline point and value.
        desired_ind : dict, optional
            Mapping from indicator name to a dictionary ``{label:value}`` specifying a target contour level to highlight for that indicator (e.g.,
            ``{"MSP": {"Target": 0.83}}``).
        marker_color : str, optional
            color of the baseline indicator. If ``None``, Matplotlib defaults are used.
        crosshair : bool, default=False
            Wether to draw vertical and horizontal lines at the baseline x and y coordinates.
        show_baseline_marker : bool, default=True
            Wether to plot a marker at the baseline plot.
        show_baseline_contour : bool, default=True
            Wether to draw a contour line corresponding to the baseline indicator value.
        baseline_ind_color : str, default="White"
            Color of the baseline indicator contour line.
        baseline_ind_linestyle : str, default="--"
            Line style of the baseline indicator contour line.
        desired_ind_color : str, default="Green"
            Color of the desired indicator contour line(s).
        desired_ind_linestyle : str, default="--"
            Line style of the desired indicator contour line(s).

        """
        # Validate the presence of the indicator selected 
        if indicators is None:
            plot_indicators = list(zs.keys())
        elif isinstance(indicators, str):
            if indicators not in zs:
                raise ValueError(f"Indicator '{indicators}' not in zs: {list(zs)}")
            plot_indicators = [indicators]
        else:
            missing = [ind for ind in indicators if ind not in zs]
            if missing:
                raise ValueError(f"Indicators not found: {missing}. Available: {list(zs)}")
            plot_indicators = list(indicators)
        
        # Helper to get levels from data
        def _levels_from_data(zm, n = 10):
            zmin = np.nanmin(zm); zmax = np.nanmax(zm)
            if not np.isfinite(zmin) or not np.isfinite(zmax):
                raise ValueError("All values are NaN; cannot plot")
            if zmin == zmax:
                eps = (abs(zmin) + 1.0)*1e-6
                zmin -= eps; zmax += eps
            return np.linspace(zmin, zmax, int(n))

        # Mask invalids and plot
        figs = []
        for ind in plot_indicators:
            Z = np.asarray(zs[ind], dtype=float)
            if Z.shape != X.shape or Z.shape != Y.shape:
                raise ValueError("Shape mismatch for {}: X{}, Y{}, Z{}".format(ind, X.shape, Y.shape, Z.shape))
            
            Zm = np.ma.masked_invalid(Z)

            # Build levels
            if levels is None:
                levels_arr = _levels_from_data(Zm, n=10)
            elif isinstance(levels, int):
                levels_arr = _levels_from_data(Zm, n=levels)
            else:
                levels_arr = np.asarray(levels, dtype=float)

            # Create the plot
            fig, ax = plt.subplots()
            cf = ax.contourf(X, Y, Zm, levels = np.round(levels_arr,n_round_ind), cmap = cmap)
            
            # Add the baseline parameters and indicators
            if baseline is not None and isinstance(baseline, dict):
                try:
                    x0, y0 = baseline.get("point", (None, None))
                    if x0 is not None and y0 is not None:
                        if crosshair:
                            ax.axvline(x0, linestyle = '--', linewidth = 1)
                            ax.axhline(y0, linestyle = '--', linewidth = 1)
                        if show_baseline_marker:
                            ax.plot(x0, y0, color = marker_color,marker = 'o', markersize = 6)
                    base_vals = baseline.get("values", {})
                    if show_baseline_contour and ind in base_vals:
                        v0 = float(base_vals[ind])
                        cs = ax.contour(X, Y, Zm, levels = [v0], linewidths = 2, colors = [baseline_ind_color],linestyles = baseline_ind_linestyle)
                        try:
                            ax.clabel(cs, inline = True, fmt = {v0: "{} base".format(ind)})
                        except Exception:
                            pass
                except Exception:
                    pass
            
            if desired_ind is not None and ind in desired_ind:
                val_dict = desired_ind[ind]
                # Check if the value for the indicator (key) is a dictionary.
                if not isinstance(val_dict,dict):
                    raise ValueError("Desired indicator values must be a dictionary[str,float]")
                
                float_values = [float(v) for v in val_dict.values()]

                # Check if the dictionary is empty
                if not val_dict:
                    raise ValueError("desired_ind['{}'] cannot be an empty dict".format(ind))
                
                # Build a dict according to fmt
                fmt_dict = {float(v): label for label,v in val_dict.items()}
                
                # Plot levels provided
                cs = ax.contour(X, Y, Zm, levels = float_values, linewidths = 2, colors = [desired_ind_color], linestyles = desired_ind_linestyle)
                
                # Add label of each level
                try:
                    ax.clabel(cs,inline = True, fmt = fmt_dict)
                except Exception:
                    pass

            # colorbar
            units = None
            for iobj in getattr(self, "indicators",[]):
                if getattr(iobj, "name", None) == ind:
                    units = getattr(iobj, "units", None)
                    break
            cb = fig.colorbar(cf, ax = ax)
            cb.set_label(ind if not units else "{} [{}]".format(ind, units))

            # Configure the plot
            ax.set_title(ind if title is None else title)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            fig.tight_layout()
            
            # Save fig if path provided
            if path:
                fig.savefig(path)
            figs.append((fig, ax, cf))
        
        return figs