"""
"""
import math

__all__ = (
    "log_mean"
)

def log_mean(a: float, b: float):
    """

    Logarithmic mean of two positive numbers calculated as:
    (b - a) / (log(b) - log(a))

    """
    if a <= 0 or b <= 0:
        raise ValueError("The logarithmic mean is only defined for a,b > 0")
    if a == b:
        return a
    return (b-a)/(math.log(b)-math.log(a))