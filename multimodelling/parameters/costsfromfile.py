"""
"""
import pandas as pd

__all__ = (
    "get_unit_costs_from_CSV",
)

def get_unit_costs_from_CSV(
        CSVfile: str = None, 
        CSVsep: str = None, 
        CSVheader: int = 0, 
        unit_col: str = None, 
        CE_col: str = None, 
        CEPCI_col: str = None, 
        basecapacity_col: str = None, 
        basecapacityunits_col: str = None,
        ):
    """

    Load unit cost information from a csv file and organise it into a
    structured dictionary suitable for equipment cost scaling or techno-economic
    modelling.

    The function reads a CSV file containing unit-level cost data and checks that all
    required column names exist. Then extracts the corresponding parameters for each
    equipment type (unit):

        * Purchased equipment cost (CE)
        * Reference cost index (CEPCI)
        * Base capacity used for scaling
        * Base capacity units
    
    Parameters
    ----------
    CSVfile : str
        Path to the CSV file containing the cost data.
    CSVsep : str
        Field separator used in the CSV file (e.g., ',', ';', '\t').
    CSVheader : int, default=0
        Row number to use as column names. Passed directly to ``pandas.DataFrame``.
    unit_col : str
        Name of the column identifying each unit or equipment type.
    CE_col : str
        Name of the column containing the purchase equipment cost (CE), typically in USD.
    CEPCI_col : str
        Name of the column containing the CEPCI index value associated with the cost data.
    basecapacity_col : str
        Name of the column containing the base capacity using to scale equipment cost.
    basecapacityunits_col : str
        Name of the column specifying the units of the base capacity.

    """
    # Read the CSV file
    df = pd.read_csv(CSVfile, sep = CSVsep, header = CSVheader, index_col = False)

    # Verify the existence of the column names provided in the CSV file
    colnames = {unit_col,CE_col,CEPCI_col,basecapacity_col,basecapacityunits_col}
    for name in colnames:
        if name not in df.columns:
            raise ValueError("The {} column does not exist in the CSV file.".format(name))
    
    # Create a dictionary with the structure {Unit:{CE:value,CEPCI:value,basecapacity:value}}
    unit = df[unit_col].unique()
    unit_list = unit.tolist()
    cost_dict = {}
    for unit in unit_list:

        # Get the values for each parameter
        CE = float(df.loc[df[unit_col]==unit,CE_col])
        CEPCI = float(df.loc[df[unit_col]==unit,CEPCI_col])
        base_capacity = float(df.loc[df[unit_col]==unit,basecapacity_col])
        base_capacity_units = str(df[df[unit_col]==unit,basecapacityunits_col])

        # Add the parameters of each unit
        cost_dict[unit] = {
            'CE (USD)': CE,
            'CEPCI': CEPCI,
            'Base Capacity': base_capacity,
            'Capacity Units': base_capacity_units
        }
    
    # Return the costs dictionary
    return cost_dict