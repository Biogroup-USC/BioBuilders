"""
"""
from biosteam.exceptions import InfeasibleRegion
import thermosteam as tmo
from warnings import warn

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
def mix_and_split_with_moisture_content(ins, retentate, permeate,
                                        split, moisture_content, solvent_IDs=None, solute_IDs=None,
                                        strict=None):
    """
    Run splitter mass and energy balance with mixing all input streams and 
    and ensuring retentate moisture content.
    
    Parameters
    ----------
    ins : Iterable[Stream]
        Inlet fluids with solids.
    retentate : Stream
    permeate : Stream
    split : array_like
        Component splits to the retentate.
    moisture_content : float
        Fraction of water in retentate.

    Examples
    --------
    >>> import thermosteam as tmo
    >>> Solids = tmo.Chemical('Solids', default=True, search_db=False, phase='s')
    >>> tmo.settings.set_thermo(['Water', Solids])
    >>> feed = tmo.Stream('feed', Water=100, Solids=10, units='kg/hr')
    >>> wash_water = tmo.Stream('wash_water', Water=10, units='kg/hr')
    >>> retentate = tmo.Stream('retentate')
    >>> permeate = tmo.Stream('permeate')
    >>> split = [0., 1.]
    >>> moisture_content = 0.5
    >>> tmo.separations.mix_and_split_with_moisture_content(
    ...     [feed, wash_water], retentate, permeate, split, moisture_content
    ... )
    >>> retentate.show(flow='kg/hr')
    Stream: retentate
    phase: 'l', T: 298.15 K, P: 101325 Pa
    flow (kg/hr): Water   10
                  Solids  10
    >>> permeate.show(flow='kg/hr')
    Stream: permeate
    phase: 'l', T: 298.15 K, P: 101325 Pa
    flow (kg/hr): Water  100

    """
    mix_and_split(ins, retentate, permeate, split)
    adjust_moisture_content(retentate, permeate, moisture_content, solvent_IDs, solute_IDs, strict)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
