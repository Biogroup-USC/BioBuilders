"""
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Sequence, Literal, Optional, runtime_checkable, Protocol
from ..tools.streamtools import extract_components_flow, validate_compiled_chemicals
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

__all__ = (
    "DisplayMassResults",
    "ProcessMassBalance",
)

@runtime_checkable
class _StreamPrototype(Protocol):
    ID: str
    phase: str
    T: float
    P: float
    H: float
    vapor_fraction: Optional[float]
    F_mass: float
    F_mol: float
    @property
    def imass(self): ...
    @property
    def imol(self): ...

@dataclass
class ProcessMassBalance:
    """

    Creates a table of streams.

    This class is used to create a table of streams to display process
    mass balance.

    Parameters
    ----------
    streams: list[bst.Stream] | bst.System.streams
        Streams of the process.
    components: list[str] | None
        Order and compounds to display (IDs from the chemicals).
        If None, it is created from streams.

    """
    streams: Iterable[_StreamPrototype]
    components: Optional[Sequence[str]] = None
    _stream_list: list[_StreamPrototype] = field(init=False, repr=False)

    def __post_init__(self):
        self._stream_list = list(self.streams)
        self.components = validate_compiled_chemicals(self.streams)
    
    def build_stream_table(
            self,
            *,
            basis: Literal["mass","molar"] = "mass",
            units: dict | None = None,
            T_decimals: int = 1,
            P_decimals: int = 3,
            component_decimals: int = 3,
            totals_decimals: int = 2,
            fig_path: str = None,
            excel_path: str = None
    )-> pd.DataFrame:
        """
        """
        # units for streams table
        units = units or {
            "T": "ºC",
            "P": "bar",
            "v": "-",
            "F": "kg/h",
            "n": "kmol/h",
            "H": "kW",
            "Q": "m3/h"
        }

        # Create column index
        row_idx1 = [
            "Stream",
            "Pressure ({})".format(units["P"]),
            "Temperature ({})".format(units["T"]),
            "Flow basis"
            
        ]
        row_idx2 = list(self.components)
        row_idx3 = ["Total mass flow (kg/h)" if basis == "mass" else "Total molar flow (kmol/h)"]
        row_idx = row_idx1 + row_idx2 + row_idx3

        # Obtain each stream info
        streams_df = pd.DataFrame(index=row_idx)
        for s in self.streams:
            # Stream P
            if units["P"] == "bar":
                stream_P = s.P / 10**5
            elif units["P"] == "kPa":
                stream_P = s.P / 1000
            else:
                stream_P = s.P
            # Stream T
            if units["T"] in ("°C","C","ºC"):
                stream_T = s.T - 273.15
            else:
                stream_T = s.T
            # Get the flow of each component
            components_flow = extract_components_flow(s,basis=basis,components=self.components)
            flows = [round(components_flow[c],component_decimals) for c in self.components]
            # Get the total flow
            total_flow = round((sum(flows)),totals_decimals)
            # Add the column to the dataframe
            new_column = [
                s.ID,
                round(stream_P, P_decimals),
                round(stream_T, T_decimals),
                ("kg/h" if basis == "mass" else "kmol/h"),
                *flows,
                round(total_flow, totals_decimals)
            ]
            streams_df[s.ID] = new_column

        if fig_path:
            # Create streams table
            fig, ax = plt.subplots(figsize = (8, 0.3 + 0.22 * len(streams_df)))
            ax.axis("off")
            tab = ax.table(
                cellText = streams_df.values,
                rowLabels = list(streams_df.index),
                colLabels = None,
                rowLoc = "center", cellLoc = "center", loc = "center",
            )
            # Format
            tab.auto_set_font_size(False); tab.set_fontsize(5); tab.scale(0.9,1.0)
            fig.tight_layout()
            # Save fig
            fig.savefig(fig_path, dpi = 300, bbox_inches = "tight", pad_inches = 0.05)

        # Save dataframe
        if excel_path:
            streams_df.to_excel(excel_path,index=True,header=False)

        return streams_df[1:]