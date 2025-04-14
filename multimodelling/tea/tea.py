"""
"""
import biosteam as bst

__all__ = (
    "Load_Process_Settings",
    "TEA"
)

def Load_Process_Settings(
            CEPCI: float = 567.5,           # CEPCI is 567.5 (2013) by default (BioSTEAM)
            electricity: float = 0.0782,    # electricity price is 0.0782 USD/kWh by default (BioSTEAM)
            heatutility: list | dict = None,
            coolutility: list | dict = None,
            streamsprice: dict = None,      # The keys of this dict must be the Stream objects from BioSTEAM
            ):
        """

        This function loads all the process settings nedeed to perform the techno economical
        analysis (TEA). 

        A CEPCI, electricity, heating agents and cooling agents prices are needed when performing a
        TEA. Moreover, the prices of certain streams must be defined. For example, the price of the 
        substrate or the enzymes. So, this function simplifies the definition of all process settings
        reducing the code. However, the BioSTEAM workflow could be follow as it is showed in 
        https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html.

        Parameters
        ----------

        CEPCI: float
            The CEPCI is the Chemical Engineering Plant Cost Index which is set by default to 567.5 (2013).
        electricity: float
            The electricity parameters refers to its price in USD/kWh. It is setted by default to 0.0782 USD/kWh.
        heatutility: list | dict
            This parameter is a list of the heating agents used between the following: 'low_pressure_steam', 'medium_pressure_steam',
            'high_pressure_steam', 'natural_gas'.
        coolutility: list | dict
            This parameter is a list of the heating agents used between the following: 'cooling_water', 'chilled_water', 'chilled_brine',
            'propane', 'propylene', 'ethylene'.
        streamsprice: dict
            The streams price dictionary contains all the prices of certain streams like the raw materials, solvents or others. The structure of
            this dictionary is the following: {Stream object : price}. The Stream object is the bst.Stream().

        """
        # CEPCI
        bst.settings.CEPCI = CEPCI

        # Electricity price
        bst.settings.electricity_price = electricity

        # Set the heat utility
        Heat_Utility_List = []
        if heatutility is None:
            # by default the only heat utility used is low pressure steam produced on-site
            Heat_Utility = bst.settings.get_agent('low_pressure_steam')
            bst.settings.heating_agents = [Heat_Utility]
            Heat_Utility.heat_transfer_efficiency = 0.9   #       by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html 
            Heat_Utility.T = 529.2                        # K     by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html
            Heat_Utility.P = 44e5                         # Pa    by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html
            Heat_Utility_List.append(Heat_Utility)
        elif isinstance(heatutility, list):
            # A list of heat utilities from BioSTEAM could be provided and the P, T and heat effiency values are the default 
            for utility in heatutility:
                Heat_Utility = bst.settings.get_agent(utility)
                Heat_Utility_List.append(Heat_Utility)
            bst.settings.heating_agents = Heat_Utility_List
        elif isinstance(heatutility, dict):
            for utility in heatutility.keys():
                pass
        
        # Set the cool utility
        Cool_Utility_List = []
        if coolutility is None:
            # by default the only heat utility used is low pressure steam produced on-site
            Cool_Utility = bst.settings.get_agent('cooling_water')
            bst.settings.cooling_agents = [Cool_Utility]
            Cool_Utility.heat_transfer_efficiency = 0.9   #     by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html 
            Cool_Utility.T = 273.15 + 25                  # K   Set to 25ºC by default
            Cool_Utility.P = 101325                       # Pa  by default in BioSTEAM 
            Cool_Utility_List.append(Cool_Utility)
        elif isinstance(coolutility, list):
            # A list of heat utilities from BioSTEAM could be provided and the P, T and heat effiency values are the default from BioSTEAM
            for utility in coolutility:
                Cool_Utility = bst.settings.get_agent(utility)
                Cool_Utility_List.append(Cool_Utility)
            bst.settings.heating_agents = Cool_Utility_List
        elif isinstance(coolutility, dict):
            for utility in coolutility.keys():
                pass
        
        # Set the prices of the process streams given
        for stream in streamsprice.keys():
            if not isinstance(stream, object):
                raise ValueError("The keys of streamsprice dictionary must be the Stream objects. {} is not a Stream object from Biosteam".format(stream))
            stream.price = streamsprice[stream]
        
        return Heat_Utility_List, Cool_Utility_List

class TEA(bst.TEA):
    """
    """
    def __init__(self, system, IRR, duration, depreciation, income_tax, operating_days, lang_factor,
                 labor_cost, fringe_benefits, property_tax, property_insurance, supplies, maintenance, administration,
                 construction_schedule, startup_months, startup_FOCfrac, startup_VOCfrac, startup_salesfrac, 
                 WC_over_FCI, finance_interest, finance_years, finance_fraction, accumulate_interest_during_construction = False):
        super().__init__(system, IRR, duration, depreciation, income_tax, operating_days, lang_factor, 
                         construction_schedule, startup_months, startup_FOCfrac, startup_VOCfrac, startup_salesfrac, 
                         WC_over_FCI, finance_interest, finance_years, finance_fraction, accumulate_interest_during_construction)
        self.labor_cost = labor_cost
        self.fringe_benefits = fringe_benefits
        self.property_tax = property_tax
        self.property_insurance = property_insurance
        self.supplies= supplies
        self.maintenance = maintenance
        self.administration = administration
        
    def _DPI(self, installed_equipment_cost):
        return super()._DPI(installed_equipment_cost)
    
    def _TDC(self, DPI):
        return super()._TDC(DPI)
    
    def _FCI(self, TDC):
        return super()._FCI(TDC)
    
    def _FOC(self, FCI):
        return (FCI*(self.property_tax + self.property_insurance + self.maintenance + self.administration) + self.labor_cost*(1+self.fringe_benefits+self.supplies))
