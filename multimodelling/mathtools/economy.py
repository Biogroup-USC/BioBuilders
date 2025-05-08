"""
"""

__all__ = (
    "discounting_to_present_value",
    "updating_to_future_value"
)

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