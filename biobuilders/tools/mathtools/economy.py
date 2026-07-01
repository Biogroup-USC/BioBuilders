"""
"""

import numpy as np
import math
from typing import Mapping, Sequence, Union

__all__ = (
    "discounting_to_present_value",
    "updating_to_future_value",
    "build_nominal_factor",
    "calculate_labor_requirements",
    "calculate_mean_median_price",
)

# Inflation
def discounting_to_present_value(value: float = None, discount_rate: float = None, years: int = None):
    """
    
    This function discounts the inflation to obtain the present value following the next equation:
    Present_Value = Future_Value / (1 + Discount_Rate)**Number_of_periods

    Parameters
    ----------
    value : float
        The future value.
    
    discount_rate : float
        The discount rate applied.
    
    years : int
        The number of years from the present value to the future value.

    """
    # Calculate the present value
    Future_Value = value
    Discount_Rate = discount_rate
    Number_of_Periods = years
    Present_Value = Future_Value/(1 + Discount_Rate)**Number_of_Periods

    # Return the present value
    return Present_Value

def updating_to_future_value(value: float = None, growth_rate: float = None, years: int = None):
    """
    
    This functions updates the value to get the future value following the next equation:
    Future_Value = Present_Value * (1 + Growth_Rate)**Number_of_periods

    Parameters
    ----------
    value : float
        The future value.
    
    growth_rate : float
        The discount rate applied.
    
    years : int
        The number of years from the present value to the future value.

    """
    # Calculate the future value
    Present_Value = value
    Growth_Rate = growth_rate
    Number_of_Periods = years
    Future_Value = Present_Value * (1 + Growth_Rate)**Number_of_Periods

    # Return the future value
    return Future_Value

def build_nominal_factor(years: Sequence[int], base_year: int, yearly_rates: Union[float, Mapping[int, float]]) -> np.ndarray:
    """
    
    Compute multiplicative factors to convert real (base-year) monetary values
    into nominal values for each year.

    For a given year y, the factor is:
        factor(y) = Π_{k=base_year+1..y} (1 + r_k)
    where r_k is the annual growth/inflation rate applicable to year k.
    By convention, factor(base_year) = 1.0.

    Parameters
    ----------
    years
        A sequence of integer years aligned with your cash-flow table index
        (e.g., [2026, 2027, 2028]) or relative year counters (e.g., [-2, -1, 0, 1, ...]).
        The function returns one factor per element in `years`, in the same order.
    base_year
        The base year at which your values are expressed in real terms.
        Typically this is `years[0]`. Values at `base_year` should not be scaled.
    yearly_rates
        Either:
          A float r (e.g., 0.03 for 3%): a constant annual growth/inflation rate, or
          A mapping {year: rate} giving a (possibly varying) rate for each calendar year.
            Any year not present in the mapping is assumed to have rate 0.0.

        Important: If you pass a mapping, its keys must be in the same year
        coordinate as `years` (i.e., calendar years if `years` are calendar years;
        relative offsets if `years` are relative integers).

    Returns
    -------
    numpy.ndarray
        A 1D array of multiplicative factors aligned with `years`.
        The element corresponding to `base_year` equals 1.0; later years are the
        cumulative product of (1 + rate) up to that year.

    """
    years = np.asarray(years, dtype = int)
    base_year = int(base_year)

    # Constant rate
    if isinstance(yearly_rates, (int,float)):
        r = float(yearly_rates)
        return (1 + r) ** (years - base_year)
    
    # Mapping of year -> rate
    def rate_for(y: int) -> float:
        try:
            return float(yearly_rates[y])
        except (KeyError, TypeError):
            return 0.0
    
    # The last year
    max_year = years.max()

    # Build cumulative product from base_year + 1 ... max_year
    acc = 1.0
    cumulative = [1.0]
    for y in range (base_year + 1, max_year + 1):
        acc *= (1.0 + rate_for(y))
        cumulative.append(acc)
    cumulative = np.asarray(cumulative, dtype = float)

    # Map factors back to requested years
    factors = np.ones_like(years, dtype = float)
    mask = years > base_year
    idx = years[mask] - base_year
    factors[mask] = cumulative[idx]
    return factors

# Labor calculation
## Labor/Equipment correlation
## Reference: Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
## Chapter 6, page 264
labor_per_equip = {
    "Blowers": 0.2,                     # Workers/unit/shift                                      
    "Compressors": 0.2,                 # Workers/unit/shift
    "Centrifugal separators": 0.50,     # Workers/unit/shift            
    "Crystallizer": 0.16,               # Workers/unit/shift
    "Rotatory dryer": 0.5,              # Workers/unit/shift
    "Spray dryer": 1.0,                 # Workers/unit/shift
    "Tray dryer": 0.5,                  # Workers/unit/shift
    "Evaporator": 0.25,                 # Workers/unit/shift
    "Vacuum filter": 0.25,              # Workers/unit/shift    
    "Plate & frame filter": 1.0,        # Workers/unit/shift    
    "Rotatory & belt filter": 0.1,      # Workers/unit/shift    
    "Heat exchanger": 0.1,              # Workers/unit/shift
    "Process vessel": 0.5,              # Workers/unit/shift
    "Batch reactor": 1.0,               # Workers/unit/shift
    "Continuous reactor": 0.5,          # Workers/unit/shift
}

def calculate_labor_requirements(equipment_type_N: dict = None, operators_per_shift_position: int = 4.8): #TODO Peters page 264 table
    """

    Calculate the labor requeriments depending on the number and type of equipments used in
    the process. This calculation could be performed considering 1, 2 or 3 shifts.

    Parameters
    ----------
    equipment_type_N : dict[str,int]
        This dictionary contains each equipment type (key) and its number (value).
        Moreover, the only valid equipments are the following:
            * Blowers
            * Compressors
            * Centrifugal separators
            * Crystallizer
            * Rotatory dryer
            * Spray dryer
            * Tray dryer
            * Evaporator
            * Vacuum filter
            * Plate & frame filter
            * Rotatory & belt filter
            * Heat exchanger
            * Process vessel
            * Batch reactor
            * Continuous reactor
    shifts : int
        Number of shifts to calculate labor requirements.

    Returns
    -------
    Int:
        Labor requirement.
    dict:
        Labor per equipment per shift.

    """
    # Check if the dictionary of equipment is provided
    if equipment_type_N is None:
        raise ValueError("A dictionary of equipment counts must be provided")

    # Dictionary to save the total labor per equipment given the number of each equipment
    labor_per_N_equip = {}
    
    # Total labor variable
    total_labor = 0.0

    # Calculate the total labor per equipment of the process
    for equip in equipment_type_N.keys():
        if equip not in labor_per_equip:
            raise KeyError("{} not found in Labor_per_Equip table: \ {}".format(equip,labor_per_equip))
        labor = equipment_type_N[equip] * labor_per_equip[equip]
        labor_per_N_equip[equip] = labor
        total_labor += labor
    
    labor_ceil = math.ceil(total_labor)

    # Return the total labor and the total labor per equipment
    return labor_ceil*operators_per_shift_position, labor_per_N_equip

def calculate_mean_median_price(prices: list[float] = None, type: int = 0):
    """
    """
    if type == 0:
        price = np.mean(prices)
    elif type == 1:
        price = np.median(prices)
    return price