from dataclasses import dataclass

import biosteam as bst

@dataclass
class ProcessResults:
    """
    """
    system: bst.System
    tea: bst.TEA | None = None

    def simulate(self):
        self.system.simulate()

    def build_mass_balance():
        """"""

    def build_energy_balance():
        """"""