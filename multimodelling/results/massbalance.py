"""
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Sequence, Literal, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

__all__ = (
    "DisplayMassResults",
    "ProcessMassBalance",
)

class _StreamPrototype:
    ID: str
    phase: str
    T: float
    P: float
    H: float
    vapor_fraction: float | None
    F_mass: float
    F_mol: float
    imass: object
    imol: object

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
            comp = set()
    
    def build_stream_table(
            self,
            *,
            basis: Literal["mass","molar"] = "mass",
            include_energy: bool = False,
            units: dict | None = None,
            component_decimals: int = 3,
            totals_decimals: int = 2,
            order_streams: Optional[Sequence[str]] = None,
    )-> pd.DataFrame:
        """
        """
        units = units or {
            "T": "ºC",
            "P": "bar",
            "v": "-",
            "F": "kg/h",
            "n": "kmol/h",
            "H": "kW",
            "Q": "m3/h"
        }

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