def adjust_moisture_content(retentate, permeate, moisture_content, solvent_IDs=('Water',), solute_IDs=None, strict=None,):
    """
    Remove water from permate to adjust retentate moisture content.
    
    Parameters
    ----------
    retentate : Stream
    permeate : Stream
    moisture_content : float
        Fraction of water in retentate.

    Examples
    --------
    >>> import thermosteam as tmo
    >>> Solids = tmo.Chemical('Solids', default=True, search_db=False, phase='s')
    >>> tmo.settings.set_thermo(['Water', Solids])
    >>> retentate = tmo.Stream('retentate', Solids=20, units='kg/hr')
    >>> permeate = tmo.Stream('permeate', Water=50, Solids=0.1, units='kg/hr')
    >>> moisture_content = 0.5
    >>> tmo.separations.adjust_moisture_content(retentate, permeate, moisture_content)
    >>> retentate.show(flow='kg/hr')
    Stream: retentate
    phase: 'l', T: 298.15 K, P: 101325 Pa
    flow (kg/hr): Water   20
                  Solids  20
    >>> permeate.show(flow='kg/hr')
    Stream: permeate
    phase: 'l', T: 298.15 K, P: 101325 Pa
    flow (kg/hr): Water   30
                  Solids  0.1
    
    Note that if not enough water is available, an InfeasibleRegion error is raised:
        
    >>> retentate.imol['Water'] = permeate.imol['Water'] = 0
    >>> tmo.separations.adjust_moisture_content(retentate, permeate, moisture_content)
    Traceback (most recent call last):
    InfeasibleRegion: not enough water; permeate moisture content is infeasible

    """
    # Calculate solute concentration
    if not solvent_IDs:
        raise ValueError(
            f"solvent_IDs must contain at least one chemical."
        )
    elif isinstance(solvent_IDs, str):
        solvent_IDs = (solvent_IDs,)
    else:
        solvent_IDs = tuple(solvent_IDs)

    if solute_IDs is None:
        solute_IDs = ()
    elif isinstance(solute_IDs, str):
        solute_IDs = (solute_IDs,)
    else:
        solute_IDs = tuple(solute_IDs)

    if moisture_content is None:
        raise ValueError(
            f"moisture_content must be provided. Its value should be between 0 and 1."
        )
    
    if not 0. <= moisture_content < 1.:
        raise ValueError(
            f"moisture_content must be between 0 and 1, both included."
        )
    
    # Total solvent in feed
    liquid_total = sum(permeate.imass[get_key_for(permeate, ID, 'l')] for ID in solvent_IDs)
    if liquid_total <= 0:
        if strict is None:
            strict = True
        if strict:
            raise InfeasibleRegion(
                f"not enough solvent {solvent_IDs} for the moisture_content specified."
            )
        else:
            return

    mc = moisture_content

    if solute_IDs:
        
        # Dictionary with solute concentration per kg of solvent
        solutes_conc = {}

        for solute in solute_IDs:
            permeate_solute = permeate.imass[get_key_for(permeate, solute, 'l')]
            solute_conc = permeate_solute / liquid_total  # kg solute / kg liquid (feed)
            solutes_conc[solute] = solute_conc

        solutes_total_conc = sum(solutes_conc[ID] for ID in solutes_conc.keys())
    else:
        solutes_conc = {}
        solutes_total_conc = 0.

    # solve liquid needed to satisfy moisture
    liquid_total_retentate = sum(retentate.imass[get_key_for(retentate, ID, 'l')] for ID in solvent_IDs)
    solids_retentate = retentate.F_mass - liquid_total_retentate
    mc_factor = mc/(1-mc)
    liquid_retained = (mc_factor * solids_retentate) / (1 - mc_factor * solutes_total_conc)
    liquid_transfer = liquid_retained - liquid_total_retentate

    if abs(liquid_transfer) < 1e-12:
        return

    if liquid_transfer < 0:
        warn(
            f"Retentate already has more solvent than required "
            f"({liquid_total_retentate:.3g} kg/hr > {liquid_retained:.3g} kg/hr). "
            "No solvent removal implemented."
        )
        return
    
    # Distribute solvents
    fraction_retained = liquid_transfer / liquid_total
    for ID in solvent_IDs:
        key_r = get_key_for(retentate, ID, 'l')
        key_p = get_key_for(permeate, ID, 'l')
        retentate.imass[key_r] += fraction_retained * permeate.imass[key_p]
        permeate.imass[key_p] -= fraction_retained * permeate.imass[key_p]

        if abs(permeate.imass[key_p]) < 1e-12:
            permeate.imass[key_p] = 0.

        if permeate.imass[key_p] < 0:
            if strict is None: strict = True
            if strict:
                raise InfeasibleRegion(
                    f"not enough {ID} for the moisture_content specified."
                )
            else:
                retentate.imass[key_r] -= permeate.imass[key_p]
                permeate.imass[key_p] = 0.

    # Distribute solutes
    for solute, conc in solutes_conc.items():
        retentate.imass[get_key_for(retentate, solute, 'l')] += conc * liquid_transfer
        permeate.imass[get_key_for(permeate, solute, 'l')] -= conc * liquid_transfer
        
        if abs(permeate.imass[get_key_for(permeate, solute, 'l')]) < 1e-12:
            permeate.imass[get_key_for(permeate, solute, 'l')] = 0.

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
def mix_and_split(ins, top, bottom, split):
    """
    Run splitter mass and energy balance with mixing all input streams.
    
    Parameters
    ----------
    ins : Iterable[Stream]
        All inlet fluids.
    top : Stream
        Top inlet fluid.
    bottom : Stream
        Bottom inlet fluid
    split : array_like
        Component-wise split of feed to the top stream.
    
    Examples
    --------
    >>> import thermosteam as tmo
    >>> tmo.settings.set_thermo(['Water', 'Ethanol'], cache=True)
    >>> feed_a = tmo.Stream(Water=20, Ethanol=5)
    >>> feed_b = tmo.Stream(Water=15, Ethanol=5)
    >>> split = 0.8
    >>> effluent_a = tmo.Stream('effluent_a')
    >>> effluent_b = tmo.Stream('effluent_b')
    >>> tmo.separations.mix_and_split([feed_a, feed_b], effluent_a, effluent_b, split)
    >>> effluent_a.show()
    Stream: effluent_a
    phase: 'l', T: 298.15 K, P: 101325 Pa
    flow (kmol/hr): Water    28
                    Ethanol  8
    >>> effluent_b.show()
    Stream: effluent_b
    phase: 'l', T: 298.15 K, P: 101325 Pa
    flow (kmol/hr): Water    7
                    Ethanol  2
    
    """
    top.mix_from(ins)
    top.split_to(top, bottom, split, energy_balance=True)

def get_key_for(stream, ID, phase='l'):
    """Return the correct index for Stream or MultiStream."""
    return (phase, ID) if isinstance(stream, tmo.MultiStream) else ID