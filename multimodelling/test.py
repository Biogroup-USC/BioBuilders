
import chems as cs
import biosteam as bst
import units as uts
import results as rs
import parameters as pts
import tea 
import biosteam as bst
from biosteam.units.decorators import cost

Chem_List = ["Water", "Methanol","Ethanol"]
ChMn = cs.ChemManager(Chem_List)
Chemicals = ChMn.creating_chems()
ChMn.initialize_chemicals(Chemicals)

S1 = bst.Stream(ID = 'S1', Water = 10000, units = "kg/hr")
S2 = bst.Stream(ID = 'S2')
S0 = bst.Stream(ID = 'Water', Water = 0, units = "kg/hr")

U1 = uts.ShellHeatExchanger('U1', ins = S1, outs = S2, Tout = 273.15 + 100.0)
U1.run()
U1.simulate()
print(U1.results())