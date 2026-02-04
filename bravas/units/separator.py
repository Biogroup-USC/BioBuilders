import biosteam as bst

__all__ = (
    "SeparationUnit",
)

class SeparationUnit(bst.Unit):
    """

    This class represents an abstract separation for simulating
    hypothetical separations without determining the equipment
    used. 
    
    This unit does not contribute to capital (CAPEX) or operating
    cost (OPEX) calculations, since it represents a conceptual
    separation step. It is useful for assesing the preliminary
    impact of a separation on the process, such as solvent recovery
    or component distribution.

    Parameters
    ----------
    ins : tuple[bst.Stream]
        Inlet streams to the separation unit.
        * [0] feed.
    outs : tuple[bst.Stream]
        Outlet streams representing separated products.
        * [0] separated compounds.
        * [1] remnants.
    sfi : dict[str, float]
        Separation factor of each compound defined as
        kg of the compound separated per kg of compound
        in the feed. If a compound is not mentioned inside
        this dictionary, sfi is 0 by default (The compound
        goes to the stream called `remnants`).

        Example: {"Water": 0.70} --> 70% of the water goes
        to the stream called `separated`.
    operating_T : float
        Operating temperature of this unit operation. Default to 25 ºC.
    operating_P : float
        Operating pressure of this unit operation. Default to 101325 Pa.

    """
    _N_ins = 1
    _N_outs = 2

    def _init(
        self,
        sfi: dict[str, float] = None, 
        operating_T: float = None, 
        operating_P: float = None
    ):
        """
        """
        self.sfi = sfi
        self.operating_T = operating_T if operating_T is not None else (25+273.15)
        self.operating_P = operating_P if operating_P is not None else 101325
    
    def _run(self):
        """
        """
        # Define each stream
        feed, = self.ins
        separated, remnants = self.outs

        separated.copy_like(feed)
        remnants.copy_like(feed)
        
        # Apply separation factor
        for chem in feed.available_chemicals:
            ID = chem.ID
            
            # Get the separation factor
            if ID in self.sfi:
                sfi = self.sfi[ID]
            else:
                sfi = 0
            
            # solve the mass balance
            separated.imass[ID] = feed.imass[ID] * sfi
            remnants.imass[ID] = feed.imass[ID] * (1-sfi)

        # get temperature and pressure of output streams
        separated.T = self.operating_T
        separated.P = self.operating_P

        remnants.T = self.operating_T
        remnants.P = self.operating_P