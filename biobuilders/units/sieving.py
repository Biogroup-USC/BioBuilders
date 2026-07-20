import biosteam as bst
from .centrifuge import SolidsSeparator

__all__ = (
    'SieveBend',
    'VibratingScreen',
)

class SieveBend(SolidsSeparator):
    """
    Continuous fixed inclined wedge-wire screen for coarse solids separation.

    This unit models a sieve bend as a solid-liquid separator used for
    continuous screening and dewatering of slurry streams. Separation is defined
    by component-wise split fractions to the retained oversize stream. If a
    target moisture content is provided, the moisture in the retained solids
    stream is adjusted using the inherited ``SolidsSeparator`` moisture-control
    routine.

    The screen area is estimated from the solids loading capacity:

        A = m_solids / L_solids

    where ``A`` is the screen area [m2], ``m_solids`` is the dry solids flow
    [g/s], and ``L_solids`` is the solids loading capacity [g/s/m2].

    Parameters
    ----------
    ID : str
        Unit operation ID.
    ins : Stream
        Feed slurry.
    outs : tuple[Stream]
        Output streams:

        * [0] Retained oversize solids stream.
        * [1] Liquid and fine solids passing through the screen.

    split : array_like or dict
        Component split fractions to the retained oversize stream.
    order : sequence[str], optional
        Chemical order used to define split values when ``split`` is array-like.
    moisture_content : float, optional
        Target moisture content of the retained oversize stream.
    moisture_ID : str, optional
        ID of the moisture component. Defaults to water if not provided by the
        inherited ``SolidsSeparator``.
    solute_ID : str or tuple[str], optional
        Solute IDs associated with the moisture phase when enforcing moisture
        content.
    strict_moisture_content : bool, optional
        Whether to strictly enforce the specified moisture content.
    solids_loading : float, optional
        Solids loading capacity of the screen [g/s/m2]. Default is 2.5 g/s/m2.

    Attributes
    ----------
    base_cost : float
        Reference purchase cost of the sieve bend [USD].
    base_n_cost : float
        Cost scaling exponent.
    base_area : float
        Reference screen area used for cost scaling [m2].
    CE_base : float
        Chemical Engineering Plant Cost Index used for the reference cost.

    """

    _units = {
        'Solids flow': 'kg/hr',
        'Area by solids loading': 'm2',
        'Screen area': 'm2',
    }

    def _init(
        self,
        split,
        order=None,
        moisture_content=None,
        moisture_ID=None,
        solute_ID=None,
        strict_moisture_content=None,
        solids_loading=3.5*3600,
        solid_IDs=None,

    ):
        super()._init(
            split=split,
            order=order,
            moisture_content=moisture_content,
            moisture_ID=moisture_ID,
            solute_ID=solute_ID,
            strict_moisture_content=strict_moisture_content,
        )

        self.solids_loading = solids_loading
        

        if solid_IDs is None:
            raise ValueError("Solid_IDs must contain at least one solid component.")
        
        if isinstance(solid_IDs, str):
            solid_IDs = (solid_IDs,)
        else:
            solid_IDs = tuple(solid_IDs)
        
        self.solid_IDs = solid_IDs
        
        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._CE_base = None

    def _design(self):
        feed = self.ins[0]
        design_results = self.design_results

        # Solids flow: all mass except moisture.
        solids_flow_kg_hr = feed.imass[self.solid_IDs].sum()

        A_solids = solids_flow_kg_hr / self.solids_loading
        A_screen = A_solids

        design_results['Solids flow'] = solids_flow_kg_hr
        design_results['Area by solids loading'] = A_solids
        design_results['Screen area'] = A_screen

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 45000 # USD
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.62
        return self._base_n_cost

    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            self._base_area = 1.5   # m2
        return self._base_area

    @base_area.setter
    def base_area(self, value):
        """
        """
        self._base_area = value

    @property
    def CE_base(self):
        """
        """
        if self._CE_base is None:
            self._CE_base = 1000
        return self._CE_base

    @CE_base.setter
    def CE_base(self, value):
        """
        """
        self._CE_base = value

    def _cost(self):
        """
        """
        # Load all the design parameters needed to calculate the costs
        area = self.design_results["Screen area"]

        # Calculate the baseline purchase cost for Screen, vibrating.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        sieve_bend_cost = self.base_cost * (area/self.base_area)**self.base_n_cost
        self.baseline_purchase_costs['Sieve bend'] = sieve_bend_cost

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Sieve bend'] = self.F_M['Sieve bend'] = self.F_P['Sieve bend'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        delivery = 0.10
        installation = 0.80             # Filters
        instrumentation_Control = 0.50
        piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        bare_module = (1 + (delivery + installation + instrumentation_Control + piping))
        self.F_BM['Sieve bend'] = bare_module

        ## Scale the costs using CEPCI
        ce_factor = bst.CE/self.CE_base
        self.baseline_purchase_costs['Sieve bend'] = self.baseline_purchase_costs['Sieve bend'] * ce_factor

class VibratingScreen(SieveBend):
    """
    """

    _units = {
        'Solids flow': 'g/s',
        'Area by solids loading': 'm2',
        'Screen area': 'm2',
        'Specific energy': 'kWh/kg'
    }

    def _init(
        self, 
        split, 
        order=None, 
        moisture_content=None, 
        moisture_ID=None, 
        solute_ID=None, 
        strict_moisture_content=None, 
        solids_loading=3.5*3600,
        solid_IDs=None,
    ):
        super()._init(
            split, order, moisture_content, moisture_ID, solute_ID, 
            strict_moisture_content, solids_loading, solid_IDs
        )
    
        self._specific_energy = None

    @property
    def specific_energy(self):
        if self._specific_energy is None:
            self._specific_energy = 0.0055
        return self._specific_energy
    
    @specific_energy.setter
    def specific_energy(self, value):
        self._specific_energy = value

    def _design(self):
        feed = self.ins[0]
        design_results = self.design_results

        # Solids flow: all mass except moisture.
        solids_flow_kg_hr = feed.imass[self.solid_IDs].sum()

        A_solids = solids_flow_kg_hr / self.solids_loading
        A_screen = A_solids

        # power utilities
        power = solids_flow_kg_hr * self.specific_energy
        self.add_power_utility(power)

        design_results['Solids flow'] = solids_flow_kg_hr
        design_results['Area by solids loading'] = A_solids
        design_results['Screen area'] = A_screen
        design_results['Specific power'] = self.specific_energy
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 45000 # USD
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.62
        return self._base_n_cost

    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            self._base_area = 1.5   # m2
        return self._base_area

    @base_area.setter
    def base_area(self, value):
        """
        """
        self._base_area = value

    @property
    def CE_base(self):
        """
        """
        if self._CE_base is None:
            self._CE_base = 1000
        return self._CE_base

    @CE_base.setter
    def CE_base(self, value):
        """
        """
        self._CE_base = value