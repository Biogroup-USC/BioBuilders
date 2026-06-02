"""
"""
import pandas as pd
import numpy as np
import biosteam as bst
from ..tea import TEA
from ..tools.diagramtools import simplify_labels, filename_to_save
import matplotlib.pyplot as plt
import os
from typing import Literal

__all__ = (
    "ResultsTEA",
)

class ResultsTEA:
    """
    """
    def __init__(self, cashflow: pd.DataFrame = None, TEAobject: TEA  = None):
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

        # Properties
        self._conversion_dollars_euros = None

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
            print("CAPEX: {:.2f} | Capacity: {:.2f} {} [{}]".format(CAPEX, capacity, u, input_stream if input_stream is not None else output_stream))
        
        # Return CAPEX and Capacity
        return CAPEX, (capacity, u)
        
    def solve_price(self, stream: bst.Stream = None):
        """
        """
        Price = self.TEA.solve_price(streams = stream,)

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
        operating_hours = self.TEA.operating_hours
        if units == 0:
            for stream in streams:
                idx = streams.index(stream)
                print("")
                print("Production costs:")
                print("The production costs of {} are {:.2f} USD/Year.".format(stream.ID, production_costs[idx]))
                print("")
            return production_costs    
        if units == 1:
            production_kg_per_year = {}
            production_costs_per_kg = {}
            for stream in streams:
                idx = streams.index(stream)
                production_kg_per_year[stream.ID] = stream.F_mass * operating_hours
                production_costs_per_kg[stream.ID] = production_costs[idx]/(production_kg_per_year[stream.ID])
                print("")
                print("Production costs:")
                print("The production costs of {} [{:.2f} kg/yr] are {:.2f} USD/kg ".format(stream.ID, production_kg_per_year[stream.ID], production_costs_per_kg[stream.ID]))
                print("")
            return production_costs_per_kg, production_kg_per_year

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
    
    @staticmethod
    def _create_production_costs_dict(tea: bst.TEA = None):
        """
        """
        if tea is None: raise ValueError("BioSTEAM TEA object must be provided")
        
        # Get TEA object
        system = tea.system

        # Get operating hours
        operating_hours = tea.operating_hours

        # Get production costs individually
        labour = tea.labor_cost
        
        maintenance = tea.FCI * tea.maintenance
        property_tax = tea.FCI * tea.property_tax
        property_insurance = tea.FCI * tea.property_insurance
        supplies = tea.FCI * tea.maintenance * tea.supplies
        
        power_utility = system.power_utility.cost * operating_hours

        # Get the total cost of the heat utilities used
        heat_utilities = system.heat_utilities
        heat_utilities_dict = {}
        for utility in heat_utilities:
            id = utility.agent.ID
            annual_cost = utility.cost * operating_hours
            heat_utilities_dict[id] = annual_cost
        
        # Get the cost of raw materials
        raw_materials = system.ins
        operating_hours = tea.operating_hours
        raw_materials_cost = {}
        for raw_material in raw_materials:
            flow = raw_material.F_mass
            price = raw_material.price
            annual_cost = flow * price * operating_hours
            raw_materials_cost[raw_material.ID] = annual_cost
        
        # Generate the breakdown of costs
        production_costs = {
            "FOC": {
                "Labour": labour,
                "Maintenance": maintenance,
                "Property": property_tax + property_insurance,
                "Supplies": supplies
            },
            "VOC": raw_materials_cost,
            "Heat utilities": heat_utilities_dict,
            "Power utility": power_utility
        }

        return production_costs

    @staticmethod
    def _create_bar_arrays(costs_list: list[dict] = None):
        """
        """
        if costs_list is None: raise ValueError(
            "A list of dictionaries with the costs broken down must be provided"
        )

        # Create list for every key in the dictionaries
        labour = []; maintenance = []; property_related = []; supplies = []; power = []

        # Union of keys across all scenarios
        raw_material_keys = set()
        heat_utility_keys = set()

        for costs in costs_list:
            raw_material_keys.update(costs.get("VOC",{}).keys())
            heat_utility_keys.update(costs.get("Heat utilities",{}).keys())
        
        raw_material_keys = sorted(raw_material_keys)
        heat_utility_keys = sorted(heat_utility_keys)

        raw_materials = {key: [] for key in raw_material_keys}
        heat_utilities = {key: [] for key in heat_utility_keys}

        for costs in costs_list:
            labour.append(costs["FOC"]["Labour"])
            maintenance.append(costs["FOC"]["Maintenance"])
            property_related.append(costs["FOC"]["Property"])
            supplies.append(costs["FOC"]["Supplies"])
            power.append(costs["Power utility"])
            
            for key in raw_material_keys:
                raw_materials[key].append(costs.get("VOC",{}).get(key,0.0))
            
            for key in heat_utilities.keys():
                heat_utilities[key].append(costs.get("Heat utilities",{}).get(key,0.0))
        
        # Create a dictionary with all lists as np.array
        bar_arrays = {
            "Labour": np.array(labour),
            "Maintenance": np.array(maintenance),
            "Property taxes + insurrance": np.array(property_related),
            "Supplies": np.array(supplies),
            "Power utilities": np.array(power),
        }

        # Add raw materials and heat utilities dictionaries
        for key,values in raw_materials.items():
            bar_arrays[key] = np.array(values)
        
        for key,values in heat_utilities.items():
            bar_arrays[key] = np.array(values)

        return bar_arrays

    @property
    def conversion_dollars_euros(self):
        """
        """
        if self._conversion_dollars_euros is None:
            self._conversion_dollars_euros = 0.86
        return self._conversion_dollars_euros

    @conversion_dollars_euros.setter
    def conversion_dollars_euros(self,value):
        """
        """
        self._conversion_dollars_euros = value

    @staticmethod
    def _get_stream_flow_by_id(system,stream_id):
        """
        """
        for stream in system.streams:
            if stream.ID == stream_id:
                mass_flow = stream.F_mass
            else: 
                continue
        
        return mass_flow

    def plot_production_costs_scenarios(
            self,
            base_scenario: str = "base case",
            other_scenarios: dict[str,bst.TEA] = None,
            basis: Literal['USD/kg','USD','EUR/kg','EUR'] = 'USD',
            basis_flow: dict[str,str] = None,
            title: str = "Breakdown of production costs",
            simplify_legend: dict = None,
            y_label: str = "Production costs",
            y_lim: tuple[float] = None,
#            y_breaks: list[tuple] = None,
            xlabel_font: float = 6,
            legend_font: float = 4,
            legend_title: str = 'Production costs',
            legend_title_font: float = 4,
            legend_loc: str = 'upper right',
            save_path: str = None,
            filename: str = None,
            file_extension: str = ".png",
            show: bool = True,
            width: float = 0.20
        ):
        """
        """
        simplify_legend = simplify_legend or {}
        y_breaks = None

        # Get the production cost of each case
        scenarios = []
        scenarios_costs = []
        scenarios_TEA = {base_scenario: self.TEA}
        if other_scenarios is not None:
            scenarios_TEA.update(other_scenarios)

        
        for key,value in scenarios_TEA.items():
            scenarios.append(key)
            prod_costs = self._create_production_costs_dict(value)
            scenarios_costs.append(prod_costs)
        
        # calculate the currency factor and the flow factor depending on the basis parameter
        if basis == 'USD':
            currency_factor = 1.
            flow_factor = 1.
        elif basis == 'EUR':
            currency_factor = self.conversion_dollars_euros
            flow_factor = 1.
        elif basis == 'USD/kg':
            currency_factor = 1.
            flow_factor = {}
            for case in scenarios:
                stream_id = basis_flow[case]
                operating_h = scenarios_TEA[case].operating_hours
                mass_flow = self._get_stream_flow_by_id(scenarios_TEA[case].system,stream_id) * operating_h
                flow_factor[case] = mass_flow
        elif basis == 'EUR/kg':
            currency_factor = self.conversion_dollars_euros
            flow_factor = {}
            for case in scenarios:
                stream_id = basis_flow[case]
                operating_h = scenarios_TEA[case].operating_hours
                mass_flow = self._get_stream_flow_by_id(scenarios_TEA[case].system,stream_id) * operating_h
                flow_factor[case] = mass_flow
        else:
            raise ValueError("You must provide basis for production cost calculation")

        # Build bar arrays
        bar_arrays = self._create_bar_arrays(scenarios_costs)
        x = np.arange(len(scenarios))

        # Precompute stacked values to reuse in all axes
        stacked_data = []
        bottom = np.zeros(len(scenarios),dtype=float)

        for cost, value in bar_arrays.items():
            updated_value = currency_factor * np.asarray(value, dtype=float)

            label = simplify_legend.get(cost, cost)

            if basis in ('EUR/kg','USD/kg'):
                flows = np.array([float(flow_factor[case]) for case in scenarios], dtype=float)
                if updated_value.shape != flows.shape:
                    raise ValueError(
                        f"Shape mismatch in normalisation: updated_value.shape={updated_value.shape}",
                        f"flows.shape={flows.shape}, cost={cost}, scenarios={scenarios}"
                    )
                updated_value = updated_value / flows
            
            if np.any(updated_value != 0):
                stacked_data.append({
                    "label": label,
                    "height": updated_value.copy(),
                    "bottom": bottom.copy()
                })
                bottom += updated_value
        
        totals = bottom.copy()

        if not y_breaks:
            fig, ax = plt.subplots(figsize=(6,4), layout='constrained')

            for item in stacked_data:
                ax.bar(
                    x,
                    item["height"],
                    width,
                    label=item["label"],
                    bottom=item["bottom"]
                )
            
            for element, total in enumerate(totals):
                ax.text(
                    element,
                    total,
                    f"{total:.1f}",
                    ha ='center',
                    va='bottom'
                )
            
            if y_lim is not None:
                y_limits = y_lim
            else:
                y_limits = (0.0, float(np.max(totals)) * 1.1 if len(totals) else 1.0)
            
            ax.set(ylabel=y_label + f" ({basis})", ylim=y_lim)
            ax.set_xlim(-0.5, x[-1] + 0.5)
            ax.set_title(title)
            ax.set_xticks(x)
            ax.set_xticklabels(scenarios, fontsize=xlabel_font)
            ax.legend(
                fontsize = legend_font,
                title = legend_title,
                title_fontsize = legend_title_font,
                loc = legend_loc
            )

            plt.tight_layout()

            if save_path:
                default_filename = "production_costs"
                file_path = filename_to_save(save_path, filename, default_filename, file_extension)
                fig.savefig(file_path)

            if show:
                plt.show()
            else:
                plt.close(fig)
            return
        
