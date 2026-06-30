import biosteam as bst
from ..tools.mathtools.logmean import log_mean

class NaturalGasBoiler(bst.Unit): 
    """
    """
    _N_ins = 3
    _N_outs = 2

    auxiliary_unit_names = (
        'heat_exchanger',
    )

    _units = {
        "Heat duty": "kJ/hr",
        "Heat duty kW": "kW",
        "Heat absorbed": "MW",
        "Fuel duty": "kJ/hr",
        "Methane flow": "kmol/hr",
        "Flue gas inlet temperature": "K",
        "Flue gas outlet temperature": "K",
        "Cold fluid inlet temperature": "K",
        "Hot fluid outlet temperature": "K",
        "Hot-end approach": "K",
        "Cold-end approach": "K",
        "LMTD": "K",
        "LMTD correction factor": "",
        "Overall heat transfer coefficient": "W/m2/K",
        "Convective heat transfer area": "m2",
    }

    def _init(
        self,
        excess_air: float = 0.20,
        hot_fluid_T: float = 273.15 + 60.0,
        hot_fluid_P: float = 101325,
        flue_gas_T: float = 273.15 + 260,
        thermal_efficiency: float = 0.85,
        F: float = 1.0,
        U: float = 75.0,
        flue_gas_convective_T: float = 650,
    ):
        """
        """
        self.excess_air = excess_air
        self.hot_fluid_T = hot_fluid_T
        self.hot_fluid_P = hot_fluid_P
        self.flue_gas_T = flue_gas_T
        self.flue_gas_convective_T = flue_gas_convective_T
        self.thermal_efficiency = thermal_efficiency
        self.F = F
        self.U = U

    def _run(self):
        
        natural_gas, combustion_air, cold_fluid = self.ins
        flue_gas, hot_fluid = self.outs

        # Calculate required duty
        hot_fluid.copy_like(cold_fluid)
        hot_fluid.T = self.hot_fluid_T
        hot_fluid.P = self.hot_fluid_P

        Q_required = hot_fluid.H - cold_fluid.H

        # Methane required
        Q_fuel = Q_required / self.thermal_efficiency

        LHV = self.thermo.chemicals.CH4.LHV
        n_CH4 = Q_fuel / LHV

        # Combustion stoichiometry
        n_O2_stoich = 2.0 * n_CH4
        n_CO2 = n_CH4
        n_H2O = 2.0 * n_CH4

        # Excess air
        n_O2_in = n_O2_stoich * (1.0 + self.excess_air)
        n_O2_excess = n_O2_in - n_O2_stoich

        # Dry air composition
        n_N2_in = n_O2_in * (0.79 / 0.21)

        # Natural gas stream
        natural_gas.empty()
        natural_gas.phase = 'g'
        natural_gas.T = 298.15
        natural_gas.P = 101325
        natural_gas.imol['CH4'] = n_CH4

        # Combustion air
        combustion_air.empty()
        combustion_air.phase = 'g'
        combustion_air.T = 298.15
        combustion_air.P = 101325
        combustion_air.imol['O2'] = n_O2_in
        combustion_air.imol['N2'] = n_N2_in

        # Flue gas
        flue_gas.empty()
        flue_gas.phase = 'g'
        flue_gas.T = self.flue_gas_T

        flue_gas.imol['CO2'] = n_CO2
        flue_gas.imol['H2O'] = n_H2O
        flue_gas.imol['O2'] = n_O2_excess
        flue_gas.imol['N2'] = n_N2_in

        # Store results
        self.Q_required = Q_required
    
    def _design(self):
        design = self.design_results

        Q = self.Q_required # kJ/h

        cold_fluid = self.ins[2]
        hot_fluid = self.outs[1]

        # Temperatures
        Th_in = self.flue_gas_convective_T  # K, outlet of radiant section / inlet to convective section
        Th_out = self.flue_gas_T            # K, outlet of convective section / stack
        Tc_in = cold_fluid.T                # K
        Tc_out = hot_fluid.T                # K

        dT1 = Th_in - Tc_out
        dT2 = Th_out - Tc_in

        LMTD = log_mean(dT2, dT1)
        F = self.F
        U = self.U

        U_kJ_h = U * 3.6

        A = Q / (U_kJ_h * F * LMTD)

        Q_kW = Q / 3600.0
        Q_MW = Q / 3.6e6

        design["Heat duty kW"] = Q_kW
        design["Heat absorbed"] = Q_MW

        design["Fuel duty"] = self.Q_fuel
        design["Methane flow"] = self.n_CH4

        design["Flue gas inlet temperature"] = Th_in
        design["Flue gas outlet temperature"] = Th_out
        design["Cold fluid inlet temperature"] = Tc_in
        design["Hot fluid outlet temperature"] = Tc_out

        design["Hot-end approach"] = Th_in - Tc_out
        design["Cold-end approach"] = Th_out - Tc_in

        design["LMTD"] = LMTD
        design["LMTD correction factor"] = F
        design["Overall heat transfer coefficient"] = U
        design["Convective heat transfer area"] = A