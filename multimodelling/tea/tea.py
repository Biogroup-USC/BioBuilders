"""
"""
import numpy as np
import biosteam as bst

__all__ = (
    "Load_Process_Settings",
    "TEA"
)

def Load_Process_Settings(
            CEPCI: float = 567.5,           # CEPCI is 567.5 (2017) by default (BioSTEAM)
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
            This parameter is a list of the cooling agents used between the following: 'cooling_water', 'chilled_water', 'chilled_brine',
            'propane', 'propylene', 'ethylene'.
        streamsprice: dict
            The streams price dictionary contains all the prices of certain streams like the raw materials, solvents or others. The structure of
            this dictionary is the following: {Stream object : price}. The Stream object is the bst.Stream().

        """
        Settings = bst.settings
        # CEPCI
        Settings.CEPCI = CEPCI

        # Electricity price
        Settings.electricity_price = electricity

        # Set the heat utility
        Heat_Utility_ = bst.HeatUtility
        Heat_Utility_List = []
        if heatutility is None:
            # by default the only heat utility used is low pressure steam produced on-site
            Heat_Utility = Heat_Utility_.get_heating_agent('low_pressure_steam')
            Heat_Utility.heat_transfer_efficiency = 0.9   #       by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html 
            Heat_Utility.T = 529.2                        # K     by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html
            Heat_Utility.P = 44e5                         # Pa    by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html
            Heat_Utility_List.append(Heat_Utility)
        elif isinstance(heatutility, list):
            # A list of heat utilities from BioSTEAM could be provided and the P, T and heat effiency values are the default 
            for utility in heatutility:
                Heat_Utility = Heat_Utility_.get_heating_agent(utility)
                Heat_Utility_List.append(Heat_Utility)
        elif isinstance(heatutility, dict):
            # A dictionary which contains the BioSTEAM heat utility as keys and its cost as value
            for utility in heatutility.keys():
                try:
                    Heat_Utility = Heat_Utility_.get_heating_agent(utility)
                    Heat_Utility.regeneration_price = heatutility[utility]*Heat_Utility.MW
                    Heat_Utility_List.append(Heat_Utility)
                except LookupError:
                    Settings.stream_prices[utility] = heatutility[utility]
                    Heat_Utility_List.append(utility)
        
        # Set the cool utility
        Cool_Utility_ = bst.HeatUtility
        Cool_Utility_List = []
        if coolutility is None:
            # by default the only heat utility used is low pressure steam produced on-site
            Cool_Utility = Cool_Utility_.get_cooling_agent('cooling_water')
            Cool_Utility.heat_transfer_efficiency = 0.9   #     by default from https://biosteam.readthedocs.io/en/latest/tutorial/Sugarcane_ethanol_biorefinery.html 
            Cool_Utility.T = 273.15 + 25                  # K   Set to 25ºC by default
            Cool_Utility.P = 101325                       # Pa  by default in BioSTEAM 
            Cool_Utility_List.append(Cool_Utility)
        elif isinstance(coolutility, list):
            # A list of heat utilities from BioSTEAM could be provided and the P, T and heat effiency values are the default from BioSTEAM
            for utility in coolutility:
                Cool_Utility = Cool_Utility_.get_cooling_agent(utility)
                Cool_Utility_List.append(Cool_Utility)
        elif isinstance(coolutility, dict):
            # A dictionary which contains the BioSTEAM cool utility as keys and its cost as value
            for utility in coolutility.keys():
                try:
                    Cool_Utility = Cool_Utility_.get_cooling_agent(utility)
                    Cool_Utility.cost = coolutility[utility]
                    Cool_Utility_List.append(Cool_Utility)
                except LookupError:
                    Settings.stream_prices[utility] = coolutility[utility]
                    Cool_Utility_List.append(coolutility[utility])

        # Set the prices of the process streams given
        for stream in streamsprice.keys():
            if not isinstance(stream, object):
                raise ValueError("The keys of streamsprice dictionary must be the Stream objects. {} is not a Stream object from Biosteam".format(stream))
            stream.price = streamsprice[stream]
        
        return Heat_Utility_List, Cool_Utility_List

class TEA(bst.TEA):
    """
    """
    def __init__(self,
                 system: object = None,
                 IRR: float = 0.10,                         # 10% is a common target in medium-risk industrial projects
                 duration: tuple = None,                    
                 depreciation: str | np.ndarray = 'SL',     # Straight line 
                 income_tax: float = 0.25,                  # 25% is the corporate tax rate in Spain
                 operating_days: float = 330,               # 330 days by default 
                 lang_factor: float = None,                 # If no Lang factor is defined, all the installation costs are calculated using the bare module factor
                 labor_cost: float = None,                  
                 fringe_benefits: float = 0.247,            # Non-labour cost from European countries https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Wages_and_labour_costs#Net_earnings_and_tax_burden 
                 property_tax: float = 0.01,                # 1% of FCI as an estimation for industrial property taxes 
                 property_insurance: float = 0.005,         # 0.5% of FCI is a standard for latge-scale process plants
                 supplies: float = 0.05,                    # 5% is a common assumption for indirect material expenses
                 maintenance: float = 0.03,                 # 3% is an industry average for bio-based facilities
                 administration: float = 0.01,              # 1% is a typical value for admin and support services in industrial operations
                 construction_schedule: tuple = (0.5, 0.5), # 50% firt year and 50% the sencond by default 
                 startup_months: float = 0,                 # The startup is not taken into account
                 startup_FOCfrac: float = 0,                # The startup is not taken into account
                 startup_VOCfrac: float = 0,                # The startup is not taken into account
                 startup_salesfrac: float = 0,              # The startup is not taken into account
                 WC_over_FCI: float = 0.15,                 # 15% from Smith, R. (2016). *Chemical Process Design and Integration* (2nd ed.). Wiley. ISBN: 978-1-119-99013-0
                 finance_interest: float = None, 
                 finance_years: int = None, 
                 finance_fraction: float = None, 
                 accumulate_interest_during_construction: bool = False
                ):
        
        # Call to parent constructor
        super().__init__(system, IRR, duration, depreciation, income_tax, operating_days, lang_factor, 
                         construction_schedule, startup_months, startup_FOCfrac, startup_VOCfrac, startup_salesfrac, 
                         WC_over_FCI, finance_interest, finance_years, finance_fraction, accumulate_interest_during_construction)
        
        # Parameters
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
