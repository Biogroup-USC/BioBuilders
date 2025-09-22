"""
"""

__all__ = (
    "damp_to",
)

def damp_to(current, target, alpha=0.5):
    return current + alpha*(target - current)