"""
"""
import numpy as np
import biosteam as bst
from biosteam._tea import (
    add_all_replacement_costs_to_cashflow_array,
    solve_payment,
    loan_principal_with_interest,
    taxable_earnings_with_fowarded_losses,
    NPV_at_IRR
)
from typing import Mapping
from ..mathtools.economy import build_nominal_factor

__all__ = (
    "Load_Process_Settings",
    "TEA",
    "TEAInflation"
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

    This object performs the techno-economic analysis of the system
    given.

    Parameters
    ----------
    system : bst.System
        BioSTEAM System object which simulates the process.
    IRR : float
        Internal Return Rate. Set to 0.10 by default.
    duration : tuple
        Lifetime of the project used to calculate all financial
        indicators and cashflows.
    depreciation : str | np.ndarray
        Depreciation schedule array or string with format '{schedule}{years}',
        where years is the number of years until the property value is 0 and schedule
        is one of the following: 'MACRS', 'SL', 'DDB' or 'SYD'. Default to venture years.
    income_tax : float
        Income tax rate. Set to 0.25 by default which is the corporate rate in Spain.
    operating_days : float
        Number of operating days per year.
    lang_factor : float | None
        Lang factor for estimating the fixed capital investment from total purchase cost.
        If no lang is provided, it is estimated using the bare module factors.
    labor_cost : float
        Total labor cost per year ($/year).
    fringe_benefits : float
        Fraction of labor cost for fringe benefits. Set to 0.247 by default since it is the
        average inside UE.
    property_tax : float
        Property tax as a fraction of fixed capital investment. Set to 1% by default.
    property_insurance : float
        Insurance as a fraction of fixed capital investment. Set to 1% by default.
    maintenance : float
        Equipment maintenance costs as a fraction of fixed capital investment. Set to
        7% by default.
    supplies : float
        Operating supplies as a fraction of maintenance. Set to 15% by default.
    administration : float
        Administration cost as a fraction of labour cost. Set to 20% by default.
    construction_schedule : tuple
        Schedule for plant construction which represents the fraction of the fixed capital
        investment spent each year. Note that the construction years will be calculated based
        on the tuple length. Set to (0.5,0.5) by default which means 50% the first year and 50%
        the second year.
    startup_months : float
        Startup time in months until the steady state is achieved.
    startup_FOCfrac : float
        Fraction of fixed operating costs incurred during startup.
    startup_VOCfrac : float
        Fraction of variable operating costs incurred during startup.
    startup_salesfrac : float
        Fraction of sales during startup.
    WC_over_FCI : float
        Working capital as a fraction of fixed capital investment.
    finance_interest : float
        Yearly interest of loan as a fraction.
    finance_years : int
        Number of years the loan is paid for.
    finance_fraction : float
        Fraction of capital cost which needs to be financed.
    accumulate_interest_during_construction : bool
        Whether to accumulate interest during construction years. Set
        to False by default.

    """
    def __init__(self,
                 system: bst.System = None,
                 IRR: float = 0.10,                         # 10% is a common target in medium-risk industrial projects
                 duration: tuple = None,                    
                 depreciation: str | np.ndarray = 'SL',     # Straight line 
                 income_tax: float = 0.25,                  # 25% is the corporate tax rate in Spain
                 operating_days: float = 330,               # 330 days by default 
                 lang_factor: float = None,                 # If no Lang factor is defined, all the installation costs are calculated using the bare module factor
                 labor_cost: float = None,                  
                 fringe_benefits: float = 0.247,            # Non-labour cost from European countries https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Wages_and_labour_costs#Net_earnings_and_tax_burden 
                 property_tax: float = 0.01,                # 1% of FCI as an estimation for industrial property taxes 
                 property_insurance: float = 0.01,          # 1% of FCI is a standard for latge-scale process plants
                 supplies: float = 0.15,                    # 15% of maintenance from Peters, M. S. ., Timmerhaus, K. D. ., & West, R. E. . (2004). Analysis of Cost Estimation. In Plant design and economics for chemical engineers (pp. 226–279). McGraw-Hill. 
                 maintenance: float = 0.07,                 # 7% from Peters, M. S. ., Timmerhaus, K. D. ., & West, R. E. . (2004). Analysis of Cost Estimation. In Plant design and economics for chemical engineers (pp. 226–279). McGraw-Hill.
                 administration: float = 0.20,              # 20% is an average from Peters, M. S. ., Timmerhaus, K. D. ., & West, R. E. . (2004). Analysis of Cost Estimation. In Plant design and economics for chemical engineers (pp. 226–279). McGraw-Hill.
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
        return (FCI*(self.property_tax + self.property_insurance + self.maintenance + self.maintenance * self.supplies) + self.labor_cost*(1 + self.fringe_benefits + self.administration))

class InflationTEA(bst.TEA):            #TODO add inflation to sales, materials, utilities, foc, capex and wc
    """

    This object performs the techno-economic analysis of the system
    given.

    Parameters
    ----------
    system : bst.System
        BioSTEAM System object which simulates the process.
    IRR : float
        Internal Return Rate. Set to 0.10 by default.
    duration : tuple
        Lifetime of the project used to calculate all financial
        indicators and cashflows.
    depreciation : str | np.ndarray
        Depreciation schedule array or string with format '{schedule}{years}',
        where years is the number of years until the property value is 0 and schedule
        is one of the following: 'MACRS', 'SL', 'DDB' or 'SYD'. Default to venture years.
    income_tax : float
        Income tax rate. Set to 0.25 by default which is the corporate rate in Spain.
    operating_days : float
        Number of operating days per year.
    lang_factor : float | None
        Lang factor for estimating the fixed capital investment from total purchase cost.
        If no lang is provided, it is estimated using the bare module factors.
    labor_cost : float
        Total labor cost per year ($/year).
    fringe_benefits : float
        Fraction of labor cost for fringe benefits. Set to 0.247 by default since it is the
        average inside UE.
    property_tax : float
        Property tax as a fraction of fixed capital investment. Set to 1% by default.
    property_insurance : float
        Insurance as a fraction of fixed capital investment. Set to 1% by default.
    maintenance : float
        Equipment maintenance costs as a fraction of fixed capital investment. Set to
        7% by default.
    supplies : float
        Operating supplies as a fraction of maintenance. Set to 15% by default.
    administration : float
        Administration cost as a fraction of labour cost. Set to 20% by default.
    construction_schedule : tuple
        Schedule for plant construction which represents the fraction of the fixed capital
        investment spent each year. Note that the construction years will be calculated based
        on the tuple length. Set to (0.5,0.5) by default which means 50% the first year and 50%
        the second year.
    startup_months : float
        Startup time in months until the steady state is achieved.
    startup_FOCfrac : float
        Fraction of fixed operating costs incurred during startup.
    startup_VOCfrac : float
        Fraction of variable operating costs incurred during startup.
    startup_salesfrac : float
        Fraction of sales during startup.
    WC_over_FCI : float
        Working capital as a fraction of fixed capital investment.
    finance_interest : float
        Yearly interest of loan as a fraction.
    finance_years : int
        Number of years the loan is paid for.
    finance_fraction : float
        Fraction of capital cost which needs to be financed.
    accumulate_interest_during_construction : bool
        Whether to accumulate interest during construction years. Set
        to False by default.

    """
    def __init__(self,
                 system: bst.System = None,
                 IRR: float = 0.10,                                     # 10% is a common target in medium-risk industrial projects
                 duration: tuple = None,                                
                 depreciation: str | np.ndarray = 'SL',                 # Straight line 
                 income_tax: float = 0.25,                              # 25% is the corporate tax rate in Spain
                 operating_days: float = 330,                           # 330 days by default 
                 lang_factor: float = None,                             # If no Lang factor is defined, all the installation costs are calculated using the bare module factor
                 labor_cost: float = None,                              
                 fringe_benefits: float = 0.247,                        # Non-labour cost from European countries https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Wages_and_labour_costs#Net_earnings_and_tax_burden 
                 property_tax: float = 0.01,                            # 1% of FCI as an estimation for industrial property taxes 
                 property_insurance: float = 0.01,                      # 1% of FCI is a standard for latge-scale process plants
                 supplies: float = 0.15,                                # 15% of maintenance from Peters, M. S. ., Timmerhaus, K. D. ., & West, R. E. . (2004). Analysis of Cost Estimation. In Plant design and economics for chemical engineers (pp. 226–279). McGraw-Hill. 
                 maintenance: float = 0.07,                             # 7% from Peters, M. S. ., Timmerhaus, K. D. ., & West, R. E. . (2004). Analysis of Cost Estimation. In Plant design and economics for chemical engineers (pp. 226–279). McGraw-Hill.
                 administration: float = 0.20,                          # 20% is an average from Peters, M. S. ., Timmerhaus, K. D. ., & West, R. E. . (2004). Analysis of Cost Estimation. In Plant design and economics for chemical engineers (pp. 226–279). McGraw-Hill.
                 construction_schedule: tuple = (0.5, 0.5),             # 50% firt year and 50% the sencond by default 
                 startup_months: float = 0,                             # The startup is not taken into account
                 startup_FOCfrac: float = 0,                            # The startup is not taken into account
                 startup_VOCfrac: float = 0,                            # The startup is not taken into account
                 startup_salesfrac: float = 0,                          # The startup is not taken into account
                 WC_over_FCI: float = 0.15,                             # 15% from Smith, R. (2016). *Chemical Process Design and Integration* (2nd ed.). Wiley. ISBN: 978-1-119-99013-0
                 finance_interest: float = None, 
                 finance_years: int = None, 
                 finance_fraction: float = None, 
                 accumulate_interest_during_construction: bool = False, 
                 sales_rate: float | Mapping[int, float] = None,
                 materials_rate: float | Mapping[int, float] = None,
                 utilities_rate: float | Mapping[int, float] = None,
                 foc_rates: float | Mapping[int, float] = None,
                 capex_rates: float | Mapping[int, float] = None,
                 wc_rates: float | Mapping[int, float] = None,
                 global_rate: float | Mapping[int, float] = None,
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

        # New inflation parameters
        self.sales_rate = sales_rate
        self.materials_rate = materials_rate
        self.utilities_rate = utilities_rate
        self.foc_rate = foc_rates
        self.capex_rate = capex_rates
        self.wc_rate = wc_rates
        self.global_rate = global_rate

        # Use global rate value if provided
        if self.global_rate: self.sales_rate = self.materials_rate = self.utilities_rate = self.foc_rate = self.capex_rate = self.wc_rate = self.global_rate

    def _years_index(self) -> np.ndarray:
        """

        Return the year axis used by cashflow table:
        from (start years before first calendar year) to end year.

        """
        return np.arange(self._duration[0] - self._start, self._duration[1], dtype = int)
    
    def _factor(self, rates: float | Mapping[int, float]) -> np.ndarray:
        """
        
        Build multiplicative factors aligned with the cashflow year index.
        if 'rates' is None, return ones.
        
        """
        years = self._years_index()
        return build_nominal_factor(years, years[0], rates) if rates is not None else np.ones_like(years, dtype = float)

    def _DPI(self, installed_equipment_cost):
        return super()._DPI(installed_equipment_cost)
    
    def _TDC(self, DPI):
        return super()._TDC(DPI)
    
    def _FCI(self, TDC):
        return super()._FCI(TDC)
    
    def _FOC(self, FCI):
        """

        Base-year (real) fixed operating costs model (per year).
        Supplies are modelled as a fraction of maintenance; administration as
        a fraction of labour. This value is later scaled year-by-year by 'foc_rates'
        inside cashflow assembly.

        """
        foc_from_fci = FCI*(self.property_tax + self.property_insurance + self.maintenance + self.maintenance * self.supplies) * FCI
        labour = self.labor_cost * (1 + self.fringe_benefits + self.administration)
        return foc_from_fci + labour
    
    def _taxable_nontaxable_depreciation_cashflows(self):
        """
        """
        # Parameters non-influenced by inflation
        TDC = self.TDC
        FCI = self._FCI(TDC)
        start = self._start
        years = self._years

        # Parameters influenced by inflation
        FOC0 = self._FOC(FCI)                   # Base-year FOC
        VOCm0 = self.system.material_cost       # Base-year materials
        VOCu0 = self.utility_cost               # Base-year utilities
        sales0 = self.sales                     # Base-year sales

        # Arrays
        D, C_FC, C_WC, Loan, LP, C, S = np.zeros((7, start + years))

        # Depreciation (historical cost)
        self._fill_depreciation_array(D, start, years, TDC)

        # CAPEX
        C_FC[:start] = FCI * self._construction_schedule

        # Add equipment replacements
        units_iter = self.system.unit_capital_costs.values() if isinstance(self.system, bst.AgileSystem) else self.system.cost_units
        for u in units_iter:
            add_all_replacement_costs_to_cashflow_array(u, C_FC, years, start, self.lang_factor)
        
        # Inflation factors aligned with full year axis
        years_idx = self._years_index()
        f_capex = self._factor(self.capex_rate)
        f_sales = self._factor(self.sales_rate)
        f_mat = self._factor(self.materials_rate)
        f_util = self._factor(self.utilities_rate)
        f_foc = self._factor(self.foc_rate)
        f_wc = self._factor(self.wc_rate)

        # Update CAPEX by year
        C_FC *= f_capex

        # Update working capital
        wc_base = self.WC_over_FCI * FCI            # Base-year amount
        C_WC[start -1] = wc_base * f_wc[start - 1]  # Deposit before operating
        C_WC[-1] = -wc_base * f_wc[-1]              # Release at the endo of the project

        # Update sales and operating costs
        S_op = sales0 * f_sales[start:]
        VOCm_op = VOCm0 * f_mat[start:]
        VOCu_op = VOCu0 * f_util[start:]
        FOC_op = FOC0 * f_foc[start:]

        w0 = self._startup_time
        if years >= 1:
            # first operating year: weighted between "startup" and "steady"
            C[start] = w0*(self.startup_VOCfrac*(VOCm_op[0] + VOCu_op[0]) + self.startup_FOCfrac*FOC_op[0]) \
                       + (1.0 - w0)*((VOCm_op[0] + VOCu_op[0]) + FOC_op[0])
            S[start] = w0*self.startup_salesfrac*S_op[0] + (1.0 - w0)*S_op[0]
        if years > 1:
            C[start+1:] = (VOCm_op[1:] + VOCu_op[1:]) + FOC_op[1:]
            S[start+1:] = S_op[1:]

        # Financing (nominal)
        if self.finance_interest:
            r = self.finance_interest
            n = self.finance_years or 0
            Loan[:start] = (self.finance_fraction or 0.0) * C_FC[:start]

            if self.accumulate_interest_during_construction:
                principal0 = loan_principal_with_interest(Loan[:start], r)
            else:
                principal0 = Loan[:start].sum()

            LP[start:start + n] = solve_payment(principal0, r, n)

            taxable_cashflow    = S - C - D - LP
            nontaxable_cashflow = D + Loan - C_FC - C_WC

            # If not capitalizing interest during construction, subtract it from NPV as cash out
            if not self.accumulate_interest_during_construction:
                LI_construction = Loan[:start] * r
                nontaxable_cashflow[:start] -= LI_construction
        else:
            taxable_cashflow    = S - C - D
            nontaxable_cashflow = D - C_FC - C_WC

        return taxable_cashflow, nontaxable_cashflow, D
    
    def get_cashflow_table(self):
        """
        Return a cashflow table. If inflation rates are provided, the table is **nominal**
        (sales, OPEX, CAPEX, WC scaled per-year; depreciation at historical cost).
        NPV is computed with your TEA IRR (use nominal IRR for nominal flows).
        """
        TDC = self.TDC
        FCI = self._FCI(TDC)
        start = self._start
        years = self._years
        length = start + years

        # base-year blocks
        FOC0 = self._FOC(FCI)
        VOCm0 = self.system.material_cost
        VOCu0 = self.system.utility_cost
        sales0 = self.sales

        # factors
        years_idx = self._years_index()
        f_capex = self._factor(self.capex_rate)
        f_sales = self._factor(self.sales_rate)
        f_mat   = self._factor(self.materials_rate)
        f_util  = self._factor(self.utilities_rate)
        f_foc   = self._factor(self.foc_rate)
        f_wc    = self._factor(self.wc_rate)

        # arrays
        C_D  = np.zeros(length)  # Depreciable capital outlay
        C_FC = np.zeros(length)  # Fixed capital investment
        C_WC = np.zeros(length)
        D    = np.zeros(length)
        L    = np.zeros(length)
        LI   = np.zeros(length)
        LP   = np.zeros(length)
        LPl  = np.zeros(length)
        C    = np.zeros(length)  # Annual operating cost (excl. dep.)
        S    = np.zeros(length)
        T    = np.zeros(length)
        I    = np.zeros(length)
        TE   = np.zeros(length)
        FL   = np.zeros(length)
        NE   = np.zeros(length)
        CF   = np.zeros(length)
        DF   = np.zeros(length)
        NPV  = np.zeros(length)
        CNPV = np.zeros(length)

        # depreciation (historical)
        self._fill_depreciation_array(D, start, years, TDC)

        # CAPEX construction (base-year), then nominalize
        C_D[:start]  = TDC * self._construction_schedule
        C_FC[:start] = FCI * self._construction_schedule

        # replacements (base-year amounts first)
        units_iter = self.system.unit_capital_costs.values() if isinstance(self.system, bst.AgileSystem) else self.system.cost_units
        for u in units_iter:
            add_all_replacement_costs_to_cashflow_array(u, C_FC, years, start, self.lang_factor)
            add_all_replacement_costs_to_cashflow_array(u, C_D,  years, start, self.lang_factor)

        # nominalize CAPEX lines
        C_FC *= f_capex
        C_D  *= f_capex

        # Working capital
        wc_base = self.WC_over_FCI * FCI
        C_WC[start - 1] = wc_base * f_wc[start - 1]
        C_WC[-1]        = -wc_base * f_wc[-1]
        
        # Sales and costs (nominal) with startup
        S_op    = sales0 * f_sales[start:]
        VOCm_op = VOCm0  * f_mat[start:]
        VOCu_op = VOCu0  * f_util[start:]
        FOC_op  = FOC0   * f_foc[start:]

        w0 = self._startup_time
        if years >= 1:
            C[start] = w0*(self.startup_VOCfrac*(VOCm_op[0] + VOCu_op[0]) + self.startup_FOCfrac*FOC_op[0]) \
                       + (1.0 - w0)*((VOCm_op[0] + VOCu_op[0]) + FOC_op[0])
            S[start] = w0*self.startup_salesfrac*S_op[0] + (1.0 - w0)*S_op[0]
        if years > 1:
            C[start+1:] = (VOCm_op[1:] + VOCu_op[1:]) + FOC_op[1:]
            S[start+1:] = S_op[1:]

        # Financing (nominal)
        if self.finance_interest:
            r = self.finance_interest
            n = self.finance_years or 0
            end = start + n
            L[:start] = (self.finance_fraction or 0.0) * C_FC[:start]

            # amortization schedule
            if self.accumulate_interest_during_construction:
                principal0 = loan_principal_with_interest(L[:start], r)
            else:
                principal0 = L[:start].sum()
            LP[start:end] = solve_payment(principal0, r, n)

            loan_principal = 0.0
            if self.accumulate_interest_during_construction:
                for i in range(end):
                    li = (loan_principal + L[i]) * r
                    LI[i] = li
                    LPl[i] = loan_principal = loan_principal - LP[i] + li + L[i]
            else:
                for i in range(end):
                    li = 0.0 if i < start else (loan_principal + L[i]) * r
                    LI[i] = li
                    LPl[i] = loan_principal = loan_principal - LP[i] + li + L[i]
                LI[:start] = L[:start] * r

        # Taxable / nontaxable cashflows and taxes
        taxable_cashflow    = S - C - D - LP
        nontaxable_cashflow = D + L - C_FC - C_WC
        if self.finance_interest and not self.accumulate_interest_during_construction:
            nontaxable_cashflow[:start] -= LI[:start]

        TE[:] = taxable_earnings_with_fowarded_losses(taxable_cashflow)
        FL[1:] = (taxable_cashflow - TE).cumsum()[:-1]
        self._fill_tax_and_incentives(I, TE, nontaxable_cashflow, T, D)
        NE[:] = taxable_cashflow + I - T
        CF[:] = NE + nontaxable_cashflow

        # Discount with TEA IRR (nominal if flows are nominal)
        DF[:]  = 1.0 / (1.0 + self.IRR) ** self._get_duration_array()
        NPV[:] = CF * DF
        CNPV[:] = NPV.cumsum()

        # Present in MM$
        DF *= 1e6
        data = np.vstack([C_D, C_FC, C_WC, D, L, LI, LP, LPl, C, S, T, I, TE, FL, NE, CF, DF, NPV, CNPV]) / 1e6
        return bst.pd.DataFrame(
            data.T,
            index=np.arange(self._duration[0] - start, self._duration[1]),
            columns=('Depreciable capital [MM$]',
                     'Fixed capital investment [MM$]',
                     'Working capital [MM$]',
                     'Depreciation [MM$]',
                     'Loan [MM$]',
                     'Loan interest payment [MM$]',
                     'Loan payment [MM$]',
                     'Loan principal [MM$]',
                     'Annual operating cost (excluding depreciation) [MM$]',
                     'Sales [MM$]',
                     'Tax [MM$]',
                     'Incentives [MM$]',
                     'Taxed earnings [MM$]',
                     'Forwarded losses [MM$]',
                     'Net earnings [MM$]',
                     'Cash flow [MM$]',
                     'Discount factor',
                     'Net present value (NPV) [MM$]',
                     'Cumulative NPV [MM$]'),
        )