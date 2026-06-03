from biosteam import Model
from ..tools.mathtools.sampling import build_cartesian_grid
from ..diagrams.contourplot import plot_contourf
import time
import numpy as np
from tqdm import tqdm
from typing import Literal

__all__ = (
    "ContourAnalysis",
)
class ContourAnalysis:
    """
    """
    def __init__(self, model: Model):
        if model is None:
            raise TypeError("model must be a valid BioSTEAM Model, got None.")
        
        self.model = model
        self.system = model.system

    @property
    def parameters(self):
        """Registered BioSTEAM model parameters."""
        return self.model.parameters

    @property
    def indicators(self):
        """Registered BioSTEAM model metrics."""
        return self.model.indicators
    
    def _get_parameter(self, name_or_parameter):
        """Return a BioSTEAM parameter from either its name or the parameter object"""
        if name_or_parameter in self.parameters:
            return name_or_parameter
        
        if isinstance(name_or_parameter, str):
            for parameter in self.parameters:
                if parameter.name == name_or_parameter:
                    return parameter
            raise ValueError(
                f"Parameter {name_or_parameter} not found. "
                f"Available parameters: {[parameter.name for parameter in self.parameters]!r}"
            )

        raise TypeError(
            "name_or_parameter must be a BioSTEAM parameter object or a parameter name."
        )
    
    def _get_bounds(self, parameter):
        """Return lower and upper bounds from BioSTEAM parameter."""
        return parameter.bounds

    def _get_indicator(self, indicators = None):
        """Return selected BioSTEAM indicator from names or indicator objects."""
        all_indicators = self.indicators

        if indicators is None:
            return all_indicators
        
        if isinstance(indicators, str):
            requested = [indicators]
        else:
            requested = list(indicators)
        
        selected_indicators = []
        name_to_indicator = {indicator.name: indicator for indicator in all_indicators}

        for ind in requested:
            if ind in all_indicators:
                selected_indicators.append(ind)
            elif isinstance(ind, str):
                try:
                    selected_indicators.append(name_to_indicator[ind])
                except KeyError:
                    available = [indicator.name for indicator in self.indicators]
                    raise ValueError(
                        f"Indicator: {ind} not found. "
                        f"Available indicators: {available}"
                    )
            else:
                raise TypeError(
                    "indicators must be None, an indicator name, an indicator object "
                    "or a sequence of indicator names/object."
                )
        
        return selected_indicators

    def _compute_baseline(self, parameter_x, parameter_y, indicators):
        """Compute indicators using baseline values"""
        px = parameter_x
        py = parameter_y

        baseline_x = getattr(px, "baseline", None)
        baseline_y = getattr(py, "baseline", None)

        if baseline_x is None or baseline_y is None:
            raise ValueError(
                "Both contour parameters must define a baseline value "
                "to compute the baseline case."
            )
        
        px.setter(float(baseline_x))
        py.setter(float(baseline_y))
        self.system.simulate()

        values = {}

        for indicator in indicators:
            try:
                values[indicator.name] = float(indicator.getter())
            except Exception as e:
                raise RuntimeError(
                    f"Could not evaluate baseline value for indicator "
                    f"{indicator.name!r}."
                ) from e

        return {
            "point": (float(baseline_x), float(baseline_y)),
            "values": values,
        }

    def _build_grid(
        self,
        parameter_x,
        parameter_y,
        nx,
        ny,
        order,
        xbounds,
        ybounds,
    ):
        """Build a Cartesian grid for two BioSTEAM model parameters"""
        px = self._get_parameter(parameter_x)
        py = self._get_parameter(parameter_y)

        if px is py:
            raise ValueError("parameter_x and parameter_y must be different parameters.")

        if not isinstance(nx, int) or nx < 1:
            raise ValueError(f"nx must be an integer >= 1, got {nx!r}.")

        if not isinstance(ny, int) or ny < 1:
            raise ValueError(f"ny must be an integer >= 1, got {ny!r}.")
        
        if xbounds is None:
            xbounds = self._get_bounds(px)
        
        if ybounds is None:
            ybounds = self._get_bounds(py)
        
        X, Y, pairs, idx_pairs = build_cartesian_grid(
            xbounds=xbounds,
            ybounds=ybounds,
            nx=nx,
            ny=ny,
            return_pairs=True,
            return_idx=True,
            order=order,
        )

        return X, Y, pairs, idx_pairs, px, py
    
    def _run_grid(
        self,
        shape,
        pairs,
        idx_pairs,
        parameter_x,
        parameter_y,
        indicators,
        show_progress: bool = True,
        reset_each_run: bool = False,
    ):
        px = parameter_x
        py = parameter_y

        restore_px = px.baseline
        restore_py = py.baseline

        if len(pairs) != len(idx_pairs):
            raise ValueError("pairs and idx_pairs must have the same lenght.")
        
        ny, nx = shape

        Z = {
            indicator.name: np.full((ny,nx), np.nan, dtype=float) for indicator in indicators
        }

        failures = []

        def register_failure(vx, vy, i, j, stage, error, dt=None):
            failures.append({
                "point": (float(vx), float(vy)),
                "idx": (int(i), int(j)),
                "stage": str(stage),
                "error": repr(error),
                "dt": float(dt) if dt is not None else None,
            })
        
        iterator = zip(pairs, idx_pairs)

        if show_progress:
            iterator = tqdm(
                iterator,
                total=len(pairs),
                desc="Contour analysis",
                unit="sim",
                smoothing=0.0,
                miniters=1,
                mininterval=0.2,
                dynamic_ncols=True
            )
        
        t0 = time.perf_counter()
        try:
            for (vx,vy),(i,j) in iterator:
                i = int(i)
                j = int(j)

                vx = float(vx)
                vy = float(vy)

                if reset_each_run:
                    px.setter(float(restore_px))
                    py.setter(float(restore_py))
                    self.system.empty_recycles()
                    self.system.simulate()

                s0 = time.perf_counter()
                try:
                    try:
                        px.setter(vx)
                        py.setter(vy)
                    except Exception as e:
                        register_failure(vx, vy, i, j, "setter", e)
                        continue
                    
                    try:
                        self.system.simulate()
                    except Exception as e:
                        register_failure(vx, vy, i, j, "simulate", e)
                        continue

                    for indicator in indicators:
                        try:
                            Z[indicator.name][j,i] = float(indicator.getter())
                        except Exception as e:
                            register_failure(vx, vy, i, j, f"indicator:{indicator.name}", e)
            
                finally:
                    if show_progress:
                        dt = time.perf_counter() - s0
                        iterator.set_postfix_str(
                            f"t/it={dt:.2f}s | fails={len(failures)}"
                        )

        finally:
            if show_progress:
                iterator.close()
            
            px.setter(float(restore_px))
            py.setter(float(restore_py))
            self.system.simulate()
        
        elapsed = time.perf_counter() - t0

        return Z, failures, elapsed
    
    def evaluate_contour(
        self,
        parameter_x,
        parameter_y,
        indicators = None,
        nx: int = 20,
        ny: int = 20,
        xbounds = None,
        ybounds = None,
        order: Literal["row","serpentine"] = "row",
        show_progress: bool = True,
        reset_each_run: bool = False,
    ):
        """Evaluate selected BioSTEAM indicators over a 2D parameter grid."""
        X, Y, pairs, idx_pairs, px, py = self._build_grid(
            parameter_x=parameter_x,
            parameter_y=parameter_y,
            nx=nx,
            ny=ny,
            xbounds=xbounds,
            ybounds=ybounds,
            order=order,
        )

        selected_indicators = self._get_indicator(indicators)

        Z, failures, elapsed = self._run_grid(
            shape=Y.shape,
            pairs=pairs,
            idx_pairs=idx_pairs,
            parameter_x=px,
            parameter_y=py,
            indicators=selected_indicators,
            show_progress=show_progress,
            reset_each_run=reset_each_run
        )

        baseline = self._compute_baseline(
            parameter_x = px,
            parameter_y = py,
            indicators = selected_indicators
        )

        return {
            "X": X,
            "Y": Y,
            "Z": Z,
            "failures": failures,
            "parameters": (px, py),
            "indicators": selected_indicators,
            "baseline": baseline,
            "elapsed": elapsed
        }