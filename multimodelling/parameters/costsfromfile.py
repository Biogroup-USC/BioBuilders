"""
"""
import pandas as pd

__all__ = (
    "get_unit_costs_from_CSV"
)

def get_unit_costs_from_CSV(
        CSVfile: str = None, CSVsep: str = None, CSVheader: int = 0, 
        unit_col: str = None, CE_col: str = None, CEPCI_col: str = None, 
        basecapacity_col: str = None, basecapacityunits_col: str = None,
        ):
    """
    """
    # Read the CSV file
    Df = pd.read_csv(CSVfile, sep = CSVsep, header = CSVheader, index_col = False)

    # Verify the existence of the column names provided in the CSV file
    Colnames = {unit_col,CE_col,CEPCI_col,basecapacity_col,basecapacityunits_col}
    for name in Colnames:
        if name not in Df.columns:
            raise ValueError("The {} column does not exist in the CSV file.".format(name))
    
    # Create a dictionary with the structure {Unit:{CE:value,CEPCI:value,basecapacity:value}}
    Unit_Unique = Df[unit_col].unique()
    Unit_List = Unit_Unique.tolist()
    Cost_Dict = {}
    for unit in Unit_List:

        # Get the values for each parameter
        CE = float(Df.loc[Df[unit_col]==unit,CE_col])
        CEPCI = float(Df.loc[Df[unit_col]==unit,CEPCI_col])
        Base_Capacity = float(Df.loc[Df[unit_col]==unit,basecapacity_col])
        Base_Capacity_Units = str(Df[Df[unit_col]==unit,basecapacityunits_col])

        # Add the parameters of each unit
        Cost_Dict[unit] = {
            'CE (USD)': CE,
            'CEPCI': CEPCI,
            'Base Capacity': Base_Capacity,
            'Capacity Units': Base_Capacity_Units
        }
    
    # Return the costs dictionary
    return Cost_Dict