#        # Multi broken axis
#        if not isinstance(y_breaks, (list, tuple) or len(y_breaks)==0):
#            raise ValueError("y_breaks must be a non-empty list of (ymin,ymax) tuples")
#        
#        clean_breaks = []
#        for bk in y_breaks:
#            if not isinstance(bk,(list,tuple) or len(bk)!=2):
#                raise ValueError(f"Invalid y_break entry: {bk}. Each entry must be (ymin,ymax)")
#            ymin,ymax = bk
#            if ymax <= ymin:
#                raise ValueError(f"Invalid y_break range: {bk}. Must satisfy ymax > ymin")
#            clean_breaks.append(bk)
#        
#        # bottom-top order
#        heights = [ymax - ymin for ymin,ymax in clean_breaks]
#
#        fig, axes = plt.subplots(
#            nrows = len(clean_breaks),
#            ncols = 1,
#            sharex = True,
#            figsize = (6, max(4, 1.8 * len(clean_breaks))),
#            gridspec_kw={"height_ratios": heights, "hspace": 0.05},
#            layout = 'constrained'
#        )
#
#        if len(clean_breaks) == 1:
#            axes = [axes]
#        
#        plot_axes = axes[::-1]
#        plot_breaks = clean_breaks[::-1]
#
#        legend_handles = None
#        legend_labels = None
#
#        for ax, (ymin, ymax) in zip(plot_axes, plot_breaks):
#            for item in stacked_data:
#                container = ax.bar(
#                    x,
#                    item["height"],
#                    width,
#                    label=item["label"],
#                    bottom=item["bottom"]
#                )
#                if legend_handles is None:
#                    legend_handles, legend_labels = ax.get_legend_handles_labels()
#            
#            ax.set_ylim(ymin, ymax)
#            ax.set_xlim(-0.5,x[-1]+0.5)
#        
#        for element,total in enumerate(totals):
#            for ax, (ymin,ymax) in zip(plot_axes, plot_breaks):
#                if ymin <= total <= ymax:
#                    ax.text(
#                        element,
#                        total,
#                        f"{total:.1f}",
#                        ha="center",
#                        va="bottom",
#                        fontsize=max(5,xlabel_font)
#                    )
#                    break
#        
#        n_axes = len(axes)
#        d = 0.008
#
#        for i, ax in enumerate(axes):
#            # Label only once, on central axis if possible
#            if i == n_axes // 2:
#                ax.set_ylabel(y_label + f" ({basis})")
#
#            # Hide inner spines
#            if i != 0:
#                ax.spines['top'].set_visible(False)
#            if i != n_axes - 1:
#                ax.spines['bottom'].set_visible(False)
#
#            # Tick labels only on bottom axis
#            if i != n_axes - 1:
#                ax.tick_params(labelbottom=False, bottom=False)
#            else:
#                ax.set_xticks(x)
#                ax.set_xticklabels(scenarios, fontsize=xlabel_font)
#
#        # Draw diagonal break marks between adjacent axes
#        for i in range(n_axes - 1):
#            ax_top = axes[i]
#            ax_bottom = axes[i + 1]
#
#            kwargs_top = dict(transform=ax_top.transAxes, color='k', clip_on=False, linewidth=0.8)
#            ax_top.plot((-d, +d), (-d, +d), **kwargs_top)
#            ax_top.plot((1 - d, 1 + d), (-d, +d), **kwargs_top)
#
#            kwargs_bottom = dict(transform=ax_bottom.transAxes, color='k', clip_on=False, linewidth=0.8)
#            ax_bottom.plot((-d, +d), (1 - d, 1 + d), **kwargs_bottom)
#            ax_bottom.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs_bottom)
#
#        # Title on top axis
#        axes[0].set_title(title)
#
#        # Legend only once
#        if legend_handles is not None:
#            axes[0].legend(
#                legend_handles,
#                legend_labels,
#                fontsize=legend_font,
#                title=legend_title,
#                title_fontsize=legend_title_font,
#                loc=legend_loc
#            )
#
#        plt.tight_layout()
#
#        if save_path:
#                default_filename = "production_costs"
#                file_path = filename_to_save(save_path, filename, default_filename, file_extension)
#                fig.savefig(file_path)
#        if show:
#            plt.show()
#        else:
#            plt.close(fig)
#        return
        