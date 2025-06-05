import biosteam as bst
import numpy as np
from biosteam.units._flash import Evaporator
import flexsolve as flx
from thermosteam import MultiStream
from biosteam.units.design_tools import heat_transfer as ht

__all__ = (
    "MultiEffectEvaporator",
)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
## Evaporator cost
## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
Evap_Costs = {
    'Natural circulation':      # External short tube, vertical exchanger, natural circulation
        {
            'Cost': 80000,      # USD
            'n': 0.50,
            'Cap': 5,           # m2
            'bounds': (
                2, 20           # m2
        ),
            'CE': 1000  
    },
    'Forced circulation':       # External short tube, vertical exchanger forced circulation
        {
            'Cost': 1200000,    # USD
            'n': 0.74,
            'Cap': 100,         # m2
            'bounds': (
                20, 500         # m2
        ),
            'CE': 1000
    },
    'Falling film':             # Long tube, rising or falling film
        {
            'Cost': 350000,     # USD
            'n': 0.68,
            'Cap': 100,         # m2
            'bounds': (
                1, 10000        # m2
        ),
            'CE': 1000
    }
}
class MultiEffectEvaporator(bst.Unit):                                      #TODO change the cost calculation
    """
    Creates evaporatorators with pressures given by P (a list of pressures). 
    Adjusts first evaporator vapor fraction to satisfy an overall fraction
    evaporated. All evaporators after the first have zero duty. Condenses
    the vapor coming out of the last evaporator. Pumps all liquid streams
    to prevent back flow in later parts. All liquid evaporated is ultimately
    recondensed. Cost is based on required heat transfer area. Vacuum system
    is based on air leakage. Air leakage is based on volume, as given by
    residence time `tau` and flow rate to each evaporator.

    Parameters
    ----------
    ins : 
        Inlet.
    outs : 
        * [0] Solid-rich stream.
        * [1] Condensate stream.
    P : tuple[float]
        Pressures describing each evaporator (Pa).
    V : float
        Molar fraction evaporated as specified in `V_definition` 
        (either overall or in the first effect).
    V_definition : str, optional
        * 'Overall' - `V` is the overall molar fraction evaporated.
        * 'First-effect' - `V` is the molar fraction evaporated in the first effect.
        
    """
    line = 'Multi-effect evaporator'
    vacuum_system_preference = 'Liquid-ring pump'
    auxiliary_unit_names = ('condenser', 'mixer', 'vacuum_system', 'evaporators')
    _units = {'Area': 'm^2',
              'Volume': 'm^3'}
    _F_BM_default = {'Evaporators': 2.45,
                     'Vacuum system': 1.0,
                     'Condenser': 3.17}
    _N_outs = 2

    # Evaporator type
    _Type = 'Forced circulation'
    
    # Data for simmulation and costing
    _evap_data = Evap_Costs[_Type]

    @property
    def Type(self):
        """Evaporation type."""
        return self._Type
    @Type.setter
    def Type(self, evap_type):
        try:
            self._evap_data = Evap_Costs[evap_type]
        except KeyError:
            dummy = str(Evap_Costs.keys())[11:-2]
            raise ValueError(f"Type must be one of the following: {dummy}")
        self._Type = evap_type

    @property
    def V_definition(self):
        """[str] Must be one of the following:
        * 'Overall' - Defines attribute `V` as the overall molar fraction evaporated.
        * 'First-effect' - Defines attribute `V` as the molar fraction evaporated in the first effect.
        * 'First-effect duty' - Defines attribute `V` as the supplied duty over the total duty required to achived a vapor fraction of 1 at the first effect .
        """
        return self._V_definition
    @V_definition.setter
    def V_definition(self, V_definition):
        V_definition = V_definition.capitalize()
        if V_definition in ('Overall', 'First-effect', 'First-effect duty'):
            self._reload_components = True
            self._V_definition = V_definition
        else:
            raise ValueError("V_definition must be either 'Overall', 'First-effect', or 'First-effect duty'")

    def _init(self, P, V, V_definition='Overall',
              flash=True, chemical='7732-18-5'):
        self.P = P #: tuple[float] Pressures describing each evaporator (Pa).
        self.V = V #: [float] Molar fraction evaporated.
        self.V_definition = V_definition
        self.flash = flash #: [bool] Whether to perform a flash calculation to account for volatile components.
        self._V_first_effect = None
        self.chemical = chemical

        # New properties
        self._Base_Cost = None
        self._Base_Area = None
        self._Base_n_Cost = None
        self._CE_Base = None
        self._Evap_U = None
        
    def reset_cache(self, isdynamic=None):
        self._reload_components = True
        
    def _load_components(self):
        P = self.P
        self._N_evap = n = len(P) # Number of evaporators
        self.evaporators = []
        if self.flash:
            evaporator = self.auxiliary(
                'evaporators', bst.Flash,
                ins=self.ins, 
                outs=(None, self.outs[0] if n == 1 else None), P=P[0],
            )
        else:
            evaporator = self.auxiliary(
                'evaporators', Evaporator,
                ins=self.ins,
                outs=(None, self.outs[0] if n == 1 else None), P=P[0],
                chemical=self.chemical,
            )
        for i in range(1, n):
            evaporator = self.auxiliary(
                'evaporators', Evaporator, 
                # Put liquid first, then vapor side stream
                ins=(evaporator.outs[1], evaporator.outs[0]), 
                outs=(None, self.outs[0] if i == n-1 else None, None), 
                P=P[i], chemical=self.chemical,
            )
        condenser = self.auxiliary(
            'condenser', bst.HXutility, ins=evaporator.outs[0], outs=[None], V=0
        )
        self.auxiliary(
            'mixer', bst.Mixer, 
            ins=[condenser.outs[0], *[i.outs[2] for i in self.evaporators[1:]]], 
            outs=self.outs[1]
        )
        
    def _V_overall(self, V_first_effect):
        first_evaporator, *other_evaporators = self.evaporators
        V_definition = self.V_definition
        chemical = self.chemical
        feed = first_evaporator.ins[0]
        if V_definition in ('First-effect', 'Overall'):
            first_evaporator.V = V_overall = V_first_effect
        elif V_definition == 'First-effect duty':
            if isinstance(first_evaporator, bst.Flash):
                stream = feed.copy()
                stream.vle(P=first_evaporator.P, V=1)
                Hvap = stream.H - feed.H
                Q = V_first_effect * Hvap
            else:
                Hvap = first_evaporator.Hvap * first_evaporator.ins[0].imol[chemical]
                Q = V_first_effect * Hvap 
            first_evaporator.Q = Q
            
        first_evaporator._run()
        for evap in other_evaporators: evap._run()
        evaporated = self.evaporators[-1].outs[1]
        V_overall = 1. - evaporated.imol[chemical] / feed.imol[chemical]
        return V_overall
        
    def _V_overall_objective_function(self, V_first_effect):
        return self._V_overall(V_first_effect) - self.V
    
    def _run(self):
        out_wt_solids, liq = self.outs
        ins = self.ins
        if self.V == 0:
            out_wt_solids.copy_like(ins[0])
            liq.empty()
            self._reload_components = True
            return
        
        if self._reload_components:
            self._load_components()
            self._reload_components = False
        
        if self.V_definition == 'Overall':
            P = tuple(self.P)
            self.P = list(P)
            for i in range(self._N_evap - 1):
                if self._V_overall(0.) > self.V:
                    self.P.pop()
                    self._load_components()
                    self._reload_components = True
                else:
                    break
            
            self.P = P
            self._V_first_effect = flx.IQ_interpolation(self._V_overall_objective_function,
                                                        0., 1., None, None, self._V_first_effect, 
                                                        xtol=1e-9, ytol=1e-6,
                                                        checkiter=False)
            V_overall = self.V
        else: 
            V_overall = self._V_overall(self.V)
            
        evaporators = self.evaporators
        condenser = self.condenser
        mixer = self.mixer
        last_evaporator = evaporators[-1]
    
        # Condense vapor from last effector
        condenser._run()
        
        # Mix liquid streams
        liq = mixer.outs[0]
        liq.P = self.ins[0].P
        liq.mix_from(mixer.ins, conserve_phases=True)
        if self.flash:
            mixed_stream = MultiStream(None, thermo=self.thermo)
            mixed_stream.copy_flow(self.ins[0])
            mixed_stream.vle(P=last_evaporator.P, V=V_overall)
            out_wt_solids.mol = mixed_stream.imol['l']
            if liq.phase == 'l':
                liq.phase = 'l'
                liq.mol = mixed_stream.imol['g']
            else:
                H = liq.H
                liq.copy_like(mixed_stream['g'])
                liq.vle(H=H, P=self.ins[0].P)
        liq.P = out_wt_solids.P
    
    @property
    def Evap_U(self):
        """
        """
        if self._Evap_U is None:
            if self._Type == 'Forced circulation': self._Evap_U = 10731.92      # kJ/(h*m2*k)   From BioSTEAM MultiEffectEvaporator class --> Forced circulation
            elif self._Type == 'Natural circulation': self._Evap_U = 4906.02    # kJ/(h*m2*k)   From BioSTEAM MultiEffectEvaporator class --> Horizontal tube
            elif self._Type == 'Falling film': self._Evap_U = 10220.87          # kJ/(h*m2*k)   From BioSTEAM MultiEffectEvaporator class --> Falling film
            else: self._Evap_U = 8176.70                                        # kJ/(h*m2*k)   From BioSTEAM MultiEffectEvaporator class --> Long-tube vertical
        return self._Evap_U

    @Evap_U.setter
    def Evap_U(self, value):
        """
        """
        self._Evap_U = value

    def _design(self):
        if self.V == 0: 
            for i in self.auxiliary_units: i._setup()
            return
        
        # This functions also finds the cost
        evaporators = self.evaporators
        Design = self.design_results      
        
        first_evaporator = evaporators[0]
        if self.flash:
            duty = first_evaporator.H_out - first_evaporator.H_in
        else:
            duty = first_evaporator.design_results['Heat transfer']
        
        # Cost first evaporators
        Q = abs(duty)
        Tci = first_evaporator.ins[0].T
        Tco = first_evaporator.outs[0].T
        hu = self.create_heat_utility()
        hu(duty, Tci, Tco)
        Th = hu.inlet_utility_stream.T
        LMTD = ht.compute_LMTD(Th, Th, Tci, Tco)
        ft = 1
        A = abs(bst.design_tools.compute_heat_transfer_area(LMTD, self.Evap_U, Q, ft))
        
        # Find area and cost of evaporators
        As = [A]
        evap = evaporators[-1]
        for evap in evaporators[1:]:
            Q = evap.design_results['Heat transfer']
            if Q <= 1e-12: 
                As.append(0.)
            else:
                Tc = evap.outs[0].T
                Th = evap.outs[2].T
                LMTD = Th - Tc
                A = bst.design_tools.compute_heat_transfer_area(LMTD, self.Evap_U, Q, 1.)
                As.append(A)

        self._As = As
        Design['Area'] = A = sum(As)
        total_volume = 0
        for evap in evaporators:
            if evap.outs[0].isempty(): continue
            evap._size_flash_vessel()
            vapor_sep_design = evap.design_results
            L = vapor_sep_design['Length']
            D = vapor_sep_design['Diameter']
            R = D / 2.
            total_volume += 0.0283168466 * np.pi * L * R * R # m3
        Design['Volume'] = total_volume
    
    @property
    def Base_Cost(self):
        """
        """
        if self._Base_Cost is None:
            self._Base_Cost = self._evap_data['Cost']   # USD
        return self._Base_Cost

    @Base_Cost.setter
    def Base_Cost(self, value):
        """
        """
        self._Base_Cost = value

    @property
    def Base_Area(self):
        """
        """
        if self._Base_Area is None:
            self._Base_Area = self._evap_data['Cap']    # m2
        return self._Base_Area

    @Base_Area.setter
    def Base_Area(self, value):
        """
        """
        self._Base_Area = value

    @property
    def Base_n_Cost(self):
        """
        """
        if self._Base_n_Cost is None:
            self._Base_n_Cost = self._evap_data['n']
        return self._Base_n_Cost
    
    @Base_n_Cost.setter
    def Base_n_Cost(self, value):
        """
        """
        self._Base_n_Cost = value
    
    @property
    def CE_Base(self):
        """
        """
        if self._CE_Base is None:
            self._CE_Base = self._evap_data['CE']
        return self._CE_Base
    
    @CE_Base.setter
    def CE_Base(self, value):
        """
        """
        self._CE_Base = value

    def _cost(self):
        """
        """
        # Load the design parameters
        Area = self.design_results['Area']

        # Calculate the baseline purchase cost for the evaporators
        ## The base cost account for the evaporator, vacuum system and
        ## condenser.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Evaporators_Purchase_Cost = self.Base_Cost * (Area/self.Base_Area) ** self.Base_n_Cost
        self.baseline_purchase_costs['Evaporators'] = Evaporators_Purchase_Cost

        ## The material, pressure and temperature factor are assumed to be 1
        self.F_D['Evaporators'] = self.F_M['Evaporators'] = self.F_P['Evaporators'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.90             # Metal tanks
        Instrumentation_Control = 0.50
        Piping = 0.68                   # Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Evaporators'] = Bare_Module

        ## Scale the costs using CEPCI
        CE_Base = self.CE_Base
        self.baseline_purchase_costs['Evaporators'] *= bst.CE/CE_Base