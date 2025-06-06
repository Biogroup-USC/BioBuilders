"""
"""

__all__ = (
    "discounting_to_present_value",
    "updating_to_future_value",
    "calculate_labor_requirements"
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

# Labor calculation
## Labor/Equipment correlation
## Reference: Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
## Chapter 6, page 264
Labor_per_Equip = {
    "Blowers": 0.2,                     # Workers/unit/shift                                      
    "Compressors": 0.2,                 # Workers/unit/shift
    "Centrifugal separators": 0.50,     # Workers/unit/shift            
    "Crystallizer": 0.16,               # Workers/unit/shift
    "Rotatory dryer": 0.5,              # Workers/unit/shift
    "Spray dryer": 1.0,                 # Workers/unit/shift
    "Tray dryer": 0.5,                  # Workers/unit/shift
    "Evaporator": 0.25,                 # Workers/unit/shift
    "Vacuum filter": 0.25,              # Workers/unit/shift    
    "Plate & Frame filter": 1.0,        # Workers/unit/shift    
    "Rotatory & Belt filter": 0.1,      # Workers/unit/shift    
    "Heat Exchanger": 0.1,              # Workers/unit/shift
    "Process vessel": 0.5,              # Workers/unit/shift
    "Batch reactor": 1.0,               # Workers/unit/shift
    "Continuous reactor": 0.5,          # Workers/unit/shift
}

def calculate_labor_requirements(equipment_type_N: dict = None): #TODO Peters page 264 table
    """
    """
    # Check if the dictionary of equipment is provided
    if equipment_type_N is None:
        raise ValueError("A dictionary of equipment counts must be provided")

    # Dictionary to save the total labor per equipment given the number of each equipment
    Labor_per_N_Equip = {}
    
    # Total labor variable
    Total_Labor = 0.0

    # Calculate the total labor per equipment of the process
    for equip in equipment_type_N.keys():
        if equip not in Labor_per_Equip:
            raise KeyError("{} not found in Labor_per_Equip table: \ {}".format(equip,Labor_per_Equip))
        Labor = equipment_type_N[equip] * Labor_per_Equip[equip]
        Labor_per_N_Equip[equip] = Labor
        Total_Labor += Labor

    # Return the total labor and the total labor per equipment
    return Total_Labor, Labor_per_N_Equip