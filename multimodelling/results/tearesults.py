"""
"""
import pandas as pd
import biosteam as bst
from ..tea import TEA
import matplotlib.pyplot as plt
from ..mathtools.economy import updating_to_future_value

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
        Filename = excelname if excelname is not None else "TEA_Report.xlsx"
        Dataframe = self.cashflow

        if inflation is not None:
            # Get the NPV and the years
            Net_Present_Value = Dataframe.loc[:,'Net present value (NPV) [MM$]'].tolist()
            Years = Dataframe.index.tolist()

            # Update the NPV to future values
            Updated_NPV = []
            Present_Year = Years[0]
            for value, year in zip(Net_Present_Value, Years):
                # Update value to year
                Number_of_Periods = year - Present_Year
                Future_Value = updating_to_future_value(value = value, growth_rate = inflation, years = Number_of_Periods)
                # Append the future value to the Updated_NPV list
                Updated_NPV.append(Future_Value)
            
            # Add the Updated NPV column to the Dataframe of the TEA results
            Dataframe["Updated NPV ({:.2f} % inflation)[MM$]".format(inflation*100)] = Updated_NPV

            # Get the updated cumulative NPV
            Updated_Cumulative_NPV = []
            Cumulative = 0
            for value in Updated_NPV:
                Cumulative += value
                Updated_Cumulative_NPV.append(Cumulative)
            
            # Add the Updated cumulative NPV to the Dataframe of the TEA results
            Dataframe["Updated Cumulative NPV ({:.2f} % inflation)[MM$]".format(inflation*100)] = Updated_Cumulative_NPV

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
    
    def plot_NPV(self):
        """
        """
        # Get the data
        Net_Present_Values = self.cashflow['Cumulative NPV [MM$]'].tolist()
        Years = self.cashflow.index.tolist()

        # Create the plot
        plt.plot(Years, Net_Present_Values, marker = 'o', linestyle = '-', linewidth = 2)

        # Axis names
        plt.xlabel('Year')
        plt.ylabel('Net Present Value (NPV) [MM$]')

        # Title
        plt.title('Cumulative NPV over Years')

        # Show
        plt.tight_layout()
        plt.grid(True)
        plt.show()