import biosteam as bst

__all__ = (
    'ProcessVessel',
)

class ProcessVessel(bst.Unit):
    """
    """
    _ins_size_is_fixed = False
    _outs_size_is_fixed = False

    def _init(
        self,
        split,
        tau,
        V_cf,
        V_wf,
        kW_per_m3,
    ):
        self.split = split
        self.tau = tau
        self.V_cf = V_cf
        self.V_wf = V_wf
        self.kW_per_m3 = kW_per_m3

        self._base_cost = None
        self._base_volume = None
        self._base_n_cost = None
        self._base_CE = None
    
    def _run(self):
        ins = self.ins
        outs = self.outs

        mixture = bst.Stream()
        mixture.mix_from(ins)
        self._total_inlet_flow = mixture.F_vol

        split = self.split
        for outlet, fraction in zip(outs,split,strict=True):
            outlet.copy_like(mixture)
            outlet.mass[:] *= fraction

    def _design(self):
        design = self.design_results
        Q_in = self._total_inlet_flow
        tau = self.tau
        V_wf = self.V_wf
        V_cf = self.V_cf

        # Calculate process vessel volume accounting for
        # safety and operative margin
        V_tank = Q_in * tau * (1 + V_cf) / V_wf

        design['Tank volume'] = V_tank
        design['HRT'] = tau
        design['Total inlet flow'] = Q_in

        # utilities
        volumetric_power = self.kW_per_m3
        power = volumetric_power * V_tank
        self.add_power_utility(power)
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 17000.0   # USD
        return self._base_cost
    
    @base_cost.setter
    def base_cost(self,value):
        """
        """
        self._base_cost = value
    
    @property
    def base_volume(self):
        """
        """
        if self._base_volume is None:
            self._base_volume = 1.5     # m3
        return self._base_volume

    @base_volume.setter
    def base_volume(self,value):
        """
        """
        self._base_volume = value
    
    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.93
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
            self._base_CE = 1000.0
        return self._base_CE
    
    @base_CE.setter
    def base_CE(self, value):
        """
        """
        self._base_CE = value

    def _cost(self):
        volume = self.design_results['Tank volume']

        # process vessel
        process_vessel = self.base_cost * (volume / self.base_volume)**self.base_n_cost
        agitation_factor = 1.7
        
        self.baseline_purchase_costs['Process vessel'] = process_vessel * agitation_factor
        self.baseline_purchase_costs['Process vessel'] *= bst.CE/self.base_CE

        self.F_D["Process vessel"] = 1.
        self.F_M["Process vessel"] = 2.0
        self.F_P["Process vessel"] = 1.

        delivery = 0.10
        installation = 0.45
        instrumentation = 0.26 * (1 + delivery)
        piping = 0.17

        # Calculate F_BM equivalent for BioSTEAM method
        F =  self.F_D['Process vessel'] * self.F_M['Process vessel'] * self.F_P['Process vessel']
        F_BM_eq = 1 + (delivery + installation + instrumentation + piping) * F

        self.F_BM["Process vessel"] = F_BM_eq