"""
"""
import pandas as pd

__all__ = (
    "TEA_Results"
)

class TEA_Results:
    """
    """
    def __init__(self, cashflow: pd.DataFrame = None):
        """
        """
        if cashflow is not None:
            self.cashflow = cashflow
        else:
            raise ValueError("The cashflow parameter must be the pandas dataframe from TEA.get_cashflow_table().")

    def TEA_report(self, excelreport: bool = False, excelname: str = None):
        """
        """
        Filename = excelname if excelname is not None else "TEA_Report.xlsx"
        Dataframe = self.cashflow
        
        # Display the pandas dataframe
        pd.set_option('display.max_columns', None)
        pd.set_option('display.float_format', '{:.2f}'.format)
        print("")
        print("---------------------------------------------------------------------------------------------------------------------")
        print("                                             TEA REPORT OF THE PROCESS                                               ")
        print("---------------------------------------------------------------------------------------------------------------------")
        print(Dataframe)

        # Create an excel file with the TEA
        if excelreport is True:
            Dataframe.to_excel(Filename, header = True, index = True)

        return Dataframe