import biosteam as bst
import thermosteam as tmo
import numpy as np
import matplotlib.pyplot as plt
from math import ceil
from scipy.optimize import brentq
from thermosteam._graphics import vertical_column_graphics
from thermosteam.exceptions import InfeasibleRegion
from warnings import warn

__all__ = (
    "BinaryDistillation",
)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class Distillation(bst.Unit, isabstract=True):
    r"""
    Abstract distillation column class. The Murphree efficiency is based on the
    modified O'Connell correlation [2]_. The diameter is based on tray separation
    and flooding velocity [1]_ [3]_. Purchase costs are based on correlations
    compiled by Warren et. al. [4]_.

    Parameters
    ----------
    ins : 
        Inlet fluids to be mixed into the feed stage.
    outs : 
        * [0] Distillate
        * [1] Bottoms product
    LHK : tuple[str]
        Light and heavy keys.
    y_top : float
        Molar fraction of light key to the light and heavy keys in the
        distillate.
    x_bot : float
        Molar fraction of light key to the light and heavy keys in the bottoms
        product.
    Lr : float
        Recovery of the light key in the distillate.
    Hr : float
        Recovery of the heavy key in the bottoms product.
    k : float
        Ratio of reflux to minimum reflux.
    Rmin : float, optional
        User enforced minimum reflux ratio. If the actual minimum reflux ratio
        is more than `Rmin`, this enforced value is ignored. Defaults to 0.3.
    product_specification_format=None : "Composition" or "Recovery"
        If composition is used, `y_top` and `x_bot` must be specified.
        If recovery is used, `Lr` and `Hr` must be specified.
    P=101325 : float
        Operating pressure [Pa].
    vessel_material : str, optional
        Vessel construction material. Defaults to 'Carbon steel'.
    tray_material : str, optional
        Tray construction material. Defaults to 'Carbon steel'.
    tray_type='Sieve' : 'Sieve', 'Valve', or 'Bubble cap'
        Tray type.
    tray_spacing=450 : float
        Typically between 152 to 915 mm.
    stage_efficiency=None : 
        User enforced stage efficiency. If None, stage efficiency is
        calculated by the O'Connell correlation [2]_.
    velocity_fraction=0.8 : float
        Fraction of actual velocity to maximum velocity allowable before
        flooding.
    foaming_factor=1.0 : float
        Must be between 0 to 1.
    open_tray_area=0.1 : float
        Ratio of open area to active area of a tray.
    downcomer_area_fraction=None : float
        Enforced fraction of downcomer area to net (total) area of a tray.
        If None, estimate ratio based on Oliver's estimation [1]_.
    is_divided=False : bool
        True if the stripper and rectifier are two separate columns.

    """
    line = 'Distillation'
    auxiliary_unit_names = (
        'condenser', 'reflux_drum', 'top_split',
        'pump', 'reboiler', 'bottoms_split',
        'vacuum_system'
    )
    _auxin_index = {
        'reflux_drum': 0,
        'top_split': 0,
        'reboiler': 1,
    }
    _auxout_index = {
        'condenser': 0,
        'bottoms_split': 1,
    }
    _graphics = vertical_column_graphics
    _ins_size_is_fixed = False
    _N_ins = 1
    _N_outs = 2
    _units = {'Minimum reflux': 'Ratio',
              'Reflux': 'Ratio',
              'Rectifier height': 'ft',
              'Rectifier diameter': 'ft',
              'Rectifier wall thickness': 'in',
              'Rectifier weight': 'lb',
              'Stripper height': 'ft',
              'Stripper diameter': 'ft',
              'Stripper wall thickness': 'in',
              'Stripper weight': 'lb',
              'Height': 'ft',
              'Diameter': 'ft',
              'Wall thickness': 'in',
              'Weight': 'lb'}
    _max_agile_design = (
        'Actual stages',
        'Rectifier stages',
        'Stripper stages',
        'Rectifier height',
        'Rectifier diameter',
        'Rectifier wall thickness',
        'Rectifier weight',
        'Stripper height',
        'Stripper diameter',
        'Stripper wall thickness',
        'Stripper weight',
        'Height',
        'Diameter',
        'Wall thickness',
        'Weight',
    )
    _F_BM_default = {'Rectifier tower': 4.3,
                     'Stripper tower': 4.3,
                     'Rectifier trays': 4.3,
                     'Stripper trays': 4.3,
                     'Platform and ladders': 1.,
                     'Rectifier platform and ladders': 1.,
                     'Stripper platform and ladders': 1.,
                     'Tower': 4.3,
                     'Trays': 4.3,
                     'Vacuum system': 1.}
    
    # [dict] Bounds for results
    _bounds = {'Diameter': (3., 24.),
               'Height': (27., 170.),
               'Weight': (9000., 2.5e6)}
    
    composition_sensitive = False
    
    def _init(self, 
            LHK, k,
            P=101325, 
            Rmin=0.01,
            Lr=None,
            Hr=None,
            y_top=None,
            x_bot=None, 
            product_specification_format=None,
            vessel_material='Carbon steel',
            tray_material='Carbon steel',
            tray_type='Sieve',
            tray_spacing=450,
            stage_efficiency=None,
            velocity_fraction=0.8,
            foaming_factor=1.0,
            open_tray_area=0.1,
            downcomer_area_fraction=None,
            is_divided=False,
            vacuum_system_preference='Liquid-ring pump',
            condenser_thermo=None,
            reboiler_thermo=None,
            partial_condenser=True,
            weir_height=0.1,
        ):
        self.check_LHK = True
        
        # Operation specifications
        self.k = k
        self.P = P
        self.Rmin = Rmin
        self._partial_condenser = partial_condenser
        self._set_distillation_product_specifications(product_specification_format,
                                                      x_bot, y_top, Lr, Hr)
        
        # Construction specifications
        self.vessel_material = vessel_material
        self.tray_type = tray_type
        self.tray_material = tray_material
        self.tray_spacing = tray_spacing
        self.weir_height = weir_height
        self.stage_efficiency = stage_efficiency
        self.velocity_fraction = velocity_fraction
        self.foaming_factor = foaming_factor
        self.open_tray_area = open_tray_area
        self.downcomer_area_fraction = downcomer_area_fraction
        self.is_divided = is_divided
        self.vacuum_system_preference = vacuum_system_preference
        self._load_components(partial_condenser, condenser_thermo, reboiler_thermo)
        self.LHK = LHK
      
    def _mass_and_energy_balance_specifications(self):
        spec = self.product_specification_format
        specs = []
        if spec == 'Composition':
            self._Lr = self._Hr = None
        elif spec == 'Recovery':
            self._y_top = self._x_bot = None
        specs.append( 
            ('Partial condenser', self._partial_condenser, '-'),
        )
        if spec == 'Composition':
            specs.extend([
                ('Distillate light key fraction', 100 * self._y_top, '%'),
                ('Bottoms product heavy key fraction', 100 * self._x_bot, '%'),
            ])
        elif spec == 'Recovery':
            specs.extend([
                ('Light key recovery', 100 * self._Lr, '%'),
                ('Heavy key recovery', 100 * self._Hr, '%'),
            ])
        else:
            raise RuntimeError('invalid product specification format')
        if isinstance(self, bst.ShortcutColumn):
            return 'Shortcut column', specs
        elif isinstance(self, BinaryDistillation):
            return 'Binary distillation', specs
        else:
            raise NotImplementedError('unknown name for distillation class')
            
    def _reset_thermo(self, thermo):
        super()._reset_thermo(thermo)
        self.LHK = self._LHK
        
    def _load_components(self, partial_condenser, condenser_thermo, reboiler_thermo):
        # Setup components
        thermo = self.thermo
        
        #: [MultiStream] Overall feed to the distillation column
        self.mixed_feed = tmo.MultiStream(None, thermo=thermo)
        
        #: [HXutility] Condenser.
        if not condenser_thermo: condenser_thermo = thermo
        if partial_condenser:
            self.auxiliary(
                'condenser', bst.HXutility,
                ins='vapor',
                thermo=condenser_thermo
            )
            self.condenser.outlet.phases = ('g', 'l')
            self.auxiliary(
                'reflux_drum', bst.RefluxDrum,
                ins=self.condenser-0,
                outs=(self-0, 'condensate')
            )
            self.condensate =  self.reflux_drum-1
        else:
            self.auxiliary(
                'condenser', bst.HXutility,
                ins='vapor',
                thermo=condenser_thermo
            )
            self.auxiliary(
                'top_split', bst.MockSplitter,
                ins = self.condenser-0,
                outs=(self-0, 'condensate'),
                thermo=condenser_thermo
            )
            self.condensate = self.top_split-1
        self.condenser.inlet.phase = 'g'
        if not reboiler_thermo: reboiler_thermo = thermo
        self.auxiliary('pump', bst.Pump,
            'liquid', thermo=reboiler_thermo,
        )
        self.auxiliary('reboiler', bst.HXutility,
            self.pump-0, thermo=reboiler_thermo
        )
        self.reboiler.outs[0].phases = ('g', 'l')
        self.auxiliary('bottoms_split', bst.PhaseSplitter,
            self.reboiler-0, ('boilup', self-1), thermo=reboiler_thermo,
        )
    
    @property
    def distillate(self):
        return self.outs[0]
    @property
    def bottoms_product(self):
        return self.outs[1]
    
    @property
    def product_specification_format(self):
        return self._product_specification_format
    @product_specification_format.setter
    def product_specification_format(self, spec):
        if spec == 'Composition':
            self._Lr = self._Hr = None
        elif spec == 'Recovery':
            self._y_top = self._x_bot = None
        else:
            raise AttributeError("product specification format must be either "
                                 "'Composition' or 'Recovery'")
        self._product_specification_format = spec  
    
    @property
    def LHK(self):
        """tuple[str, str] Light and heavy keys."""
        return self._LHK
    @LHK.setter
    def LHK(self, LHK):
        # Set light non-key and heavy non-key indices
        self._LHK = LHK = tuple(LHK)
        intermediate_volatile_chemicals = []
        chemicals = self.chemicals
        LHK_chemicals = LK_chemical, HK_chemical = self.chemicals[LHK]
        Tb_light = LK_chemical.Tb
        Tb_heavy = HK_chemical.Tb
        LNK = []
        HNK = []
        gases = []
        solids = []
        for chemical in chemicals:
            ID = chemical.ID
            Tb = chemical.Tb
            if not Tb or chemical.locked_state in ('l', 's'):
                solids.append(ID)
            elif chemical.locked_state == 'g':
                gases.append(ID)
            elif Tb < Tb_light:
                LNK.append(ID)
            elif Tb > Tb_heavy:
                HNK.append(ID)
            elif chemical not in LHK_chemicals:
                intermediate_volatile_chemicals.append(chemical.ID)
        self._LNK = LNK = tuple(LNK)
        self._HNK = HNK = tuple(HNK)
        self._gases = gases = tuple(gases)
        self._solids = solids = tuple(solids)
        self._intermediate_volatile_chemicals = tuple(intermediate_volatile_chemicals)
        get_index = self.chemicals.get_index
        self._LHK_index = get_index(LHK)
        self._LNK_index = get_index(LNK)
        self._HNK_index = get_index(HNK)
        self._gases_index = get_index(gases)
        self._solids_index = get_index(solids)
    
    @property
    def Rmin(self):
        """User enforced minimum reflux ratio. If the actual minimum reflux ratio is less than `Rmin`. This enforced value is ignored."""
        return self._Rmin
    @Rmin.setter
    def Rmin(self, Rmin):
        self._Rmin = Rmin
    
    @property
    def y_top(self):
        """Light key composition of at the distillate."""
        return self._y_top
    @y_top.setter
    def y_top(self, y_top):
        assert self.product_specification_format == "Composition", (
            "product specification format must be 'Composition' "
            "to set distillate composition")
        assert 0 < y_top < 1, "light key composition in the distillate must be a fraction" 
        self._y_top = y_top
        self._y = np.array([y_top, 1-y_top])
    
    @property
    def x_bot(self):
        """Light key composition at the bottoms product."""
        return self._x_bot
    @x_bot.setter
    def x_bot(self, x_bot):
        assert self.product_specification_format == "Composition", (
            "product specification format must be 'Composition' to set bottoms "
            "product composition")
        assert 0 < x_bot < 1, "light key composition in the bottoms product must be a fraction" 
        self._x_bot = x_bot
    
    @property
    def Lr(self):
        """Light key recovery in the distillate."""
        return self._Lr
    @Lr.setter
    def Lr(self, Lr):
        assert self.product_specification_format == "Recovery", (
            "product specification format must be 'Recovery' "
            "to set light key recovery")
        assert 0 < Lr < 1, "light key recovery in the distillate must be a fraction" 
        self._Lr = Lr
    
    @property
    def Hr(self):
        """Heavy key recovery in the bottoms product."""
        return self._Hr
    @Hr.setter
    def Hr(self, Hr):
        if not self.product_specification_format == "Recovery":
            raise ValueError(
                "product specification format must be 'Recovery' "
                "to set heavy key recovery"
            )
        if not 0 < Hr < 1:
            raise ValueError(
                "heavy key recovery in the bottoms product must be a fraction" 
            )
        self._Hr = Hr
    
    @property
    def weir_height(self):
        """Weir height as a fraction tray spacing."""
        return self._WH
    @weir_height.setter
    def weir_height(self, WS):
        if not 0 < WS < 1:
            raise ValueError(
                "weir height must be a fraction" 
            )
        self._WH = WS
    
    @property
    def tray_spacing(self):
        return self._TS
    @tray_spacing.setter
    def tray_spacing(self, TS):
        """Tray spacing (225-600 mm)."""
        self._TS = TS
    
    @property
    def stage_efficiency(self):
        """Enforced user defined stage efficiency."""
        return self._E_eff
    @stage_efficiency.setter
    def stage_efficiency(self, E_eff):
        self._E_eff = E_eff
    
    @property
    def velocity_fraction(self):
        """Fraction of actual velocity to maximum velocity allowable before flooding."""
        return self._f
    @velocity_fraction.setter
    def velocity_fraction(self, f):
        self._f = f
    
    @property
    def foaming_factor(self):
        """Foaming factor (0 to 1)."""
        return self._F_F
    @foaming_factor.setter
    def foaming_factor(self, F_F):
        if not 0 <= F_F <= 1:
            raise ValueError(f"foaming_factor must be between 0 and 1, ({F_F} given).")
        self._F_F = F_F
    
    @property
    def open_tray_area(self):
        """Ratio of open area, A_h, to active area, A_a."""
        return self._A_ha
    @open_tray_area.setter
    def open_tray_area(self, A_ha):
        self._A_ha = A_ha
    
    @property
    def downcomer_area_fraction(self):
        """Enforced fraction of downcomer area to net (total) area.
        If None, the fraction is estimated based on heuristics."""
        return self._A_dn
    @downcomer_area_fraction.setter
    def downcomer_area_fraction(self, A_dn):
        self._A_dn = A_dn
    
    @property
    def tray_type(self):
        """Default 'Sieve'"""
        return self._tray_type
    @tray_type.setter
    def tray_type(self, tray_type):
        if tray_type in bst.design_tools.distillation_tray_type_factor:
            self._tray_type = tray_type
            F_D = self.F_D
            F_D['Trays'] = F_D['Stripper trays'] = F_D['Rectifier trays'] = bst.design_tools.distillation_tray_type_factor[tray_type]
        else:
            raise ValueError("tray type must be one of the following: "
                            f"{', '.join(bst.design_tools.distillation_tray_type_factor)}")
        
    @property
    def tray_material(self):
        """Default 'Carbon steel'"""
        return self._tray_material
    @tray_material.setter
    def tray_material(self, tray_material):
        if tray_material in bst.design_tools.tray_material_factor_functions:
            self._tray_material = tray_material
            self._F_TM_function = bst.design_tools.tray_material_factor_functions[tray_material]
        else:
            raise ValueError("tray material must be one of the following: "
                            f"{', '.join(bst.design_tools.tray_material_factor_functions)}")
        
    @property
    def vessel_material(self):
        """Default 'Carbon steel'"""
        return self._vessel_material
    @vessel_material.setter
    def vessel_material(self, vessel_material):
        if vessel_material in bst.design_tools.distillation_column_material_factors:
            self._vessel_material = vessel_material
            F_M = self.F_M
            F_M['Rectifier tower'] = F_M['Stripper tower'] = F_M['Tower'] = bst.design_tools.distillation_column_material_factors[vessel_material]            
        else:
            raise ValueError("vessel material must be one of the following: "
                            f"{', '.join(bst.design_tools.distillation_column_material_factors)}")
    
    @property
    def is_divided(self):
        """[bool] True if the stripper and rectifier are two separate columns."""
        return self._is_divided
    @is_divided.setter
    def is_divided(self, is_divided):
        self._is_divided = is_divided
        self.line = 'Divided Distillation Column' if is_divided else "Distillation Column"
    
    def _set_distillation_product_specifications(self,
                                                 product_specification_format,
                                                 x_bot, y_top, Lr, Hr):
        if not product_specification_format:
            if (x_bot and y_top) and not (Lr or Hr):
                product_specification_format = 'Composition'
            elif (Lr and Hr) and not (x_bot or y_top):
                product_specification_format = 'Recovery'
            else:
                raise ValueError("must specify either x_top and y_top, or Lr and Hr")
        self._product_specification_format = product_specification_format
        if product_specification_format == 'Composition':
            self.y_top = y_top
            self.x_bot = x_bot
        elif product_specification_format == 'Recovery':
            self.Lr = Lr
            self.Hr = Hr
        else:
            raise ValueError("product specification format must be either 'Composition' or 'Recovery'")
    
    def _get_y_top_and_x_bot(self):
        if self.product_specification_format == 'Composition':
            y_top = self.y_top
            x_bot = self.x_bot
        else:
            distillate, bottoms_product = self.outs
            LHK = self._LHK
            y_top, _ = distillate.get_normalized_mol(LHK)
            x_bot, _ = bottoms_product.get_normalized_mol(LHK)
        return y_top, x_bot
    
    def _check_mass_balance(self):
        distillate, bottoms_product = self.outs
        LHK = self._LHK
        LK_distillate, HK_distillate = distillate.imol[LHK]
        LK_bottoms, HK_bottoms = bottoms_product.imol[LHK]
        if self.product_specification_format == 'Composition':
            if LK_distillate < 0. or LK_bottoms < 0.:
                raise InfeasibleRegion(
                    region='light key molar fraction',
                    msg=('the molar fraction of the light key in the feed must be '
                          'between the bottoms product and distillate compositions '
                          '(i.e. z_bottoms_LK < z_feed_LK < z_distillate_LK)')
                )
            if HK_distillate < 0. or HK_bottoms < 0.:
                raise InfeasibleRegion(
                    region='heavy key molar fraction',
                    msg=('the molar fraction of the heavy key in the feed must be '
                         'between the distillate and bottoms product compositions '
                         '(i.e. z_distillate_HK < z_feed_HK < z_bottoms_HK)')
                )
        if self.check_LHK:
            intermediate_chemicals = self._intermediate_volatile_chemicals
            intermediate_flows = self.mixed_feed.imol[intermediate_chemicals]
            minflow = min(LK_distillate, HK_bottoms)
            for flow, chemical in zip(intermediate_flows, intermediate_chemicals):
                if flow > minflow:
                    raise RuntimeError(
                        "significant intermediate volatile chemical,"
                       f"'{chemical}', between light and heavy "
                       f"keys, {', '.join(LHK)}; to ignore this check, "
                        "set `<Unit>.check_LHK = False`")
    
    def _run_binary_distillation_mass_balance(self):
        # Get all important flow rates (both light and heavy keys and non-keys)
        feed = self.mixed_feed
        feed.mix_from(self.ins)
        feed.vle(H=feed.H, P=self.P)
        mol = feed.mol
        LHK_index = self._LHK_index
        LNK_index = self._LNK_index
        HNK_index = self._HNK_index
        gases_index = self._gases_index
        solids_index = self._solids_index
        intermediate_chemicals = self._intermediate_volatile_chemicals
        intemediates_index = self.chemicals.get_index(intermediate_chemicals)
        LHK_mol = mol[LHK_index]
        LNK_mol = mol[LNK_index]
        HNK_mol = mol[HNK_index]
        gases_mol = mol[gases_index]
        try:
            solids_mol = mol[solids_index]
        except:
            breakpoint()
        
        # Mass balance for non-keys
        distillate, bottoms_product = self.outs
        distillate.mol[LNK_index] = LNK_mol
        distillate.mol[gases_index] = gases_mol
        bottoms_product.mol[HNK_index] = HNK_mol
        bottoms_product.mol[solids_index] = solids_mol
        
        # Mass balance for keys
        spec = self.product_specification_format
        if spec == 'Composition':
            # Use lever rule
            light, heavy = LHK_mol
            F_mol_LHK = light + heavy
            zf = light / F_mol_LHK
            y_top, y_bot = self._y
            x_bot = self._x_bot
            distillate_fraction = (zf - x_bot)/(y_top - x_bot)
            if distillate_fraction < 1e-6: distillate_fraction = 1e-6
            if distillate_fraction > 1 - 1e-6: distillate_fraction = 1 - 1e-6   
            F_mol_LHK_distillate = F_mol_LHK * distillate_fraction
            distillate_LHK_mol = F_mol_LHK_distillate * self._y
            max_flows = (1 - 1e-9) * LHK_mol
            mask = distillate_LHK_mol > (1 - 1e-9) * max_flows
            distillate_LHK_mol[mask] = max_flows[mask]
        elif spec == 'Recovery':
            distillate_LHK_mol = LHK_mol * [self.Lr, (1 - self.Hr)]
        else:
            raise ValueError("invalid specification '{spec}'")
        distillate.mol[LHK_index] = distillate_LHK_mol
        bottoms_product.mol[LHK_index] = LHK_mol - distillate_LHK_mol
        distillate.mol[intemediates_index] = \
        bottoms_product.mol[intemediates_index] = mol[intemediates_index] / 2
        self._check_mass_balance()
    
    def _update_distillate_and_bottoms_temperature(self):
        distillate, bottoms_product = self.outs
        condenser_distillate = self.distillate
        reboiler_bottoms_product = self.reboiler.outs[0]['l']
        condenser_distillate.copy_like(distillate)
        reboiler_bottoms_product.copy_like(bottoms_product)
        self._boilup_bubble_point = bp = reboiler_bottoms_product.bubble_point_at_P()
        bottoms_product.T = bp.T
        if self._partial_condenser: 
            self._condenser_operation = p = condenser_distillate.dew_point_at_P()
        else:
            self._condenser_operation = p = condenser_distillate.bubble_point_at_P()
        self.condenser.T = self.condensate.T = condenser_distillate.T = distillate.T = p.T
        self.condenser.P = self.condensate.P = condenser_distillate.P = distillate.P = p.P
        
    def _setup(self):
        super()._setup()
        distillate, bottoms_product = self.outs
        self.reboiler.ins[0].P = self.condenser.ins[0].P = self.condenser.outs[0].P = self.mixed_feed.P = distillate.P = bottoms_product.P = self.P
        distillate.phase = 'g' if self._partial_condenser else 'l'
        bottoms_product.phase = 'l'

    def get_feed_quality(self):
        feed = self.mixed_feed
        data = feed.get_data()
        H_feed = feed.H
        try: dp = feed.dew_point_at_P()
        except: pass
        else: feed.T = dp.T
        feed.phase = 'g'
        H_vap = feed.H
        try: bp = feed.bubble_point_at_P()
        except: pass
        else: feed.T = bp.T
        feed.phase = 'l'
        H_liq = feed.H
        q = (H_vap - H_feed) / (H_vap - H_liq)
        feed.set_data(data)
        return q

    def _run_condenser_and_reboiler(self):
        feed = self.mixed_feed
        distillate, bottoms_product = self.outs
        condenser = self.condenser
        reboiler = self.reboiler
        R = self.design_results['Reflux']
        # Set condenser conditions
        self.distillate.mol[:] = distillate.mol
        self.F_Mol_distillate = F_mol_distillate = distillate.F_mol
        self.F_Mol_condensate = F_mol_condensate = R * F_mol_distillate
        p = self._condenser_operation
        condensate = self.condensate
        condensate.empty()
        condensate.imol[p.IDs] = p.x * F_mol_condensate
        condensate.T = p.T
        condensate.P = p.P
        condenser.outs[0].mix_from([condensate, distillate], conserve_phases=True)
        vap = condenser.ins[0]
        vap.mol = distillate.mol + condensate.mol
        T_vap = vap.dew_point_at_P().T
        if T_vap < p.T: T_vap = p.T + 0.1
        vap.T = T_vap
        vap.P = distillate.P
        if not self._partial_condenser: self.top_split.ins[0].mix_from(self.top_split.outs)
        
        # Set reboiler conditions
        reboiler.outs[0]['l'].copy_flow(bottoms_product)
        F_vap_feed = feed.imol['g'].sum()
        self.F_Mol_boilup = F_mol_boilup = (R+1)*F_mol_distillate - F_vap_feed
        bp = self._boilup_bubble_point
        boilup_flow = bp.y * F_mol_boilup
        boilup = reboiler.outs[0]['g']
        boilup.T = bp.T
        boilup.P = bp.P
        boilup.imol[bp.IDs] = boilup_flow
        liq = reboiler.ins[0]
        liq.mix_from([bottoms_product, boilup], energy_balance=False)
        liq.phase = 'l'
        liq_T = liq.bubble_point_at_P().T
        if liq_T > bp.T: liq_T = bp.T - 0.1
        liq.T = liq_T
        self.pump.ins[0].copy_like(liq)
        self.pump.simulate()
        self.bottoms_split.simulate()
        if self._partial_condenser: self.reflux_drum.simulate()
    
    def _simulate_components(self): 
        reboiler = self.reboiler
        condenser = self.condenser
        Q_condenser = condenser.outs[0].H - condenser.ins[0].H
        H_out = self.H_out
        H_in = self.H_in
        Q_overall_boiler =  H_out - H_in - Q_condenser
        Q_boiler = reboiler.outs[0].H - reboiler.ins[0].H
        if Q_boiler < Q_overall_boiler:
            liquid = reboiler.ins[0]
            H_out_boiler = reboiler.outs[0].H
            try:
                liquid.H = H_out_boiler - Q_overall_boiler
            except:
                liquid.phase = 'l'
                boiler_kwargs = dict(duty=Q_boiler)                
            else:
                boiler_kwargs = dict(duty=Q_overall_boiler)
            condenser_kwargs = dict(duty=Q_condenser)
        else:
            boiler_kwargs = dict(duty=Q_boiler)
            condenser_kwargs = dict(duty=Q_condenser)
        reboiler.simulate(
            run=False,
            design_kwargs=boiler_kwargs,
        )
        condenser.simulate(
            run=False,
            design_kwargs=condenser_kwargs,
        )
    
    def _compute_N_stages(self):
        """Return a tuple with the actual number of stages for the rectifier and the stripper."""
        feed = self.mixed_feed
        vap, liq = self.outs
        Design = self.design_results
        R = Design['Reflux']
        N_stages = Design['Theoretical stages']
        feed_stage = Design['Theoretical feed stage']
        E_eff = self.stage_efficiency
        if E_eff:
            E_rectifier = E_stripper = E_eff
        else:    
            # Calculate Murphree Efficiency for rectifying section
            condensate = self.condensate
            mu = condensate.get_property('mu', 'mPa*s')
            alpha_LHK_distillate, alpha_LHK_bottoms = self._get_relative_volatilities_LHK()
            F_mol_distillate = self.F_Mol_distillate
            L_Rmol = self.F_Mol_condensate
            V_Rmol = (R+1) * F_mol_distillate
            E_rectifier = bst.design_tools.compute_murphree_stage_efficiency(mu,
                                                            alpha_LHK_distillate,
                                                            L_Rmol, V_Rmol)
            
            # Calculate Murphree Efficiency for stripping section
            mu = liq.get_property('mu', 'mPa*s')
            V_Smol = self.F_Mol_boilup
            L_Smol = R*F_mol_distillate + feed.imol['g'].sum()
            E_stripper = bst.design_tools.compute_murphree_stage_efficiency(mu,
                                                           alpha_LHK_bottoms,
                                                           L_Smol, V_Smol)
            
        # Calculate actual number of stages
        mid_stage = feed_stage - 0.5
        N_rectifier = np.ceil(mid_stage/E_rectifier)
        N_stripper = np.ceil((N_stages-mid_stage)/E_stripper)
        return N_rectifier, N_stripper
        
    def _complete_distillation_column_design(self):
        distillate, bottoms_product = self.outs
        Design = self.design_results
        R = Design['Reflux']
        Rstages, Sstages = self._compute_N_stages()
        is_divided = self.is_divided
        TS = self._TS
        
        ### Get diameter of rectifying section based on top plate ###
        
        condensate = self.condensate
        rho_L = condensate.rho
        sigma = condensate.get_property('sigma', 'dyn/cm')
        L = condensate.F_mass
        V = L*(R+1)/R
        vap = self.condenser.ins[0]
        V_vol = vap.get_total_flow('m^3/s')
        rho_V = vap.rho
        F_LV = bst.design_tools.compute_flow_parameter(L, V, rho_V, rho_L)
        C_sbf = bst.design_tools.compute_max_capacity_parameter(TS, F_LV)
        F_F = self._F_F
        A_ha = self._A_ha
        U_f = bst.design_tools.compute_max_vapor_velocity(C_sbf, sigma, rho_L, rho_V, F_F, A_ha)
        A_dn = self._A_dn
        if A_dn is None:
           A_dn = bst.design_tools.compute_downcomer_area_fraction(F_LV)
        f = self._f
        R_diameter = bst.design_tools.compute_tower_diameter(V_vol, U_f, f, A_dn) * 3.28
        
        ### Get diameter of stripping section based on feed plate ###
        rho_L = bottoms_product.rho
        boilup = self.reboiler.outs[0]['g']
        V = boilup.F_mass
        V_vol = boilup.get_total_flow('m^3/s')
        rho_V = boilup.rho
        L = bottoms_product.F_mass # To get liquid going down
        F_LV = bst.design_tools.compute_flow_parameter(L, V, rho_V, rho_L)
        C_sbf = bst.design_tools.compute_max_capacity_parameter(TS, F_LV)
        sigma = condensate.get_property('sigma', 'dyn/cm')
        U_f = bst.design_tools.compute_max_vapor_velocity(C_sbf, sigma, rho_L, rho_V, F_F, A_ha)
        A_dn = self._A_dn
        if A_dn is None:
            A_dn = bst.design_tools.compute_downcomer_area_fraction(F_LV)
        S_diameter = bst.design_tools.compute_tower_diameter(V_vol, U_f, f, A_dn) * 3.28
        Po = self.P * 0.000145078 # to psi
        rho_M = bst.design_tools.material_densities_lb_per_in3[self.vessel_material]
        if Po < 14.68:
            warn('vacuum pressure vessel ASME codes not implemented yet; '
                 'wall thickness may be inaccurate and stiffening rings may be '
                 'required', category=RuntimeWarning)
        if is_divided:
            Design['Rectifier stages'] = Rstages
            Design['Stripper stages'] =  Sstages
            Design['Rectifier height'] = H_R = bst.design_tools.compute_tower_height(TS, Rstages-1) * 3.28
            Design['Stripper height'] = H_S = bst.design_tools.compute_tower_height(TS, Sstages-1) * 3.28
            Design['Rectifier diameter'] = R_diameter
            Design['Stripper diameter'] = S_diameter
            Design['Rectifier wall thickness'] = tv = bst.design_tools.compute_tower_wall_thickness(Po, R_diameter, H_R)
            Design['Stripper wall thickness'] = tv = bst.design_tools.compute_tower_wall_thickness(Po, S_diameter, H_S)
            Design['Rectifier weight'] = bst.design_tools.compute_tower_weight(R_diameter, H_R, tv, rho_M)
            Design['Stripper weight'] = bst.design_tools.compute_tower_weight(S_diameter, H_S, tv, rho_M)
        else:
            Design['Actual stages'] = Rstages + Sstages
            Design['Height'] = H = bst.design_tools.compute_tower_height(TS, Rstages+Sstages-2) * 3.28
            Design['Diameter'] = Di = max((R_diameter, S_diameter))
            Design['Wall thickness'] = tv = bst.design_tools.compute_tower_wall_thickness(Po, Di, H)
            Design['Weight'] = bst.design_tools.compute_tower_weight(Di, H, tv, rho_M)
        self._simulate_components()
    
    def _cost_vacuum(self, dimensions):
        P = self.P
        if not P or P > 1e5: 
            self.vacuum_system = None
        else:
            volume = 0.
            for length, diameter in dimensions:
                R = diameter * 0.5
                volume += 0.02832 * np.pi * length * R * R # m3
            self.vacuum_system = bst.VacuumSystem(
                self, self.vacuum_system_preference, vessel_volume=volume,
            )
    
    def _cost(self):
        Design = self.design_results
        Cost = self.baseline_purchase_costs
        Cost.clear() # Prevent having previous results if `is_divided` changed
        F_M = self.F_M
        if self.is_divided:
            # Number of trays assuming a partial condenser
            N_RT = Design['Rectifier stages'] - 1.
            Di_R = Design['Rectifier diameter']
            Cost['Rectifier trays'] = bst.design_tools.compute_purchase_cost_of_trays(N_RT, Di_R)
            F_M['Rectifier trays'] = self._F_TM_function(Di_R)
            N_ST = Design['Stripper stages'] - 1.
            Di_S = Design['Stripper diameter']
            Cost['Stripper trays'] = bst.design_tools.compute_purchase_cost_of_trays(N_ST, Di_S)
            F_M['Stripper trays'] = self._F_TM_function(Di_S)
            
            # Cost vessel assuming T < 800 F
            W_R = Design['Rectifier weight'] # in lb
            H_R = Design['Rectifier height'] # in ft
            Cost['Rectifier tower'] = bst.design_tools.compute_empty_tower_cost(W_R)
            Cost['Stripper platform and ladders'] = bst.design_tools.compute_plaform_ladder_cost(Di_R, H_R)
            W_S = Design['Stripper weight'] # in lb
            H_S = Design['Stripper height'] # in ft
            Cost['Stripper tower'] = bst.design_tools.compute_empty_tower_cost(W_S)
            Cost['Rectifier platform and ladders'] = bst.design_tools.compute_plaform_ladder_cost(Di_S, H_S)
            
            dimensions = [(H_R, Di_R), (H_S, Di_S)]
        else:
            # Cost trays assuming a partial condenser
            N_T = Design['Actual stages'] - 1.
            Di = Design['Diameter']
            F_M['Trays'] = self._F_TM_function(Di)
            Cost['Trays'] = bst.design_tools.compute_purchase_cost_of_trays(N_T, Di)
            
            # Cost vessel assuming T < 800 F
            W = Design['Weight'] # in lb
            H = Design['Height'] # in ft
            Cost['Tower'] = bst.design_tools.compute_empty_tower_cost(W)
            
            Cost['Platform and ladders'] = bst.design_tools.compute_plaform_ladder_cost(Di, H)
            
            dimensions = [(H, Di)]
        self._cost_vacuum(dimensions)

    equation_node_names = (
        'overall_material_balance_node', 
        'separation_material_balance_node',
        'shortcut_phenomenode',
    )
    
    def initialize_overall_material_balance_node(self):
        self.overall_material_balance_node.set_equations(
            inputs=[j for i in self.ins if (j:=i.F_node)],
            outputs=[i.F_node for i in self.outs],
        )
    
    def initialize_separation_material_balance_node(self):
        self.separation_material_balance_node.set_equations(
            outputs=[self.outs[0].F_node],
            inputs=[self.S_node, self.outs[1].F_node],
        )
        
    def initialize_shortcut_phenomenode(self):
        self.shortcut_phenomenode.set_equations(
            inputs=(
                *[i.T_node for i in self.ins], 
                *[i.F_node for i in self.outs]
            ),
            outputs=(
                self.S_node, *[i.T_node for i in self.outs]),
        )

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
class BinaryDistillation(bst.BinaryDistillation):
    """

    Create a binary distillation column that assumes all light and heavy non keys
    separate to the top and bottoms product respectively. McCabe-Thiele
    analysis is used to find both the number of stages and the reflux ratio
    given a ratio of actual reflux to minimum reflux [1]_. This assumption
    is good for both binary distillation of highly polar compounds and
    ternary distillation assuming complete separation of light non-keys
    and heavy non-keys with large differences in boiling points. Preliminary
    analysis showed that the theoretical number of stages using this method
    on Methanol/Glycerol/Water systems is off by less than +-1 stage. Other
    methods, such as the Fenske-Underwood-Gilliland method, are more suitable
    for hydrocarbons. The Murphree efficiency is based on the modified
    O'Connell correlation [2]_. The diameter is based on tray separation
    and flooding velocity [1]_ [3]_. Purchase costs are based on correlations
    compiled by Warren et. al. [4]_.

    Parameters
    ----------
    ins : 
        Inlet fluids to be mixed into the feed stage.
    outs : 
        * [0] Distillate
        * [1] Bottoms product
    LHK : tuple[str]
        Light and heavy keys.
    y_top : float
        Molar fraction of light key to the light and heavy keys in the
        distillate.
    x_bot : float
        Molar fraction of light key to the light and heavy keys in the bottoms
        product.
    Lr : float
        Recovery of the light key in the distillate.
    Hr : float
        Recovery of the heavy key in the bottoms product.
    k : float
        Ratio of reflux to minimum reflux.
    Rmin : float, optional
        User enforced minimum reflux ratio. If the actual minimum reflux ratio
        is more than `Rmin`, this enforced value is ignored. Defaults to 0.3.
    product_specification_format=None : "Composition" or "Recovery"
        If composition is used, `y_top` and `x_bot` must be specified.
        If recovery is used, `Lr` and `Hr` must be specified.
    P=101325 : float
        Operating pressure [Pa].
    vessel_material : str, optional
        Vessel construction material. Defaults to 'Carbon steel'.
    tray_material : str, optional
        Tray construction material. Defaults to 'Carbon steel'.
    tray_type='Sieve' : 'Sieve', 'Valve', or 'Bubble cap'
        Tray type.
    tray_spacing=450 : float
        Typically between 152 to 915 mm.
    stage_efficiency=None : 
        User enforced stage efficiency. If None, stage efficiency is
        calculated by the O'Connell correlation [2]_.
    velocity_fraction=0.8 : float
        Fraction of actual velocity to maximum velocity allowable before
        flooding.
    foaming_factor=1.0 : float
        Must be between 0 to 1.
    open_tray_area=0.1 : float
        Fraction of open area to active area of a tray.
    downcomer_area_fraction=None : float
        Enforced fraction of downcomer area to net (total) area of a tray.
        If None, estimate ratio based on Oliver's estimation [1]_.
    is_divided=False : bool
        True if the stripper and rectifier are two separate columns.

    """
    _cache_tolerance = np.array([50., 1e-5, 1e-6, 1e-6, 1e-2, 1e-6], float)
    _energy_variable = None
    
    @property
    def S_node(self):
        if hasattr(self, '_S_node'): return self._S_node
        self._S_node = var = bst.VariableNode(
            f"{self.node_tag}.S", lambda: getattr(self, '_distillate_recoveries', np.zeros(self.chemicals.size))
        )
        return var
    
    def _update_equilibrium_variables(self):
        feed = sum([i.mol for i in self.ins])
        top = self.outs[0].mol
        self._distillate_recoveries = (top / feed).to_array()
        return self._distillate_recoveries
    
    def _run(self):
        self._run_binary_distillation_mass_balance()
        self._update_distillate_and_bottoms_temperature()
        self._update_equilibrium_variables()

    def reset_cache(self, isdynamic=None):
        self._McCabeThiele_args = np.zeros(6)
        super().reset_cache()

    def _run_McCabeThiele(self):
        distillate, bottoms = self.outs
        chemicals = self.chemicals
        LHK = self._LHK
        LHK_index = chemicals.get_index(LHK)

        # Feed light key mol fraction
        feed = self.mixed_feed
        liq_mol = feed.imol['l']
        vap_mol = feed.imol['g']
        LHK_mol = liq_mol[LHK_index] + vap_mol[LHK_index]
        F_mol_LHK = LHK_mol.sum()
        zf = LHK_mol[0]/F_mol_LHK
        q = self.get_feed_quality()
        
        # Main arguments
        P = self.P
        k = self.k
        y_top, x_bot = self._get_y_top_and_x_bot()
        
        # Cache
        args = np.array([P, k, y_top, x_bot, q, zf], float)
        if hasattr(self, '_McCabeThiele_args') and (abs(self._McCabeThiele_args - args) < self._cache_tolerance).all(): return
        self._McCabeThiele_args = args
        
        # Get R_min and the q_line 
        if abs(q - 1) < 1e-4: q = 1 - 1e-4
        q_line = lambda x: q*x/(q-1) - zf/(q-1)
        self._q_line_args = dict(q=q, zf=zf)
        
        solve_Ty = bottoms.get_bubble_point(LHK).solve_Ty
        Rmin_intersection = lambda x: q_line(x) - solve_Ty(np.array((x, 1-x)), P)[1][0]
        x_Rmin = brentq(Rmin_intersection, 0, 1)
        y_Rmin = q_line(x_Rmin)
        m = (y_Rmin-y_top)/(x_Rmin-y_top)
        Rmin = m/(1-m)
        if Rmin < self._Rmin:
            Rmin = self._Rmin
        R = k * Rmin

        # Rectifying section: Inntersects q_line with slope given by R/(R+1)
        m1 = R/(R+1)
        b1 = y_top-m1*y_top
        rs = lambda y: (y - b1)/m1 # -> x
        
        # y_m is the solution to lambda y: y - q_line(rs(y))
        self._y_m = y_m = (q*b1 + m1*zf)/(q - m1*(q-1))
        self._x_m = x_m = rs(y_m)
        
        # Stripping section: Intersects Rectifying section and q_line and beggins at bottoms liquid composition
        m2 = (x_bot-y_m)/(x_bot-x_m)
        b2 = y_m-m2*x_m
        ss = lambda y: (y-b2)/m2 # -> x        
        
        # Data for staircase
        self._x_stages = x_stages = [x_bot]
        self._y_stages = y_stages = [x_bot]
        self._T_stages = T_stages = []
        error = [None]
        try: bst.units.distillation.compute_stages_McCabeThiele(P, ss, x_stages, y_stages, T_stages, x_m, solve_Ty)
        except RuntimeError as e: error[0] = e
        yi = y_stages[-1]
        xi = rs(yi)
        x_stages[-1] = xi if xi < 1 else 0.99999
        try: bst.units.distillation.compute_stages_McCabeThiele(P, rs, x_stages, y_stages, T_stages, y_top, solve_Ty)
        except RuntimeError as e: error[0] = e
        
        # Find feed stage
        N_stages = len(x_stages)
        feed_stage = ceil(N_stages/2)
        for i in range(len(y_stages)-1):
            if y_stages[i] < y_m < y_stages[i+1]:
                feed_stage = i+1
        
        # Results
        Design = self.design_results
        if error[0] is None:
            Design['Theoretical feed stage'] = N_stages - feed_stage
            Design['Theoretical stages'] = N_stages
        else:
            Design['Theoretical feed stage'] = '?'
            Design['Theoretical stages'] = '100+'
            Design['Minimum reflux'] = Rmin
            Design['Reflux'] = R 
            y_stages = np.array(y_stages)
            x_stages = np.array(x_stages)
            mask = (x_stages >= 0)  & (x_stages <= 1) & (y_stages >= 0)  & (y_stages <= 1)
            self._y_stages = y_stages[mask]
            self._x_stages = x_stages[mask]
            self._T_stages = np.array(T_stages)[mask[:len(T_stages)]]
            raise error[0] from None
        Design['Minimum reflux'] = Rmin
        Design['Reflux'] = R 
        
    def _get_relative_volatilities_LHK(self):
        x_stages = self._x_stages
        y_stages = self._y_stages
        
        K_light = y_stages[-1]/x_stages[-1] 
        K_heavy = (1-y_stages[-1])/(1-x_stages[-1])
        alpha_LHK_distillate = K_light/K_heavy
        
        K_light = y_stages[0]/x_stages[0] 
        K_heavy = (1-y_stages[0])/(1-x_stages[0] )
        alpha_LHK_bottoms = K_light/K_heavy
        
        return alpha_LHK_distillate, alpha_LHK_bottoms
        
    def _design(self):
        self._run_McCabeThiele()
        self._run_condenser_and_reboiler()
        self._complete_distillation_column_design()
       
    def _plot_stages(self):
        """Plot stages, graphical aid line, and equilibrium curve. The plot does not include operating lines nor a legend."""
        vap, liq = self.outs
        if not hasattr(self, '_x_stages'):
            raise RuntimeError('cannot plot stages without running McCabe Thiele binary distillation')
        x_stages = self._x_stages
        y_stages = self._y_stages
        LHK = self.LHK
        LK = self.LHK[0]
        P = self.P
        
        # Equilibrium data
        x_eq = np.linspace(0, 1, 100)
        y_eq = np.zeros(100)
        T = np.zeros(100)
        n = 0
        
        bp = vap.get_bubble_point(IDs=LHK)
        solve_Ty = bp.solve_Ty
        for xi in x_eq:
            T[n], y = solve_Ty(np.array([xi, 1-xi]), P)
            y_eq[n] = y[0]
            n += 1
            
        # Set-up graph
        plt.figure()
        plt.xticks(np.arange(0, 1.1, 0.1), fontsize=12)
        plt.yticks(fontsize=12)
        plt.xlabel('x (' + LK + ')', fontsize=16)
        plt.ylabel('y (' + LK + ')', fontsize=16)
        plt.xlim([0, 1])
        
        # Plot stages
        x_stairs = []
        for x in x_stages:
            x_stairs.append(x)
            x_stairs.append(x)
            
        y_stairs = []
        for y in y_stages:
            y_stairs.append(y)
            y_stairs.append(y)
        try:
            x_stairs.pop(-1)
            x_stairs.insert(0, y_stairs[0])
        except:
            pass
        plt.plot(x_stairs, y_stairs, '--')
        
        # Graphical aid line
        plt.plot([0, 1], [0, 1])
        
        # Vapor equilibrium graph
        plt.plot(x_eq, y_eq, lw=2)
    
    def plot_stages(self):
        """Plot the McCabe Thiele Diagram."""
        # Plot stages, graphical aid and equilibrium curve
        self._plot_stages()
        vap, liq = self.outs
        Design = self.design_results
        if not hasattr(self, '_x_stages'): self._design()
        q_args = self._q_line_args
        zf = q_args['zf']
        q = q_args['q']
        q_line = lambda x: q*x/(q-1) - zf/(q-1)
        y_top, x_bot = self._get_y_top_and_x_bot()
        stages = Design['Theoretical stages']
        Rmin = Design['Minimum reflux']
        R = Design['Reflux']
        feed_stage = Design['Theoretical feed stage']
        
        # q_line
        intersect2 = lambda x: x - q_line(x)
        x_m2 = brentq(intersect2, 0, 1)
        
        # Graph q-line, Rectifying and Stripping section
        plt.plot([self._x_m, x_m2], [self._y_m, x_m2])
        plt.plot([self._x_m, y_top], [self._y_m, y_top])
        plt.plot([x_bot, self._x_m], [x_bot, self._y_m])
        plt.legend([f'Stages: {stages}, Feed: {feed_stage}', 'Graphical aid', 'eq-line', 'q-line', 'ROL', 'SOL'], fontsize=12)
        plt.title(f'McCabe Thiele Diagram (Rmin = {Rmin:.2f}, R = {R:.2f})')
        plt.show()
        return plt
    
    # def _update_net_flow_parameters(self):
    #     top, bottom = self.outs
    #     phi = sep.partition(
    #         self.ins[0], top, bottom, top.chemicals.IDs, self.K, 0.5, 
    #         None, None, True,
    #     )
    #     if phi == 1: 
    #         B = np.inf
    #     else:
    #         B = phi / (1 - phi)
    #     self.B = B 
    #     if self.product_specification_format == 'Recovery':
    #         LK, HK = self._LHK_index
    #         Lr = self._Lr
    #         Hr = self._Hr
    #         self.K[LK] = Lr / ((1 - Lr) * B)
    #         self.K[HK] = (1 - Hr) / (Hr * B)

    def _create_material_balance_equations(self, composition_sensitive):
        split = self._distillate_recoveries
        IDs = self.chemicals.IDs
        if hasattr(self, '_vle_chemicals'): 
            IDs_vle = tuple([i.ID for i in self._vle_chemicals])
            if IDs != IDs_vle: split = self.chemicals.array(IDs_vle, split)
        fresh_inlets, process_inlets, equations = self._begin_equations(composition_sensitive)
        top, bottom = self.outs
        ones = np.ones(self.chemicals.size)
        minus_ones = -ones
        zeros = np.zeros(self.chemicals.size)
        
        # Overall flows
        eq_overall = {}
        for i in self.outs: 
            eq_overall[i] = ones
        for i in process_inlets:
            if i in eq_overall: del eq_overall[i]
            else: eq_overall[i] = minus_ones
        equations.append(
            (eq_overall, sum([i.mol for i in fresh_inlets], zeros))
        )
        
        # Top and bottom flows
        eq_outs = {}
        minus_split = -split
        for i in process_inlets: eq_outs[i] = minus_split
        rhs = split * sum([i.mol for i in fresh_inlets], zeros)
        eq_outs[top] = ones
        equations.append(
            (eq_outs, rhs)
        )
        return equations
    
    def _get_energy_departure_coefficient(self, stream):
        return None
    
    def _create_energy_departure_equations(self):
        return []
    
    def _update_nonlinearities(self):
        outs = self.outs
        data = [i.get_data() for i in outs]
        self._run()
        for i, j in zip(outs, data): i.set_data(j)