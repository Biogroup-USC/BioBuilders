"""
"""
import numpy as np
import pandas as pd
import biosteam as bst
from biosteam._tea import (
    add_all_replacement_costs_to_cashflow_array,
    solve_payment,
    loan_principal_with_interest,
    taxable_earnings_with_fowarded_losses,
    cashflow_columns
)
from typing import Mapping
from ..mathtools.economy import build_nominal_factor
from numba import njit

__all__ = (
    "TEA",
    "InflationTEA"
)

@njit(cache = True)
def fill_nominal_taxable_and_nontaxable_cashflows_without_loan(
    FCI, WC, sales0, VOC_mat0, VOC_util0, FOC0,
    construction_schedule, start,
    C_FC, C_WC, S, C,
    f_sales, f_capex, f_mat, f_util, f_foc, f_wc,
    startup_time,
    startup_VOCfrac, startup_FOCfrac, startup_salesfrac, 
):
    """

    Populate (in-place) nominal per-year arrays for CAPEX (construction and any
    pre-filled replacements), Working Capital (deposit/release), Sales, and
    Operating Costs (VOC + FOC). Startup is applied in the first operating year.

    Parameters
    ----------
    FCI : float
        Fixed Capital Investment in base-year currency.
    WC : float
        Working capital in base-year currency (e.g., WC_over_FCI * FCI).
    sales0 : float
        Steady-state annual sales in base-year currency (pre-inflation).
    VOC_mat0 : float
        Steady-state annual raw materials cost in base-year currency.
    VOC_util0 : float
        Steady-state annual utilities cost in base-year currency.
    FOC0 : float
        Steady-state annual fixed operating cost in base-year currency.
    construction_schedule : 1d ndarray (len == start)
        Fractions of FCI invested per construction year.
    start : int
        Number of construction years; index of first operating year in arrays.
    C_FC, C_WC, D, S, C : 1d ndarrays
        Output arrays (length = start + years). D is not modified here.
    f_sales, f_capex, f_mat, f_util, f_foc, f_wc : 1d ndarrays
        Nominal factors aligned with the full calendar index (construction + operation).
    startup_time : float in [0,1]
        Fraction of the first operating year under startup conditions.
    startup_VOCfrac, startup_FOCfrac, startup_salesfrac : float in [0,1]
        Fractions applied to VOC, FOC and Sales during the startup portion.

    """
    # Fill C_FC
    C_FC[:start] = FCI * construction_schedule

    # Nominalise CAPEX
    C_FC[:] *= f_capex

    # Nominalise WC
    wc_base = WC
    C_WC[start-1] = wc_base * f_wc[start-1]
    C_WC[-1] = -wc_base * f_wc[-1]

    # Nominalise sales
    S_nom = sales0 * f_sales[start:]

    # Nominalise material cost
    VOC_mat_nom = VOC_mat0 * f_mat[start:]

    # Nominalise utility cost
    VOC_util_nom = VOC_util0 * f_util[start:]

    # Nominalise FOC
    FOC_nom = FOC0 * f_foc[start:]

    # Calculate C and S
    start1 = start + 1
    C[start1:] = (FOC_nom + VOC_mat_nom + VOC_util_nom)[1:]
    S[start1:] = S_nom[1:]

    # Calculate C and S of first years (including startup)
    w0 = startup_time
    w1 = 1. - w0
    VOC = VOC_mat_nom[0] + VOC_util_nom[0]
    FOC = FOC_nom[0]
    sales = S_nom[0]
    
    C[start] = (w0 * startup_VOCfrac * VOC + w1 * VOC
                + w0 * startup_FOCfrac * FOC + w1 * FOC)
    S[start] = w0 * startup_salesfrac * sales + w1 * sales

def nominal_taxable_and_nontaxable_cashflows(
    FCI, WC, sales0, VOC_mat0, VOC_util0, FOC0,
    construction_schedule, start,
    C_FC, C_WC, D, S, C, L, LP,
    f_sales, f_capex, f_mat, f_util, f_foc, f_wc,
    startup_time, startup_VOCfrac, startup_FOCfrac, startup_salesfrac,
    finance_interest, finance_years, finance_fraction, accumulate_interest_during_construction,

):
    """
    """
    # fill nominal cashflows excluding finances
    fill_nominal_taxable_and_nontaxable_cashflows_without_loan(
        FCI, WC, sales0, VOC_mat0, VOC_util0, FOC0,
        construction_schedule, start,
        C_FC, C_WC, S, C,
        f_sales, f_capex, f_mat, f_util, f_foc, f_wc,
        startup_time, startup_VOCfrac, startup_FOCfrac, startup_salesfrac 
    )

    # Finance
    if finance_interest:
        # Interest and years to pay
        interest = finance_interest
        years_pay = finance_years if finance_years else 0
        
        # Calculate the amount of the loan 
        L[:start] = loan = finance_fraction * C_FC[:start]

        # Accumulate interest during construction or not
        if accumulate_interest_during_construction:
            loan_principal = loan_principal_with_interest(loan, interest)
        else:
            loan_principal = loan.sum()
        
        # Solve loan payment
        LP[start:start + years_pay] = solve_payment(loan_principal, interest, years_pay)
        taxable_cashflow = S - C - D - LP
        nontaxable_cashflow = D + L - C_FC - C_WC
        if not accumulate_interest_during_construction:
            nontaxable_cashflow[:start] -= loan * interest
    else:
        taxable_cashflow = S - C - D
        nontaxable_cashflow = D - C_FC - C_WC
    
    return taxable_cashflow, nontaxable_cashflow

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

