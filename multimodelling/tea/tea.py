"""
"""
import biosteam as bst

__all__ = (
    "Process_Costs"
)

class Process_Costs:
    """
    """
    def __init__(self,
                 CEPCI: float = None,
                 electricity: float = None,
                 heatutility: dict = None,
                 streamsprice: dict = None
                 ):
        """
        """
        self.CEPCI = CEPCI if CEPCI is not None else bst.settings.CEPCI                                     # CEPCI is 567.5 (2013) by default (BioSTEAM)
        self.electricity_price = electricity if electricity is not None else bst.settings.electricity_price # electricity price is 0.0782 USD/kWh by default (BioSTEAM) 
        self.streams_price = streamsprice
        

class TEA(bst.TEA):
    """
    """
