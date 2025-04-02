"""
"""
import pandas as pd

class Display_Mass_Results:
    """

    Create an object for displaying the mass balance of the whole process.

    ARGUMENTS

    - streams (list): list of streams that will be displayed. Remember that 
    a stream is a BioSTEAM object.

    - chemicals (object): Chemicals is the BioSTEAM object that can be created
    using the ChemManager class in Multimodelling. 

    """
    def __init__(self, streams: list = None, chemicals: object = None):
        """
        """
        # Check if the streams have been provided
        if streams is None:
            raise ValueError("At least one stream must be provided")
        self.streams = streams
        
        # Check if the Chemicals object has been provided
        if chemicals is None:
            raise ValueError("The Chemicals (BioSTEAM) object must be provided")
        self.chemicals = chemicals.IDs
    
    def mass_report(self, excelreport: bool = False, excelname: str = "Mass_Balance_Report.xlsx"):
        """
        """
        # Create a dict for inserting the stream data
        Streams_Dict = {}
        
        # Insert the mass flow of each chemical into the dict
        for stream in self.streams:
            Streams_Dict[stream.ID] = stream.mass
        
        # Create the pandas Dataframe
        pd.set_option('display.max_columns', None)
        pd.set_option('display.float_format', '{:.2f}'.format)
        Mass_df = pd.DataFrame(Streams_Dict, index = self.chemicals)
        Mass_df.index.name = "kg/hr"
        print("")
        print("--------------------------------------------------------------------------------------------------")
        print("                             MASS REPORT OF THE PROCESS                                           ")
        print("--------------------------------------------------------------------------------------------------")
        print(Mass_df)

        # Create an excel file with the mass balance
        if excelreport is True:
            Mass_df.to_excel(excelname, header = True, index = True)
            
        return Mass_df
    
    def compare_report(self):           #TODO Add a method to compare diferent reports. Do not know if this should be a class method, a diferent class 
        pass                            # or simply a function