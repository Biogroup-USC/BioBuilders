"""
"""
import pandas as pd
import numpy as np
import biosteam as bst
from ..tea import TEA
import matplotlib.pyplot as plt
import os

__all__ = (
    "ResultsTEA"
)

class ResultsTEA:
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

    def TEA_report(self, excelreport: bool = False, excelname: str = None):
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
    
    def CAPEX_related_to_plant_capacity(
            self,
            input_stream: str | int = None,
            output_stream: str | int = None,
            units: str = "ton",
            display: bool = True
    ):
        """
        """
        # Check one stream is provided
        if (input_stream is None) == (output_stream is None):
            raise ValueError("One of the next parameters must be provided: 'input_stream' or 'output_stream'")
        
        # CAPEX
        CAPEX = self.TEA.TCI
        
        # Stream selection
        if input_stream is not None:
            seq = self.TEA.system.ins
            key = input_stream
        else:
            seq = self.TEA.system.outs
            key = output_stream
        
        # Get the proper stream
        if isinstance(key, int):
            try:
                stream = seq[key]
            except:
                raise IndexError("Index out of range {}: {}".format('ins' if input_stream is not None else 'outs', key))
        elif isinstance(key, str):
            stream = None
            for s in seq:
                if getattr(s, "ID", None) == key:
                    stream = s
                    break
            if stream is None:
                ids = [getattr(s, "ID") for s in seq]
                raise ValueError("Stream with ID = {} could not be found. Available IDs {}".format(key, ids))
        else:
            raise TypeError("Stream must be 'str' or 'int'")
        
        # Calculate ton per year
        mass_flow_kg_hr = float(stream.F_mass)
        hours_per_year = getattr(self.TEA, "operating_hours", None)
        if hours_per_year is None:
            hours_per_year = 330 * 24

        # This method supports "kg", "ton"
        u = units.lower().strip()
        if u == "ton":
            u = "t/yr"
            capacity = mass_flow_kg_hr * hours_per_year / 1000
        elif u == "kg":
            u = "kg/yr"
            capacity = mass_flow_kg_hr * hours_per_year
        else:
            raise ValueError("Units not supported. Use: 'kg' or 'ton'")

        # display the CAPEX and Capacity
        if display:
            print("")
            print("CAPEX: {:.2f} | Capacity: {:.2f} {} [{}]".format(CAPEX, capacity, units, input_stream if input_stream is not None else output_stream))
        
        # Return CAPEX and Capacity
        return CAPEX, (capacity, u)
        
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
    
    def production_costs(self, streams: list[bst.Stream] = None, depreciation: bool = True, units: int = 0):
        """
        """
        production_costs = self.TEA.production_costs(streams, depreciation)
        if units == 0:
            for stream in streams:
                Index = streams.index(stream)
                print("")
                print("Production costs:")
                print("The production costs of {} are {:.2f} USD/Year.".format(stream.ID, production_costs[Index]))
                print("")
            return production_costs    
    
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