import biosteam as bst

class NaturalGasBoiler(bst.Unit): 
    """
    """
    _N_ins = 3
    _N_outs = 2

    def _init(
        self,
        excess_air: float = 0.20,
        hot_fluid_T: float = 273.15 + 60.0,
        thermal_efficiency: float = 0.85,
    ):
        """
        """
        self.excess_air = excess_air
        self.hot_fluid_T = hot_fluid_T
        self.thermal_efficiency = thermal_efficiency

    def _run(self):
        
        natural_gas, combustion_air, cold_fluid = self.ins
        flue_gas, hot_fluid = self.outs

        # Calculate required duty
        hot_fluid.copy_like(cold_fluid)
        hot_fluid.T = self.hot_fluid_T

        Q_required = hot_fluid.H - cold_fluid.H
        
    