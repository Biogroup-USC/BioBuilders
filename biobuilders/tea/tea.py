"""
"""
import numpy as np
import biosteam as bst
from typing import Optional

__all__ = (
    "TEA",
    "InflationTEA"
)

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
                 labor_cost: float = 0.0,                  
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
                 accumulate_interest_during_construction: bool = False,
                 inflation_rate: Optional[float] = None,
                 start_year: Optional[int] = None,
                 ignore_cogen_costs = False
                ):
        
        # Call to parent constructor
        super().__init__(system, IRR, duration, depreciation, income_tax, 
                         operating_days, lang_factor, 
                         construction_schedule, startup_months, 
                         startup_FOCfrac, startup_VOCfrac, startup_salesfrac, 
                         WC_over_FCI, finance_interest, finance_years, 
                         finance_fraction, accumulate_interest_during_construction)
        
        # Added parameters
        self.labor_cost = labor_cost
        self.fringe_benefits = fringe_benefits
        self.property_tax = property_tax 
        self.property_insurance = property_insurance
        self.supplies= supplies
        self.maintenance = maintenance
        self.administration = administration

        self.ignore_cogen_costs = ignore_cogen_costs
    
    def _utility_costs(self, base_cost):
        """
        Apply cogeneration logic
        """
        return 0.0 if self.ignore_cogen_costs else base_cost

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
        foc_from_fci = FCI*(self.property_tax + self.property_insurance + self.maintenance + self.maintenance * self.supplies)
        foc_from_labour = self.labor_cost*(1 + self.fringe_benefits + self.administration)
        return foc_from_fci + foc_from_labour