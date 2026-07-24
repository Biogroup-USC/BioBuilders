import biosteam as bst

__all__ = (
    'NaturalGasBoiler',
)

class NaturalGasBoiler(bst.Facility): 
    """
    """
    ticket_name = 'B'
    network_priority = 1

    _N_ins = 3
    _N_outs = 4

    _units = {
        'Steam duty': 'kJ/hr',
        'Steam generated': 'kmol/hr',
        'Heat losses in flue gas': 'kJ/hr',
    }

    def __init__(
        self, 
        ID='', 
        ins=None, 
        outs=(), 
        thermo=None,
        agent = None,
        other_agents = None,
        excess_air: float = 0.20,
        boiler_efficiency: float = 0.85,
        natural_gas_price: float | None = None,
        flue_gas_P: float = 101325
    ):  
        bst.Facility.__init__(self, ID, ins, outs, thermo)
        self.excess_air = excess_air
        self.boiler_efficiency = boiler_efficiency

        self.agent = agent  = agent or bst.settings.get_heating_agent('low_pressure_steam')
        self.other_agents = [i for i in bst.settings.heating_agents if i is not agent] if other_agents is None else other_agents
        self.steam_utilities = []

        self.define_utility('Natural gas', self.natural_gas)
        if natural_gas_price is not None:
            self.natural_gas_price = natural_gas_price

        self.flue_gas_P = flue_gas_P

        self._base_cost = None
        self._base_steam_flow = None
        self._base_n_cost = None
        self._base_CE = None

    @property
    def natural_gas(self):
        """Natural gas calculated by the facility"""
        return self.ins[0]

    @property
    def natural_gas_price(self):
        """Price of natural gas [USD/kg]"""
        return bst.stream_utility_prices['Natural gas']

    @natural_gas_price.setter
    def natural_gas_price(self, new_price):
        bst.stream_utility_prices['Natural gas'] = new_price

    @property
    def combustion_air(self):
        """Combustion air calculated by the facility"""
        return self.ins[1]

    @property
    def flue_gas(self):
        """Flue gas outlet"""
        return self.outs[0]

    def _run(self):
        """Facilities are evaluated after process simulation"""
        pass

    def _load_steam_utilities(self):
        """Collect HeatUtility objects supplied by this boiler"""
        steam_utilities = self.steam_utilities
        steam_utilities.clear()

        agent = self.agent
        units = self.other_units
        for agent in (*self.other_agents, agent):
            ID = agent.ID
            for u in units:
                for hu in u.heat_utilities:
                    agent = hu.agent
                    if agent and agent.ID == ID:
                        steam_utilities.append(hu)

    def _solve_combustion(self, Q_required):
        """Calculate natural gas, combustion air and flue gas."""
        natural_gas = self.natural_gas
        combustion_air = self.combustion_air
        flue_gas = self.flue_gas

        # Natural gas energy required
        Q_natural_gas = (Q_required / self.boiler_efficiency)

        LHV = self.chemicals.CH4.LHV

        n_CH4 = Q_natural_gas / LHV

        # CH4 + 2 O2 -> CO2 + 2 H2O
        n_O2_stoich = 2. * n_CH4

        n_O2_in = n_O2_stoich * (1. + self.excess_air)

        n_O2_excess = n_O2_in - n_O2_stoich

        n_N2_in = n_O2_in * 0.79 / 0.21

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
        combustion_air.P = 101325.0

        combustion_air.imol['O2'] = n_O2_in
        combustion_air.imol['N2'] = n_N2_in

        # Flue gas
        flue_gas.empty()

        flue_gas.phase = 'g'
        flue_gas.T = 298.15
        flue_gas.P = self.flue_gas_P

        flue_gas.imol['CO2'] = n_CH4
        flue_gas.imol['Water'] = 2. * n_CH4
        flue_gas.imol['O2'] = n_O2_excess
        flue_gas.imol['N2'] = n_N2_in

        # Boiler efficiency represents all non-useful energy
        # which is assigned to the flue gas
        Q_loss = Q_natural_gas - Q_required
        flue_gas.H += Q_loss

        # Store important results
        self.Q_required = Q_required
        self.Q_natural_gas = Q_natural_gas
        self.n_CH4 = n_CH4

    def _design(self):
        self._load_steam_utilities()

        steam_supply = bst.HeatUtility.sum_by_agent(self.steam_utilities)
        Q_required = sum(hu.duty for hu in steam_supply)
        steam_flow = sum(hu.flow for hu in steam_supply)

        if Q_required <= 0. or steam_flow <= 0.:
            self.natural_gas.empty()
            self.combustion_air.empty()
            self.flue_gas.empty()
            self.heat_utilities.clear()

            self.Q_required = 0.0
            self.Q_natural_gas = 0.0
            self.n_CH4 = 0.0

            design = self.design_results
            
            design['Steam duty'] = 0.0
            design['Steam generated'] = 0.0
            design['Heat losses in flue gas'] = 0.0
            return

        self._solve_combustion(Q_required)

        for hu in steam_supply:
            hu.reverse()

        self.heat_utilities = steam_supply

        design = self.design_results

        design['Steam duty'] = Q_required
        design['Steam generated'] = steam_flow
        design['Heat losses in flue gas'] = self.Q_natural_gas - self.Q_required

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 500000    # USD
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_steam_flow(self):
        """
        """
        if self._base_steam_flow is None:
            self._base_steam_flow = 2.7 # kg/s
        return self._base_steam_flow

    @base_steam_flow.setter
    def base_steam_flow(self, value):
        """
        """
        self._base_steam_flow = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.92
        return self._base_n_cost
    
    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value
    
    @property
    def base_CE(self):
        """
        """
        if self._base_CE is None:
            self._base_CE = 1000
        return self._base_CE
    
    @base_CE.setter
    def base_CE(self, value):
        """
        """
        self._base_CE = value

    def _cost(self):
        # design parameters for cost correlations
        steam_flow_kg_s = self.design_results['Steam generated'] * 18.02 / 3600

        # Baseline purchase cost
        boiler = self.base_cost * (steam_flow_kg_s/self.base_steam_flow) ** self.base_n_cost

        # Scale costs
        base_CE = self.base_CE
        current_CE = bst.CE

        updated_boiler = boiler * (current_CE / base_CE)

        self.baseline_purchase_costs['Boiler'] = updated_boiler

        # Bare module
        delivery = 0.10
        installation = 0.90
        instrumentation_control = 0.50
        piping = 0.68  
        
        self.F_BM['Boiler'] = 1 + (delivery + installation + instrumentation_control + piping)

        # Material, pressure and temperature factor
        self.F_P['Boiler'] = self.F_M['Boiler'] = self.F_D['Boiler'] = 1.0