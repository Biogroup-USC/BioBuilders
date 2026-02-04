"""
"""
import pandas as pd

__all__ = (
    "get_price_streams_from_CSV",
)

def get_price_streams_from_CSV(CSVfile: str = None, CSVsep: str = None, CSVheader: int = 0, stream_col: str = None, price_col: str = None):
    """
    
    This function is used to import the process parameters from an CSV file converting it
    into a dictionary. Using this dictionary to define the parameters in the differents unit
    of the process makes easier to change them.

    ARGUMENTS:

    - CSVfile (str): Path of the CSV file where the parameters are defined.

    - CSVsep (str): separator used in the CSV file. Set to "," by default.

    - CSVheader (int): line corresponding to the header. Set to 0 by default. Note that 0 in Python represents the first element

    - stream_col (str): Header of the column that corresponds to the name of the stream.

    - price_col (str): Header of the column that corresponds to the price of the stream.

    Note: 
    
    >>> The CSV must follow the next structure
    
    >>> stream_col,price_col
    >>> Feed, price

    """
    # Read the CSV file 
    Df = pd.read_csv(filepath_or_buffer = CSVfile, sep = CSVsep, header = CSVheader, index_col = False)

    # Verify the existence of the column names provided in the CSV file
    Colnames = {stream_col, price_col}
    for name in Colnames:
        if name not in Df.columns:
            raise ValueError("The {} column does not exist in the CSV file.".format(name))
    
    # Create the dictionary with the structure {Stream:Price}
    Stream_Unique = Df[stream_col].unique()
    Stream_List = Stream_Unique.tolist()
    Price_Dict = {}
    for stream in Stream_List:

        # add the price of each stream to the dictionary
        Price_Dict[stream] = float(Df.loc[Df[stream_col] == stream, price_col])

    # Return the dictionary of parameters
    return Price_Dict