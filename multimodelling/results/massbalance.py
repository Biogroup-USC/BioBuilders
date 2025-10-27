"""
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Sequence, Literal, Optional, runtime_checkable, Protocol
from ..tools.streamtools import extract_components_flow
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

    Creates a table of streams for a BioSTEAM system and exports
    it as an image.

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
        if self.components is None:
            comp_set = set()
            for s in self._stream_list:
                components = s.chemicals.IDs
                comp_set.update(components)
            self.components = comp_set
    
    def build_stream_table(
            self,
            *,
            basis: Literal["mass","molar"] = "mass",
            units: dict | None = None,
            T_decimals: int = 1,
            P_decimals: int = 3,
            component_decimals: int = 3,
            totals_decimals: int = 2,
            save_path: str = "stream_table.png",
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
        stream_table_column = []
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
            fig.savefig(save_path, dpi = 300, bbox_inches = "tight", pad_inches = 0.05)

            # Save dataframe
            if excel_path:
                streams_df.to_excel(excel_path,index=True,header=False)

        return streams_df[1:], tab

class DisplayMassResults:
    """

    Create an object for displaying the mass balance of the whole process.

    ARGUMENTS

    - streams (list): list of streams that will be displayed. Remember that 
    a stream is a BioSTEAM object.

    - chemicals (object): Chemicals is the BioSTEAM object that can be created
    using the ChemManager class in Multimodelling. 

    """
    def __init__(self, streams: list = None, chemicals: object = None):
        """
        """
        # Check if the streams have been provided
        if streams is None:
            raise ValueError("At least one stream must be provided")
        self.streams = streams
        
        # Check if the Chemicals object has been provided
        if chemicals is None:
            raise ValueError("The Chemicals (BioSTEAM) object must be provided")
        self.chemicals = chemicals.IDs
    
    def mass_report(self, excelreport: bool = False, excelname: str = "Mass_Balance_Report.xlsx"):
        """
        """
        # Create a dict for inserting the stream data
        Streams_Dict = {}
        
        # Insert the mass flow of each chemical into the dict
        for stream in self.streams:
            Streams_Dict[stream.ID] = stream.mass
        
        # Create the pandas Dataframe
        pd.set_option('display.max_columns', None)
        pd.set_option('display.float_format', '{:.2f}'.format)
        Mass_df = pd.DataFrame(Streams_Dict, index = self.chemicals)
        Mass_df.index.name = "kg/hr"
        print("")
        print("------------------------------------------------------------------------------------------------------------------------------------------------")
        print("                                             MASS REPORT OF THE PROCESS                                                                         ")
        print("------------------------------------------------------------------------------------------------------------------------------------------------")
        print(Mass_df)

        # Create an excel file with the mass balance
        if excelreport is True:
            Mass_df.to_excel(excelname, header = True, index = True)
            
        return Mass_df
    
    def compare_report(self):           #TODO Add a method to compare diferent reports. Do not know if this should be a class method, a diferent class 
        pass                            # or simply a function