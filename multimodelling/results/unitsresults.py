"""
"""
import pandas as pd
import biosteam as bst

__all__ = (
    "Display_Units_Results",
)

class Display_Units_Results:
    """
    """
    def __init__(self, units: list = None):
        """
        """
        # Check if the units are provided
        if units is None or not isinstance(units, list):
            raise ValueError("The list of the units must be provided")
        self.units = units

    def display_unit(self, unit: str = None):
        """

        This method displays in the terminal the results of the unit given and
        returns a pandas Dataframe with the unit results.

        ARGUMENTS:

        - unit (str): ID of the unit.

        """
        # Check if the unit is provided
        if unit is None:
            raise ValueError("The unit ID must be provided")
        
        # filter the units by ID
        for element in self.units:
            if element.ID is unit:
                Results = element.results()
            else:
                continue
        
        # Display the unit results in the terminal
        print("-----------------------------------------------------------------------------------------")
        print("The results of the unit {} are:".format(unit))
        print("-----------------------------------------------------------------------------------------")
        print(Results)

        # This method also gives back a pandas Dataframe which contain all unit results
        return Results

    def save_report(self, filename: str = None):
        """
        """
        # Check the filename 
        Filepath = filename if filename is not None else "Unit_Results_Report.xlsx"

        # Results dictionary
        Results_Dict = {}

        # Get the dataframe of each unit
        for unit in self.units:
            
            # unit results
            Unit_Results = unit.results()

            if not Unit_Results.empty:
                
                # Add the results to the dictionary
                Sheet = str(unit.ID).replace(":","_").replace("/","_")[:31]
                Results_Dict[Sheet] = Unit_Results
            else:
                print("")
                print("[Warning] The unit '{}' has no valid results".format(unit.ID))

        if not Results_Dict:
            raise ValueError("No valid results to export")  
    
        # Write the excel file
        with pd.ExcelWriter(Filepath, engine = "openpyxl") as writer:
            for Sheet_name, Df in Results_Dict.items():
                Df.to_excel(writer, sheet_name = Sheet_name, index = True)

    def display_costs(self):
        pass