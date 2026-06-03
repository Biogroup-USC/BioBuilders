"""
Contour plot
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

__all__ = (
    "plot_contourf",
)

def plot_contourf(
    results: dict,
    indicators: str | list[str] = None,
    title: str = None,
    xlabel: str = None,
    ylabel: str = None,
    levels: int | np.ndarray = None,
    n_round_ind: int = 1,
    cmap: str = "Spectral_r",
    path: str | Path = None,
    baseline: dict | None = None,
    use_results_baseline: bool = True,
    desired_ind: dict | None = None,
    marker_color: str = None,
    crosshair: bool = False,
    show_baseline_marker: bool = True,
    show_baseline_contour: bool = True,
    baseline_ind_color: str = "Black",
    baseline_ind_linestyle: str = "--",
    desired_ind_color: str = "Black",
    desired_ind_linestyle: str = "--",
    x_display_fn = None,
    y_display_fn = None,
):
    """
    Generate filled contour plots from contour analysis results.

    Parameters
    ----------
    results : dict
        Dictionary returned by ``ContourAnalysis.evaluate_contour()``.
        Must contain ``"X"``, ``"Y"``, ``"Z"`` and optionally ``"indicators"``.
    indicators : str or list[str], optional
        Indicator name(s) to plot. If ``None``, all indicators in ``results["Z"]``
        are plotted.
    title : str, optional
        Common figure title. If ``None``, each figure is titled with the indicator name.
    xlabel, ylabel : str, optional
        Axis labels.
    levels : int or array_like, optional
        Number of contour levels or explicit contour levels.
    n_round_ind : int, default=1
        Number of decimals used to round generated contour levels.
    cmap : str, default="Spectral_r"
        Matplotlib colormap name.
    path : str or pathlib.Path, optional
        Path to save the figure. If multiple indicators are plotted, the indicator
        name is appended to the filename stem.
    baseline : dict, optional
        Baseline information with ``{"point": (x0, y0), "values": {...}}``.
    desired_ind : dict, optional
        Mapping from indicator name to target contour labels and values, e.g.
        ``{"MSP": {"Target": 0.83}}``.
    x_display_fn, y_display_fn : callable, optional
        Functions used to transform X and Y for plotting. These should accept
        the full X or Y array and return an array with the same shape.

    Returns
    -------
    figs : list[tuple]
        List of ``(fig, ax, contourf)`` tuples.
    """
    X = np.asarray(results["X"], dtype = float)
    Y = np.asarray(results["Y"], dtype = float)
    Z_data = results["Z"]

    if baseline is None:
        if use_results_baseline:
            baseline = results.get("baseline", None)

    if x_display_fn is not None:
        X = np.asarray(x_display_fn(X), dtype = float)

    if y_display_fn is not None:
        Y = np.asarray(y_display_fn(Y), dtype = float)
    
    baseline = _transform_baseline_point(
        baseline,
        x_display_fn=x_display_fn,
        y_display_fn=y_display_fn
    )
    
    if X.shape != Y.shape:
        raise ValueError(f"X and Y must have the same shape. Got X{X.shape}, Y{Y.shape}.")
    
    if indicators is None:
        plot_indicators = list(Z_data.keys())
    
    elif isinstance(indicators, str):
        if indicators not in Z_data:
            raise ValueError(
                f"Indicator {indicators!r} not found. "
                f"Available indicators: {list(Z_data.keys())}"
            )
        plot_indicators = [indicators]
    
    else:
        missing = [ind for ind in indicators if ind not in Z_data]
        if missing:
            raise ValueError(
                f"Indicators not found: {missing}. "
                f"Available indicators: {list(Z_data.keys())}"
            )
        plot_indicators = list(indicators)
    
    indicator_units = _get_indicator_units(results)

    figs = []

    for ind in plot_indicators:
        Z = np.asarray(Z_data[ind], dtype = float)

        if Z.shape != X.shape:
            raise ValueError(
                f"Shape mismatch for {ind!r}: X{X.shape}, Y{Y.shape}, Z{Z.shape}."
            )
        
        Zm = np.ma.masked_invalid(Z)
        levels_arr = _get_levels(Zm, levels, n_round_ind)
    
        fig, ax = plt.subplots()

        cf = ax.contourf(X, Y, Zm, levels = levels_arr, cmap = cmap)

        _add_baseline(
            ax = ax,
            X = X,
            Y = Y,
            Zm = Zm,
            indicator = ind,
            baseline = baseline,
            marker_color = marker_color,
            crosshair = crosshair,
            show_baseline_marker = show_baseline_marker,
            show_baseline_contour = show_baseline_contour,
            baseline_ind_color = baseline_ind_color,
            baseline_ind_linestyle = baseline_ind_linestyle,
        )

        _add_desired_contours(
            ax = ax,
            X = X,
            Y = Y,
            Zm = Zm,
            indicator = ind,
            desired_ind = desired_ind,
            desired_ind_color = desired_ind_color,
            desired_ind_linestyle = desired_ind_linestyle,
        )

        cb = fig.colorbar(cf, ax = ax)
        units = indicator_units.get(ind)
        cb.set_label(ind if not units else f"{ind} [{units}]")

        ax.set_title(ind if title is None else title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        fig.tight_layout()

        if path is not None:
            save_path = _resolve_save_path(path, indicator = ind, n = len(plot_indicators))
            fig.savefig(save_path, dpi = 300, bbox_inches = "tight")
        
        figs.append((fig, ax, cf))
    
    return figs

        
 
def _get_indicator_units(results: dict) -> dict:
    """Return mapping {indicator_name: units} from results metadata"""
    units = {}
    for indicator in results.get("indicators", []):
        name = getattr(indicator, "name", None)
        unit = getattr(indicator, "units", None)

        if name is not None:
            units[name] = unit
    
    return units

def _get_levels(Zm, levels=None, n_round: int = 1):
    """Return contour levels from data or user input"""
    if levels is None:
        levels_arr = _levels_from_data(Zm, n=10)
    
    elif isinstance(levels, int):
        levels_arr = _levels_from_data(Zm, n=levels)
    
    else:
        levels_arr = np.asarray(levels, dtype=float)
    
    print("levels_arr:", levels_arr)
    print("Z min:", np.nanmin(Zm))
    print("Z max:", np.nanmax(Zm))

    return np.round(levels_arr, n_round)

def _levels_from_data(Zm, n: int = 10):
    """Generate equally spaced contour levels from valid Z values."""
    zmin = np.nanmin(Zm)
    zmax = np.nanmax(Zm)

    if not np.isfinite(zmin) or not np.isfinite(zmax):
        raise ValueError("All values are NaN; cannot plot a contour.")
    
    if zmin == zmax:
        eps = (abs(zmin) + 1.0) * 1e-6
        zmin -= eps
        zmax += eps
    
    return np.linspace(zmin, zmax, int(n))

def _add_baseline(
    ax,
    X,
    Y,
    Zm,
    indicator,
    baseline,
    marker_color,
    crosshair,
    show_baseline_marker,
    show_baseline_contour,
    baseline_ind_color,
    baseline_ind_linestyle,
):
    """Add baseline marker, crosshair and baseline indicator contour."""
    if baseline is None or not isinstance(baseline, dict):
        return

    try:
        x0, y0 = baseline.get("point", (None, None))

        if x0 is not None and y0 is not None:
            if crosshair:
                ax.axvline(x0, linestyle="--", linewidth=1)
                ax.axhline(y0, linestyle="--", linewidth=1)

            if show_baseline_marker:
                ax.plot(
                    x0,
                    y0,
                    color=marker_color,
                    marker="o",
                    markersize=6,
                )

        base_values = baseline.get("values", {})

        if show_baseline_contour and indicator in base_values:
            v0 = float(base_values[indicator])

            cs = ax.contour(
                X,
                Y,
                Zm,
                levels=[v0],
                linewidths=2,
                colors=[baseline_ind_color],
                linestyles=baseline_ind_linestyle,
            )

            try:
                ax.clabel(
                    cs,
                    inline=True,
                    fmt={v0: f"{indicator} base"},
                )
            except Exception:
                pass

    except Exception:
        pass

def _add_desired_contours(
    ax,
    X,
    Y,
    Zm,
    indicator,
    desired_ind,
    desired_ind_color,
    desired_ind_linestyle,
):
    """Add desired indicator contour lines."""
    if desired_ind is None or indicator not in desired_ind:
        return

    val_dict = desired_ind[indicator]

    if not isinstance(val_dict, dict):
        raise ValueError("Desired indicator values must be a dictionary[str, float].")

    float_values = [float(v) for v in val_dict.values()]

    if not val_dict:
        raise ValueError(f"desired_ind[{indicator!r}] cannot be an empty dict.")

    fmt_dict = {float(v): label for label, v in val_dict.items()}

    cs = ax.contour(
        X,
        Y,
        Zm,
        levels=float_values,
        linewidths=2,
        colors=[desired_ind_color],
        linestyles=desired_ind_linestyle,
    )

    try:
        ax.clabel(cs, inline=True, fmt=fmt_dict)
    except Exception:
        pass

def _resolve_save_path(path, indicator: str, n: int):
    """Return a save path, creating folders and appending indicator name when needed."""
    path = Path(path)

    # path is a directory or have no file extension
    if path.is_dir() or path.suffix == "":
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{indicator}_contour.png"

    # path is a file path
    path.parent.mkdir(parents=True, exist_ok=True)

    if n == 1:
        return path

    return path.with_name(f"{path.stem}_{indicator}{path.suffix}")

def _transform_baseline_point(baseline, x_display_fn = None, y_display_fn = None):
    """Return a copy of baseline with transformed point coordinates"""
    if baseline is None:
        return None
    
    if not isinstance(baseline, dict):
        raise TypeError("baseline must be a dictionary or None.")
    
    baseline = dict(baseline)
    x0, y0 = baseline.get("point", (None, None))

    if x0 is None or y0 is None:
        return baseline
    
    if x_display_fn is not None:
        x0 = float(
            np.asarray(x_display_fn(np.asarray([[x0]], dtype = float))).ravel()[0]
        )

    if y_display_fn is not None:
        y0 = float(
            np.asarray(
                y_display_fn(np.asarray([[y0]], dtype=float))
            ).ravel()[0]
        )

    baseline["point"] = (float(x0), float(y0))
    return baseline