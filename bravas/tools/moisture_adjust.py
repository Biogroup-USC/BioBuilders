"""
"""
from biosteam.exceptions import InfeasibleRegion
import thermosteam as tmo
from warnings import warn

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
def mix_and_split_with_moisture_content(ins, retentate, permeate,
                                        split, moisture_content, ID=None,
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
    adjust_moisture_content(retentate, permeate, moisture_content, ID, strict)

# Code adapted from BioSTEAM (https://biosteam.readthedocs.io/), under the University of Illinois/NCSA Open Source License
# Copyright (c) 2019-2023 BioSTEAM Development Group. All rights reserved.
def adjust_moisture_content(retentate, permeate, moisture_content, ID=('Water',), strict=None,):
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
    # Checks
    if isinstance(ID,str):
        ID = (ID,)

    mc = moisture_content
    if not 0 <= mc <= 1:
        raise ValueError("moisture_content must satisfy 0 <= moisture_content <= 1.")
    
    # Calculate dry mass
    F_mass = retentate.F_mass
    retentate_liquid = sum(retentate.imass[i] for i in ID)
    dry_mass = F_mass - retentate_liquid
    if dry_mass < 0:
        raise ValueError("Calculated dry mass is negative. Check species in ID.")

    # Solve liquid needed
    tgt_liquid = dry_mass * mc / (1 - mc)
    delta_liquid = tgt_liquid - retentate_liquid

    # Return if moisture requirements already satisfy
    if abs(delta_liquid) < 1e-12:
        return
    
    # Handle Multistream
    def _get_key(stream, chemical_ID):
        return ('l', chemical_ID) if isinstance(stream, tmo.MultiStream) else chemical_ID
    
    # Distribute solvent and soluble chemicals
    if delta_liquid > 0:
        liquid = sum(permeate.imass[i] for i in ID)
        if liquid <= 0:
            raise InfeasibleRegion(
                f"Not enough permeate {ID}; permeate moisture content is infeasible"
            )

        for chemical in ID:
            # Calculate the mass fraction of chemical
            fraction = permeate.imass[chemical] / liquid
            chemical_mass = fraction * delta_liquid

            retentate_key = _get_key(retentate, chemical)
            permeate_key = _get_key(permeate, chemical)

            retentate.imass[retentate_key] += chemical_mass
            permeate.imass[permeate_key] -= chemical_mass

            if permeate.imass[retentate_key] < 0:
                if strict is None: strict = True
                if strict:
                    raise InfeasibleRegion(f'not enough {chemical_mass}; permeate moisture content')
                else:
                    retentate.imass[retentate_key] -= permeate.imass[permeate_key]
                    permeate.imass[permeate_key] = 0.
    elif 0 > delta_liquid > 1e-12:
        return
    else:
        warn(f"Retentate liquid ({retentate_liquid} 'kg/hr') is higher than liquid needed to satisfy moisture ({tgt_liquid} 'kg/hr').")

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