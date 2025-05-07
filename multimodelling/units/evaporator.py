import biosteam as bst

@bst.decorators.cost()
class MultiEffectEvaporator_Small(bst.MultiEffectEvaporator):
    """

    This class is basically the same from BioSTEAM with changes in the
    cost correlation.

    This multi-effect evaporator is a subclass of the evaporator from
    BioSTEAM, but the cost correlations have been updated for situations
    where the design parameters are out of bonds.

    Parameters
    ----------

    ins :
        Inlet.

    outs :

        [0] Solid-rich stream.
        [1] Condensate stream.

    P : tuple[float] 
        Pressures describing each evaporator (Pa).

    V : float 
        Molar fraction evaporated as specified in V_definition (either overall or in the first effect).

    V_definition : str, optional
        'Overall' - V is the overall molar fraction evaporated.
        'First-effect' - V is the molar fraction evaporated in the first effect.

    """
    pass