class InflationTEA(bst.TEA):
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
                 sales_rates: float | Mapping[int, float] = None,
                 materials_rates: float | Mapping[int, float] = None,
                 utilities_rates: float | Mapping[int, float] = None,
                 foc_rates: float | Mapping[int, float] = None,
                 capex_rates: float | Mapping[int, float] = None,
                 wc_rates: float | Mapping[int, float] = None,
                 global_rates: float | Mapping[int, float] = None,
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
        self.sales_rates = sales_rates
        self.materials_rates = materials_rates
        self.utilities_rates = utilities_rates
        self.foc_rates = foc_rates
        self.capex_rates = capex_rates
        self.wc_rates = wc_rates
        self.global_rates = global_rates

    def _years_index(self) -> np.ndarray:
        """

        Return the year axis used by cashflow table:
        from (start years before first calendar year) to end year.

        """
        return np.arange(self._duration[0] - self._start, self._duration[1], dtype = int)
    
    def _pick_rate(self, specific):
        """
        
        Use the specific rate when provided. Otherwise, use global rate.

        """
        return specific if specific is not None else self.global_rates

    def _factor(self, rates: float | Mapping[int, float]) -> np.ndarray:
        """
        
        Build multiplicative factors aligned with the cashflow year index.
        if 'rates' is None, return ones.
        
        """
        years = self._years_index()
        picked = self._pick_rate(rates)
        return build_nominal_factor(years, years[0], picked) if picked is not None else np.ones_like(years, dtype = float)

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
        foc_from_fci = FCI * (self.property_tax + self.property_insurance + self.maintenance + self.maintenance * self.supplies)
        labour = self.labor_cost * (1 + self.fringe_benefits + self.administration)
        return foc_from_fci + labour
    
    def _taxable_nontaxable_depreciation_cashflows(self):
        """
        """
        # Base-year cashflows
        TDC, FCI = self.TDC, self._FCI(self.TDC)
        FOC0 = self._FOC(FCI)
        start, years = self._start, self._years
        VOC_mat0, VOC_util0 = self.system.material_cost, self.system.utility_cost
        sales0 = self.sales

        # Arrays for calculating cashflow
        C_FC, C_WC, D, S, C, L, LP = np.zeros((7, start + years))

        # Fill depreciation array
        self._fill_depreciation_array(D, start, years, TDC)

        # Add the cost of the replacements
        units_cap_costs = self.system.unit_capital_costs if isinstance(self.system, bst.AgileSystem) else self.system.cost_units
        for unit in units_cap_costs:
            add_all_replacement_costs_to_cashflow_array(unit, C_FC, years, start, self.system.lang_factor)
        
        # Load nominal factor with _factor helper
        f_sales = self._factor(self.sales_rates)
        f_capex = self._factor(self.capex_rates)
        f_mat = self._factor(self.materials_rates)
        f_util = self._factor(self.utilities_rates)
        f_foc = self._factor(self.foc_rates)
        f_wc = self._factor(self.wc_rates)

        # calculate taxable and non taxable cashflows
        return (
            *nominal_taxable_and_nontaxable_cashflows(
                FCI, FCI * self.WC_over_FCI, sales0, VOC_mat0, VOC_util0, FOC0,
                self.construction_schedule, start,
                C_FC, C_WC, D, S, C, L, LP,
                f_sales, f_capex, f_mat, f_util, f_foc, f_wc,
                self._startup_time, self.startup_VOCfrac, self.startup_FOCfrac, self.startup_salesfrac,
                self.finance_interest, self.finance_years, self.finance_fraction, self.accumulate_interest_during_construction, 
            ),
            D
        )
    
    def get_cashflow_table(self):
        """
        """
        # Base-year cashflows
        TDC, FCI = self.TDC, self._FCI(self.TDC)
        FOC0 = self._FOC(FCI)
        VOC_mat0, VOC_util0 = self.system.material_cost, self.system.utility_cost
        sales0 = self.sales
        
        # Lifetime
        start, years = self._start, self._years
        length = start + years

        # Generate arrays
        C_D, C_FC, C_WC, D, L, LI, LP, LPl, C, S, T, I, TE, FL, NE, CF, DF, NPV, CNPV = data = np.zeros((19, length))

        # Fill depreciation
        self._fill_depreciation_array(D, start, years, TDC)

        # Build nominal factors array
        f_sales = self._factor(self.sales_rates)
        f_capex = self._factor(self.capex_rates)
        f_mat = self._factor(self.materials_rates)
        f_util = self._factor(self.utilities_rates)
        f_foc = self._factor(self.foc_rates)
        f_wc = self._factor(self.wc_rates)
        
        # Nominalise CAPEX
        system = self.system
        lang_factor = self.lang_factor
        unit_capital_costs = system.unit_capital_costs if isinstance(system, bst.AgileSystem) else system.cost_units
        for unit in unit_capital_costs: add_all_replacement_costs_to_cashflow_array(unit, C_FC, years, start, lang_factor)

        C_FC[:start] = FCI * self.construction_schedule
        C_FC *= f_capex

        # Nominalise depreciable capital
        C_D[:start] = TDC * self.construction_schedule
        C_D *= f_capex

        # Nominalise OPEX and sales
        FOC_nom         =   FOC0        *   f_foc[start:]
        VOC_mat_nom     =   VOC_mat0    *   f_mat[start:]
        VOC_util_nom    =   VOC_util0   *   f_util[start:]
        S_nom           =   sales0      *   f_sales[start:]

        # Calculate S and C
        start1 = start + 1
        C[start1:] = (FOC_nom + VOC_mat_nom + VOC_util_nom)[1:]
        S[start1:] = S_nom[1:]

        # Calculate C and S of first year (including startup)
        w0 = self._startup_time
        w1 = 1. - w0
        VOC = VOC_mat_nom[0] + VOC_util_nom[0]
        FOC = FOC_nom[0]
        sales = S_nom[0]

        C[start] = (w0 * self.startup_VOCfrac * VOC + w1 * VOC
                    + w0 * self.startup_FOCfrac * FOC + w1 * FOC)
        S[start] = w0 * self.startup_salesfrac * sales + w1 * sales

        # Nominalise working capital
        WC = self.WC_over_FCI * FCI
        C_WC[start-1] = WC * f_wc[start-1]
        C_WC[-1] = -WC * f_wc[-1]

        # Add finance if a fraction of TCI is a loan; calculate taxable and non taxable cashflows
        if self.finance_interest:
            # Financial parameters
            interest = self.finance_interest
            years_pay = self.finance_years
            end = start + years_pay
            
            # Calculate loan
            L[:start] = loan = self.finance_fraction * (C_FC[:start])

            # Calculate 
            if self.accumulate_interest_during_construction:
                initial_loan_principal = loan_principal_with_interest(loan, interest)
            else:
                initial_loan_principal = loan.sum()
            
            # Solve loan payment
            LP[start:end] = solve_payment(initial_loan_principal, interest, years_pay)
            
            # Calculate interest during construction
            loan_principal = 0
            if self.accumulate_interest_during_construction:
                for i in range(end):
                    LI[i] = li = (loan_principal + L[i]) * interest
                    LPl[i] = loan_principal = loan_principal - LP[i] + li + L[i]
            else:
                for i in range(end):
                    if i < start:
                        li = 0.0
                    else:
                        li = (loan_principal + L[i]) * interest
                    LI[i] = li
                    LPl[i] = loan_principal = loan_principal - LP[i] + li + L[i]
                LI[:start] = L[:start] * interest
            taxable_cashflow = S - C - D - LP
            nontaxable_cashflow = D + L -C_FC - C_WC
            if not self.accumulate_interest_during_construction:
                nontaxable_cashflow[:start] -= LI[:start]
        else:
            taxable_cashflow = S - C - D
            nontaxable_cashflow = D - C_FC - C_WC
        
        # Taxable earnings with forwarded losses
        TE[:] = taxable_earnings_with_fowarded_losses(taxable_cashflow)
        
        # Forwarded losses
        FL[1:] = (taxable_cashflow -TE).cumsum()[:-1]

        # Fill taxes and incentives
        self._fill_tax_and_incentives(I, TE, nontaxable_cashflow, T, D)

        # Fill net earnings
        NE[:] = taxable_cashflow + I - T

        # Fill cash flow
        CF[:] = NE + nontaxable_cashflow

        # Fill discount factor
        DF[:] = 1/(1 + self.IRR)**self._get_duration_array()

        # Fill net present value
        NPV[:] = CF * DF

        # Fill cumulative discount factor
        CNPV[:] = NPV.cumsum()

        DF *= 1e6
        data /= 1e6
        return pd.DataFrame(
            data.transpose(), index = np.arange(self._duration[0]-start, self._duration[1]), columns = cashflow_columns
        )