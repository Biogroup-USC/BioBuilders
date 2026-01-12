"""
"""
from biosteam import settings, UtilityAgent, Thermo, Stream
from typing import Literal
from collections.abc import Mapping

__all__ = (
    "ProcessSettingsManager",
)

ALLOWED_AGENT_ATTRS = {
    "T",
    "P",
    "phase",
    "heat_transfer_price",
    "regeneration_price",
    "heat_transfer_efficiency",
    "T_limit",
    "isfuel",
    "dT",
    "thermo",
    "units",
    "ID",
}

class ProcessSettingsManager:
    """
    """
    def __init__(
            self,
            CEPCI: float = None,
            electricity_price: float = None,
            streams_price: dict[Stream, float] = None,
    ):
        """
        """
        self.CEPCI = CEPCI
        self.electricity_price = electricity_price
        self.streams_price = streams_price

        # Biosteam settings
        self.settings = settings
    
    @property
    def heat_utilities(self):
        """
        """
        return self.settings.heating_agents
    
    @property
    def heat_utilities_ids(self):
        """
        """
        return {util.ID for util in self.settings.heating_agents}

    @property
    def cool_utilities(self):
        """
        """
        return self.settings.cooling_agents

    @property
    def cool_utilities_ids(self):
        """
        """
        return {util.ID for util in self.settings.cooling_agents}

    def create_utility(
            self, 
            utility_type: Literal["Heat","Cool"],
            utility_id: str,
            utility_phase: Literal["l","g"],
            utility_T: float,
            utility_P: float,
            utility_units: Literal["kg/hr","kmol/hr","m3/hr"],
            utility_transfer_price: float,
            utility_regen_price: float,
            utility_transfer_efficiency: float,
            isutilityfuel: bool,
            utility_dT: float,
            utility_thermo: Thermo | None = None,
            utility_T_limit: float = None,
    ):
        """
        """
        # Validate if the same utility exists to avoid duplicates
        if not utility_id or not isinstance(utility_id,str):
            raise TypeError("utility_id must be a non-empty string")
        
        if utility_type not in ("Heat", "Cool"):
            raise ValueError("Utility type must be 'Heat' or 'Cool'")
        
        if utility_id in self.heat_utilities_ids or utility_id in self.cool_utilities_ids:
            raise ValueError(f"Utility '{utility_id}' already exists.")

        # Create the new utility agent
        utility_agent = UtilityAgent(
            ID = utility_id,
            phase = utility_phase,
            T = utility_T,
            P = utility_P,
            units = utility_units,
            thermo = utility_thermo,
            T_limit = utility_T_limit,
            heat_transfer_price = utility_transfer_price,
            regeneration_price = utility_regen_price,
            heat_transfer_efficiency = utility_transfer_efficiency,
            isfuel = isutilityfuel,
            dT = utility_dT,
        )

        # Add this utility agent to settings
        if utility_type == "Heat":
            self.settings.heating_agents.append(utility_agent)
        else:
            self.settings.cooling_agents.append(utility_agent)
    
    def update_utility_agent(
            self,
            utility_id: str,
            **kwargs
    ):
        """
        """
        settings = self.settings

        # Get the utility agent
        if utility_id in self.heat_utilities_ids:
            utility_agent = settings.get_heating_agent(utility_id)
        elif utility_id in self.cool_utilities_ids:
            utility_agent = settings.get_cooling_agent(utility_id)
        else:
            raise ValueError(f"'{utility_id}' is not a valid utility agent. Check heating and"
                             "cooling utilities or create a new utility.")
        
        # validate if the attributes given exist
        for attr, value in kwargs.items():
            if attr not in ALLOWED_AGENT_ATTRS:
                raise AttributeError(f"{attr} is not a valid UtilityAgent attribute")
            
            if not hasattr(utility_agent, attr):
                raise AttributeError(f"UtilityAgent {utility_agent.ID} has no attribute '{attr}'")

            setattr(utility_agent,attr,value)
    
    @staticmethod
    def _set_streams_price(
            streams_prices: dict[Stream, float],
    ):
        """
        """
        for stream, price in streams_prices.items():
            if not isinstance(price, (float, int)):
                raise TypeError(f"Price for '{stream.ID}' stream must be a number (int/float).")
            stream.price = float(price)
    
    def load_settings(self):
        """
        """
        # Load CECPI and electricity price
        if self.CEPCI is not None:
            self.settings.CEPCI = float(self.CEPCI)
        
        if self.electricity_price is not None:
            self.settings.electricity_price = float(self.electricity_price)

        # Load streams price
        if self.streams_price is not None:
            self._set_streams_price(self.streams_price)