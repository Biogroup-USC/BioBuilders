"""
"""

__all__ = (
    "damp_to",
)

def damp_to(current, target, alpha=0.5):
    """
    
    Apply damping to iteratively update a variable
    towards a target value.

    This function is intended for use in iterative solvers
    and recirculation loops, where a direct update may lead
    to oscillations or convergence issues. The damping factor
    ``alpha`` controls how much of the difference between the
    current and target values is applied at each iteration.

    Parameters
    ----------
    current : float
        Current value of the variable at the present iteration.
    target : float
        Target value computed in the current iteration.
    alpha : float
        Damping factor (0 < alpha <= 1).
        - alpha = 1 [direct update (no damping)]
        - alpha < 1 [gradual and more stable update]
        Default is 0.5.
    
    Returns
    -------
    updated : float
        Damped updated value, computed as:
        ``current + alpha * (target - current)``.
        
    """

    updated = current + alpha*(target - current)

    return updated