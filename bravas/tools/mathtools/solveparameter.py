"""
"""

import thermosteam as tmo

__all__ = (
    "solve_operating_pressures_multieffectevaporator",
)

def solve_operating_pressures_multieffectevaporator(    
        T_initial: float = 100,     # ºC 
        T_step: float = 10,         # ºC 
        n_effects: int = 3,
        method: str = 'Antoine',
        method_params: dict = None
    ):
    """
    """
    Pressures = []
    Temperatures = []

    for i in range(n_effects):
        # Calculate the temperature of each effect
        T_C = T_initial - i * T_step
        Temperatures.append(T_C)

        # Calculate the operating pressure using Antoine
        if method == 'Antoine':
            # Check if the method_params are provided
            if method_params is None:
                raise ValueError("The params of the {} method must be defines in the method_params dictionary".format(method))
            
            # Get the Antoine´s parameters
            A = method_params['A']
            B = method_params['B']
            C = method_params['C']

            # Calculate the pressure in mmHg
            P_mmHg = 10**(A-B/(C + T_C))

            # Convert the pressure to Pa
            P_Pa = P_mmHg * 133.322
            Pressures.append(P_Pa)
        elif method == 'Thermosteam':   #TODO add a method based on Biosteam calculations
            pass

    # return the list of temperatures and pressures
    return tuple(Pressures), tuple(Temperatures)