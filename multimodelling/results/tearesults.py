"""
"""
import pandas as pd
import numpy as np
import biosteam as bst
from ..tea import TEA
import matplotlib.pyplot as plt
from ..mathtools.economy import build_nominal_factor
import os

__all__ = (
    "TEAresults"
)

class TEAresults:
    """
    """
    def __init__(self, cashflow: pd.DataFrame = None, TEAobject: bst.TEA | TEA = None):
        """
        """
        if cashflow is not None:
            self.cashflow = cashflow
        else:
            raise ValueError("The cashflow parameter must be the pandas dataframe from TEA.get_cashflow_table().")
        if TEAobject is not None:
            self.TEA = TEAobject
        else:
            raise ValueError("The TEA object must be a TEA object either from BiosTEAM or Multimodelling.")

    def TEA_report(self, excelreport: bool = False, excelname: str = None, inflation: float = None):
        """
        """
        filename = excelname or "TEA_Report.xlsx"
        df = self.cashflow.copy()

        # Display the pandas dataframe
        pd.set_option('display.max_columns', None)
        pd.set_option('display.float_format', '{:.2f}'.format)
        print("")
        print("---------------------------------------------------------------------------------------------------------------------")
        print("                                             TEA REPORT OF THE PROCESS                                               ")
        print("---------------------------------------------------------------------------------------------------------------------")
        print(df)

        # Create an excel file with the TEA
        if excelreport is True:
            df.to_excel(filename, header = True, index = True)

        return df
    
    def solve_price(self, stream: bst.Stream = None):
        """
        """
        Price = self.TEA.solve_price(streams = stream)

        #Print the price
        print("")
        print("PRICE SOLVED:")
        print("The price of {} must be {:.2f} USD/kg to achieve the break even point.".format(stream.ID, Price))
        print("")

        # Return the price
        return Price
    
    def solve_IRR(self):
        """
        """
        Internal_Return_Rate = self.TEA.solve_IRR()

        # Print the IRR
        print("")
        print("IRR SOLVED:")
        print("The IRR of {} must be {:.2f} to achieve the break even point.".format(self.TEA.system.ID,Internal_Return_Rate))
        print("")

        # Return the IRR
        return Internal_Return_Rate
    
    def ROI(self):
        """
        """
        Return_On_Investment = self.TEA.ROI

        # Print the ROI
        print("")
        print("Return on investments (ROI):")
        print("The ROI of {} is {:.2f}.".format(self.TEA.system.ID,Return_On_Investment))
        print("")

        # Return the ROI
        return Return_On_Investment
    
    def production_costs(self, streams: list[bst.Stream] = None, depreciation: bool = True):
        """
        """
        Production_Costs = self.TEA.production_costs(streams, depreciation)

        # Print the production costs
        for stream in streams:
            Index = streams.index(stream)
            print("")
            print("Production costs:")
            print("The production costs of {} are {:.2f} USD/Year.".format(stream.ID, Production_Costs[Index]))
            print("")

        # Return the production costs
        return Production_Costs        
    
    def plot_NPV(self, path: str, show_plot: bool = False):
        """
        """
        # Get the data
        Net_Present_Values = self.cashflow['Cumulative NPV [MM$]'].tolist()
        Years = self.cashflow.index.tolist()

        # Create the plot
        fig, ax = plt.subplots(figsize = (8,6))
        ax.plot(Years, Net_Present_Values, marker = 'o', linestyle = '-', linewidth = 2)

        # Axis names
        ax.set_xlabel('Year')
        ax.set_ylabel('Net Present Value (NPV) [MM$]')
        
        # Title
        ax.set_title('Cumulative NPV over Years')

        # show
        if show_plot is True:
            plt.show()
        
        # Save the figure
        if path is not None:
            file_path = os.path.join(path, 'NPV_over_Year.png')
            fig.savefig(file_path)
            plt.close(fig)