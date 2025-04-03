import pandas as pd

__all__ = (
    'get_parameters_from_excel',
    'get_parameters_from_CSV'
)

def get_parameters_from_excel(excelfile: str = None, sheet: str = None, section_col: str = None, key_col: str = None, value_col: str = None):
    """

    This function is used to import the process parameters from an excel file converting it
    into a dictionary. Using this dictionary to define the parameters in the differents unit
    of the process makes easier to change them.

    ARGUMENTS:

    - excelfile (str): Path of the excel file where the parameters are defined.

    - sheet (str): Name of the Sheet where the parameters are defined. This allows to use 
    the same excel file for different scenarios or processes.

    - section_col (str): Header of the column that corresponds to the process unit or feed composition, for example.

    - key_col (str): Header of the column that corresponds to the parameters´ name.

    - value_col (str): Header of the column that corresponds to the parameters´ value.

    Note: 
    
    >>> The excel which contains the parameters of the whole process must have the next structure:
    
    >>> | section_col | key_col | value_col |
    >>> |-----------------------------------|
    >>> | Waste_Flow  | key 1   | value 1   |
    >>> | unit 1      | key 2   | value 2   |
    >>> | unit 2      | key 1   | value 1   |

    """
    if excelfile is None:
        raise ValueError("The excelfile argument is missing")
    elif sheet is None:
        raise ValueError("The sheet argument is missing")
    elif section_col is None:
        raise ValueError("The section_col argument is missing")
    elif key_col is None:
        raise ValueError("The key_col argument is missing")
    elif value_col is None:
        raise ValueError("The value_col argument is missing")

    # Read the excel file
    Df = pd.read_excel(io = excelfile, sheet_name = sheet)

    # verify whether the columns exist in the excel file or not
    Colnames = {section_col, key_col, value_col}
    for name in Colnames:
        if name not in Df.columns:
            raise ValueError("The {} column does not exist in the Excel file.".format(name))
    
    # Create a dictionary with the structure {Unit {key:value}}
    Section_Unique = Df[section_col].unique()
    Section_List = Section_Unique.tolist()
    Param_Dict = {}
    for section in Section_List:

        # Get the keys and values for unit
        keys = Df.loc[Df[section_col] == section, key_col].tolist()
        values = Df.loc[Df[section_col] == section, value_col].tolist()

        # Add the parameters of each section to the Param_Dictionary
        Param_Dict[section] = dict(zip(keys,values))
    
    # Return the parameter dictionary
    return Param_Dict

        

def get_parameters_from_CSV(CSVfile: str = None, CSVsep: str = None, CSVheader: int = 0, section_col: str = None, key_col: str = None, value_col: str = None):
    """
    
    This function is used to import the process parameters from an CSV file converting it
    into a dictionary. Using this dictionary to define the parameters in the differents unit
    of the process makes easier to change them.

    ARGUMENTS:

    - CSVfile (str): Path of the CSV file where the parameters are defined.

    - CSVsep (str): separator used in the CSV file. Set to "," by default.

    - CSVheader (int): line corresponding to the header. Set to 0 by default. Note that 0 in Python represents the first element

    - section_col (str): Header of the column that corresponds to the process unit or feed composition, for example.

    - key_col (str): Header of the column that corresponds to the parameters´ name.

    - value_col (str): Header of the column that corresponds to the parameters´ value.

    Note: 
    
    >>> The CSV must follow the next structure
    
    >>> Section_col,key_col,value_col
    >>> Feed,parameter,value
    >>> Unit1,parameter,value
    >>> Unit1,parameter,value

    """
    # Read the CSV file 
    Df = pd.read_csv(filepath_or_buffer = CSVfile, sep = CSVsep, header = CSVheader, index_col = False)

    # Verify the existence of the column names provided in the CSV file
    Colnames = {section_col, key_col, value_col}
    for name in Colnames:
        if name not in Df.columns:
            raise ValueError("The {} column does not exist in the CSV file.".format(name))
    
    # Create the dictionary with the structure {section:{key:value}}
    Section_Unique = Df[section_col].unique()
    Section_List = Section_Unique.tolist()
    Param_Dict = {}
    for section in Section_List:

        # Get the keys and values for unit
        keys = Df.loc[Df[section_col] == section, key_col].tolist()
        values = Df.loc[Df[section_col] == section, value_col].tolist()
        
        # Convert the values from string to float and interger if it is posible, 
        # otherwise it remains as string.
        new_values = []
        for value in values:
            try:
                new_value = float(value)
                if new_value.is_integer():
                    new_values.append(int(new_value))
                else:
                    new_values.append(new_value)
            
            except ValueError:
                new_value = str(value)
                new_values.append(new_value)
        values = new_values

        # Add the parameters of each section to the Param_Dictionary
        Param_Dict[section] = dict(zip(keys,values))
    
    # Return the dictionary of parameters
    return Param_Dict