import biosteam as bst
from .centrifuge import SolidsSeparator

class SieveBend(SolidsSeparator):
    """
    Continuous fixed inclined wedge-wire screen for coarse solids separation.

    This unit models a sieve bend as a solids separator with optional moisture
    control in the retained solids stream. The equipment is typically used for
    continuous screening, dewatering, and removal of oversize particles from
    slurry streams.

    Parameters
    ----------
    ID : str
        Unit ID.
    ins : Stream
        Feed slurry.
    outs : tuple[Stream]
        Output streams:
        * [0] Retained/oversize solids stream.
        * [1] Liquid and fine solids passing through the screen.
    split : array_like or dict
        Component splits to the retained solids stream.
    moisture_content : float, optional
        Moisture content of the retained solids stream.
    hydraulic_loading : float, optional
        Liquid loading capacity, in L/s/m2.
    solids_loading : float, optional
        Solids loading capacity, in g/s/m2.
    moisture_ID : str, optional
        ID of the moisture component. Defaults to water.
    solute_ID : tuple[str], optional
        Solutes associated with the moisture phase.
    strict_moisture_content : bool, optional
        Whether to enforce the moisture content strictly.
    """

    line = 'Sieve bend'

    _units = {
        'Liquid flow': 'L/s',
        'Solids flow': 'g/s',
        'Area by liquid loading': 'm2',
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
        solids_loading=2.5,      # g/s/m2
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

    def _design(self):
        feed = self.ins[0]
        design_results = self.design_results

        moisture_ID = getattr(self, 'moisture_ID', '7732-18-5')

        # Solids flow: all mass except moisture.
        solids_flow_kg_hr = feed.F_mass - feed.imass[moisture_ID]
        solids_flow_g_s = solids_flow_kg_hr * 1000 / 3600

        A_solids = solids_flow_g_s / self.solids_loading
        A_screen = A_solids

        design_results['Solids flow'] = solids_flow_g_s
        design_results['Area by solids loading'] = A_solids
        design_results['Screen area'] = A_screen    